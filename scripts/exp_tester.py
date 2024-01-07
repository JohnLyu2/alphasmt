import os
import csv
import pathlib
import sys
import argparse
import json
sys.path.append('..')

from alphasmt.evaluator import Z3StrategyEvaluator

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('json_config', type=str, help='The experiment testing configuration file in json')
    configJsonPath = parser.parse_args()
    config = json.load(open(configJsonPath.json_config, 'r'))

    z3path = config['z3path'] if 'z3path' in config else "z3"
    strat_files = config['strat_files']
    timeout = config['timeout']
    batchSize = config['batch_size']
    res_dir = config['res_dir']
    test_dir = config['test_dir']

    test_lst = [str(p) for p in sorted(list(pathlib.Path(test_dir).rglob(f"*.smt2")))]
    res_csv = os.path.join(res_dir, "res.csv")
    with open(res_csv, 'w') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(["solver", "solved", "par2", "par10"]) # write header
        for solver in strat_files.keys():
            strat = None
            if not strat_files[solver] is None:
                strat_file = strat_files[solver]
                strat = open(strat_file, 'r').read()
            csv_path = os.path.join(res_dir, f"{solver}.csv")
            testEvaluator = Z3StrategyEvaluator(z3path, test_lst, timeout, batchSize, is_write_res=True, res_path=csv_path)
            resTuple = testEvaluator.testing(strat)
            csvwriter.writerow([solver, resTuple[0], resTuple[1], resTuple[2]])
            print(f"{solver} test results: solved {resTuple[0]} instances with par2 {resTuple[1]} and par10 {resTuple[2]:.2f}")

if __name__ == "__main__":
    main()