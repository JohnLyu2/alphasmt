import logging 
import argparse
import json
import csv
import datetime
import os

from alphasmt.synthesize import read_strat_res_from_csv, cache4stage2, stage2_synthesize

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s','%Y-%m-%d %H:%M:%S'))
log.addHandler(log_handler)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('json_config', type=str, help='The experiment configuration file in json')
    parser.add_argument('--no_caching', action='store_false', default = True, help='cache results are provided; no need to caching s1 strats')
    parser.add_argument('--no_syn', action='store_false', default = True, help='does not need to perform s2 synthesize')
    configJsonPath = parser.parse_args()
    config = json.load(open(configJsonPath.json_config, 'r'))
    s2config = config['s2config']
    is_cache = configJsonPath.no_caching
    is_syn = configJsonPath.no_syn
    assert is_cache or is_syn, "no caching and no synthesize; nothing to do"
    log_folder = f"experiments/results/out-{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}/"
    assert(not os.path.exists(log_folder))
    os.makedirs(log_folder)
    
    cache_time = 0
    res_dict = None
    bench_lst = None
    if is_cache:
        ln_strat_file = s2config['ln_res']
        with open(ln_strat_file, 'r') as f:
            creader = csv.reader(f)
            next(creader)
            stratLst = [row[0] for row in creader]
        res_dict, bench_lst, cache_time = cache4stage2(stratLst, config, log, log_folder)

    if not is_syn:
        return

    if not is_cache:
        ln_strat_file = s2config['ln_res']
        res_dict, bench_lst = read_strat_res_from_csv(ln_strat_file)
        log.info(f"s2syn: read {len(res_dict)} strategies from {ln_strat_file}")
    
    bst_strat, s2mcts_time = stage2_synthesize(res_dict,bench_lst, config, log, log_folder)
    log.info(f"Best strategy found: {bst_strat}")
    log.info(f"S2: Cache time: {cache_time:.0f}, MCTS time: {s2mcts_time:.0f}, Total time: {cache_time + s2mcts_time:.0f}")


if __name__ == "__main__":
    main()