import time
import random
import pathlib
import csv
import os

from alphasmt.evaluator import Z3StrategyEvaluator
from alphasmt.mcts import MCTS_RUN
from alphasmt.selector import * 

VALUE_TYPE = 'par10' # hard code for now

def write_strat_res_to_csv(res_dict, csv_path, bench_lst):
    with open(csv_path, 'w') as f:
        writer = csv.writer(f)
        # write header
        writer.writerow(["strat"] + bench_lst)
        for strat in res_dict:
            res_lst = []
            for res_tuple in res_dict[strat]:
                if res_tuple[0]:
                    res_lst.append(res_tuple[1])
                else:
                    res_lst.append(-res_tuple[1])
            writer.writerow([strat] + res_lst)

def read_strat_res_from_csv(csv_path):
    res_dict = {}
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        bench_lst = header[1:]
        for row in reader:
            strat = row[0]
            res_lst = []
            for res in row[1:]:
                stime = float(res)
                if stime < 0:
                    res_lst.append((False, -stime))
                else:
                    res_lst.append((True, stime))
            res_dict[strat] = res_lst
    return res_dict, bench_lst

def createBenchmarkList(benchmark_directory, timeout, batchSize, tmp_folder, is_sorted):
    benchmarkLst = [str(p) for p in sorted(list(pathlib.Path(benchmark_directory).rglob(f"*.smt2")))]
    if not is_sorted:
        return benchmarkLst
    evaluator = Z3StrategyEvaluator(benchmarkLst, timeout, batchSize, tmp_dir=tmp_folder)
    resLst = evaluator.getResLst(None)
    # par2 list from resLst; for each entry (solved, time) in resLst, if solved, return time; else return 2 * timeout
    par2Lst = [2 * timeout if not res[0] else res[1] for res in resLst]
    # sort benchmarkLst resLst into a ascending list by par2Lst
    benchmarkLst = [x for _, x in sorted(zip(par2Lst, benchmarkLst))]
    return benchmarkLst

def stage1_synthesize(config, stream_logger, log_folder):
    startTime = time.time()
    logic = config['logic']
    batch_size = config['batch_size']
    s1config = config['s1config']
    num_ln_strat = config['ln_strat_num']
    tmp_folder = config['temp_folder']
    random_seed = config['random_seed']
    random.seed(random_seed)
    
    # Stage 1
    s1_bench_dir = s1config['bench_dir']
    s1BenchLst = createBenchmarkList(s1_bench_dir, s1config["timeout"], batch_size, tmp_folder, is_sorted=True)
    stream_logger.info("S1 MCTS Simulations Start")
    run1 = MCTS_RUN(1, s1config, s1BenchLst, logic, VALUE_TYPE, log_folder, tmp_folder=tmp_folder, batch_size = batch_size)
    run1.start()
    s1_res_dict = run1.getResDict()

    selected_strat = linear_strategy_select(num_ln_strat, s1_res_dict, s1config["timeout"])
    lnStratCandidatsPath = os.path.join(log_folder,'ln_strat_candidates.csv')
    with open(lnStratCandidatsPath, 'w') as f:
        # write one strategy per line as a csv file
        cwriter = csv.writer(f)
        # header (one column "strat")
        cwriter.writerow(["strat"])
        for strat in selected_strat:
            cwriter.writerow([strat])
    stream_logger.info(f"Selected {len(selected_strat)} strategies: {selected_strat}, saved to {lnStratCandidatsPath}")

    endTime = time.time()
    s1time = endTime - startTime
    stream_logger.info(f"Stage 1 Time: {s1time:.0f}")
    return selected_strat, s1time

def cache4stage2(selected_strat, config, stream_logger, log_folder):
    startTime = time.time()
    s2config = config['s2config']
    s2benchDir = s2config['bench_dir']
    s2timeout = s2config['timeout']
    batch_size = config['batch_size']
    tmp_folder = config['temp_folder']
    s2benchLst = createBenchmarkList(s2benchDir, s2timeout, batch_size, tmp_folder, is_sorted=True)
    s2_res_dict = {}
    s2evaluator = Z3StrategyEvaluator(s2benchLst, s2timeout, batch_size, tmp_dir=tmp_folder)
    for i in range(len(selected_strat)):
        strat = selected_strat[i]
        stream_logger.info(f"Stage 2 Caching: {i+1}/{len(selected_strat)}")
        s2_res_dict[strat] = s2evaluator.getResLst(strat)
    ln_res_csv = os.path.join(log_folder, "ln_res.csv")
    write_strat_res_to_csv(s2_res_dict, ln_res_csv, s2benchLst)
    stream_logger.info(f"Cached results saved to {ln_res_csv}")
    endTime = time.time()
    cacheTime = endTime - startTime
    stream_logger.info(f"Stage 2 Cache Time: {cacheTime:.0f}")
    return s2_res_dict, s2benchLst, cacheTime

def stage2_synthesize(res_dict, bench_lst, config, stream_logger, log_folder):
    selected_strat = list(res_dict.keys())
    act_lst, solver_dict, preprocess_dict, s1strat2acts = convert_strats_to_act_lists(selected_strat)
    stream_logger.info(f"preprocess dict: {preprocess_dict}")
    stream_logger.info(f"solver dict: {solver_dict}")
    stream_logger.info(f"converted selected strategies: {act_lst}")

    s2_res_dict_acts = {}
    for strat in s1strat2acts:
        s2_res_dict_acts[s1strat2acts[strat]] = res_dict[strat]

    s2config = config['s2config']
    s2config['s1_strats'] = act_lst
    s2config['solver_dict'] = solver_dict
    s2config['preprocess_dict'] = preprocess_dict
    s2config['res_cache'] = s2_res_dict_acts
    logic = config['logic']
    tmp_folder = config['temp_folder']

    s2startTime = time.time()
    stream_logger.info(f"S2 MCTS Simulations Start")

    run2 = MCTS_RUN(2, s2config, bench_lst, logic, VALUE_TYPE, log_folder, tmp_folder=tmp_folder)
    run2.start()
    best_s2 = run2.getBestStrat()
    finalStratPath = os.path.join(log_folder, 'final_strategy.txt')
    with open(finalStratPath, 'w') as f:
        f.write(best_s2)
    stream_logger.info(f"Final Strategy saved to: {finalStratPath}")

    s2endTime = time.time()
    s2time = s2endTime - s2startTime
    stream_logger.info(f"Stage 2 MCTS Time: {s2time:.0f}")
    return best_s2, s2time