import os
import csv
import pathlib

from alphasmt.Evaluator import Z3StrategyEvaluator

def main():

  strat_files = {
    "z3-alpha": "/Users/zhengyanglumacmini/Desktop/AlphaSMT/experiments/results/out-2023-08-24_20-51-07/final_strategy.txt",
    "fastsmt": "/Users/zhengyanglumacmini/Desktop/AlphaSMT/experiments/results/out-2023-08-24_20-51-07/final_strategy.txt",
    "z3": None
    }
  timeout = 1
  strat = None
  batchSize = 2
  res_dir = "/Users/zhengyanglumacmini/Desktop/AlphaSMT/scripts/temp_res"
  test_dir = "/Users/zhengyanglumacmini/Desktop/AlphaSMT/benchmarks/test1"



  test_lst = [str(p) for p in sorted(list(pathlib.Path(test_dir).rglob(f"*.smt2")))]
  res_csv = os.path.join(res_dir, "res.csv")
  with open(res_csv, 'w') as f:
    csvwriter = csv.writer(f)
    csvwriter.writerow(["solver", "solved", "rlimit", "time", "par2"]) # write header
    for solver in strat_files.keys():
      strat = None
      if not strat_files[solver] is None:
        strat_file = strat_files[solver]
        strat = open(strat_file, 'r').read()
      csv_path = os.path.join(res_dir, f"{solver}.csv")
      testEvaluator = Z3StrategyEvaluator(test_lst, timeout, batchSize, is_write_res=True, res_path=csv_path)
      testSize = testEvaluator.getBenchmarkSize()
      resTuple = testEvaluator.evaluate(strat)  
      par2 = Z3StrategyEvaluator.caculateTimePar2(resTuple, testSize, timeout)
      csvwriter.writerow([solver, resTuple[0], resTuple[1], resTuple[2], par2])
      print(f"{solver} test results: solved {resTuple[0]} instances with rlimit {resTuple[1]} and time {resTuple[2]:.2f}; par2: {par2:.2f}")

if __name__ == "__main__":
    main()