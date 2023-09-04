import os
import logging 
import argparse
import json
import datetime
import pathlib
import random
from z3 import *

from alphasmt.MCTS import MCTS_RUN
from alphasmt.Evaluator import Z3StrategyEvaluator

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s','%Y-%m-%d %H:%M:%S'))
log.addHandler(log_handler)

import functools
print = functools.partial(print, flush=True)

def calculatePercentile(lst, percentile):
    assert (len(lst) > 0)
    sortedLst = sorted(lst)
    index = int(len(sortedLst) * percentile)
    return sortedLst[index]

def createProbeStatDict(benchmark_directory):
    numConstsLst = []
    numExprsLst = []
    sizeLst = []
    benchmarkLst = [str(p) for p in sorted(list(pathlib.Path(benchmark_directory).rglob(f"*.smt2")))]
    # no parllel now 
    for smt_path in benchmarkLst:
        formula = parse_smt2_file(smt_path)
        constProbe = Probe('num-consts')
        exprProbe = Probe('num-exprs')
        sizeProbe = Probe('size')
        goal = Goal()
        goal.add(formula)
        numConstsLst.append(constProbe(goal))
        numExprsLst.append(exprProbe(goal))
        sizeLst.append(sizeProbe(goal))
    # get 90 percentile, 70 percentile and median from lists
    percentileLst = [0.9, 0.7, 0.5]
    probeStats = {}
    # to-do: make probe as list
    probeStats[50] = {"value": [calculatePercentile(numConstsLst, p) for p in percentileLst]} # action 50: probe num-consts
    probeStats[51] = {"value": [calculatePercentile(numExprsLst, p) for p in percentileLst]} # action 51: probe num-exprs
    probeStats[52] = {"value": [calculatePercentile(sizeLst, p) for p in percentileLst]} # action 52: probe size
    return probeStats

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('json_config', type=str, help='The experiment configuration file in json')
    configJsonPath = parser.parse_args()
    config = json.load(open(configJsonPath.json_config, 'r'))

    logic = config['logic']
    train_path = config['training_dir']
    val_path = config['validation_dir']
    num_val_strat = config['strategy_2b_validated']
    sim_num = config['simulation_number']
    is_mean_est = config['is_mean_est']
    timeout = config['timeout']
    batchSize = config['batch_size']
    c_uct =  config['c_uct'] # for mcts select
    c_ucb =  config['c_ucb'] # for parameter mab
    # mab_alpha =  config['mab_alpha'] # for parameter mab
    test_factor = config['testing_factor']
    tmp_folder = config['temp_folder']
    random_seed = config['random_seed']
    random.seed(random_seed)

    log_folder = f"experiments/results/out-{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}/"
    assert(not os.path.exists(log_folder))
    os.makedirs(log_folder)

    trainProbeStatDict = createProbeStatDict(train_path)
    log.info(f"Probe Stats: {trainProbeStatDict}")

    # train
    log.info("MCTS Simulations Start")
    run = MCTS_RUN(sim_num, is_mean_est, train_path, logic, timeout, batchSize, log_folder, c_uct=c_uct, c_ucb=c_ucb, test_factor=test_factor, probe_dict=trainProbeStatDict, tmp_folder=tmp_folder)
    run.start()
    strat_candidates = run.bestNStrategies(num_val_strat)
    log.info(f"Simulations done. {num_val_strat} strategies are selected.")

    # validate
    val_log = logging.getLogger("validation")
    val_log.setLevel(logging.INFO)
    vallog_handler = logging.FileHandler(f"{log_folder}/validation.log")
    val_log.addHandler(vallog_handler) 


    log.info("Validation Starts\n")
    valEvaluator = Z3StrategyEvaluator(val_path, timeout, batchSize, test_factor=test_factor)
    valSize = valEvaluator.getBenchmarkSize()
    bestPar2 = valSize * timeout * 2
    bestStrat = None
    for strat in strat_candidates:
      val_log.info(strat)
      val_log.info(f"Training Score: {run.getStrategyStat(strat)}")
      valResTuple = valEvaluator.evaluate(strat)  
      par2 = Z3StrategyEvaluator.caculateTimePar2(valResTuple, valSize, timeout)
      val_log.info(f"Validation: solved {valResTuple[0]} instances with rlimit {valResTuple[1]} and time {valResTuple[2]:.02f}; par2: {par2:.02f}\n")
      if par2 < bestPar2:
         bestPar2 = par2
         bestStrat = strat

    log.info(f"Best Strategy found: \n{bestStrat}")
    finalStratPath = f"{log_folder}/final_strategy.txt"
    with open(finalStratPath, 'w') as f:
       f.write(bestStrat)

if __name__ == "__main__":
    main()
