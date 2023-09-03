import sys
sys.path.append('..')

from alphasmt.Evaluator import Z3StrategyEvaluator

def main():
  timeout = 24 
  strat = None
  batchSize = 120
  testEvaluator = Z3StrategyEvaluator("/home/azureuser/smtlib/fastsmt_data/sage2/valid", timeout, batchSize)
  testSize = testEvaluator.getBenchmarkSize()
  resTuple = testEvaluator.evaluate(strat)  
  par2 = Z3StrategyEvaluator.caculateTimePar2(resTuple, testSize, timeout)
  print(f"Test: solved {resTuple[0]} instances with rlimit {resTuple[1]} and time {resTuple[2]}; par2: {par2}\n")

if __name__ == "__main__":
    main()