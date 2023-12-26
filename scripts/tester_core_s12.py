import os
import csv
import pathlib
import sys
sys.path.append('..')

from alphasmt.evaluator import Z3StrategyEvaluator

def main():

  strat_files = {
    "stage_alpha": "/home/z52lu/alphasmt/cc_scripts/experiments/results/out_core-2023-12-25_23-09-46/final_strategy.txt"
  }
  timeout = 10
  batchSize = 50
  res_dir = "/home/z52lu/alphasmt/cc_scripts/experiments/results/out_core-2023-12-25_23-09-46/test_res"
  test_dir = "/home/z52lu/fastsmtData/smt_data/qf_bv/bruttomesso/core/test"

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
      testEvaluator = Z3StrategyEvaluator(test_lst, timeout, batchSize, is_write_res=True, res_path=csv_path)
      resTuple = testEvaluator.testing(strat)
      csvwriter.writerow([solver, resTuple[0], resTuple[1], resTuple[2]])
      print(f"{solver} test results: solved {resTuple[0]} instances with par2 {resTuple[1]} and par10 {resTuple[2]:.2f}")

if __name__ == "__main__":
    main()