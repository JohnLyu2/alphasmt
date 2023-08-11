import sys
sys.path.append('..')

from alphasmt.AST import DerivationAST
from alphasmt.MCTS import MCTSNode, MCTS_RUN
from alphasmt.Environment import StrategyGame
from alphasmt.Evaluator import Z3StrategyEvaluator

LOGIC = "QF_NIA"
TRAIN_SET = "/Users/zhengyanglumacmini/Desktop/AlphaSMT/Experiments/Benchmarks/test1"
VALID_SET = "/Users/zhengyanglumacmini/Desktop/AlphaSMT/Experiments/Benchmarks/test1"
SIM_NUM = 5
NUM_STRAT = 5


def main():
    # train
    print("Training Starts")
    run = MCTS_RUN(SIM_NUM, TRAIN_SET, LOGIC)
    run.start()
    strat_candidates = run.bestNStrategies(NUM_STRAT)
    print(f"Simulations done. {NUM_STRAT} strategies are selected.")

    # validate
    print("Validation Starts")
    valEvaluator = Z3StrategyEvaluator(VALID_SET)
    valSize = valEvaluator.getBenchmarkSize()
    print("Strategy Candidates: ")
    bestPar2 = valSize * 36000 # change later
    bestStrat = None
    for strat in strat_candidates:
      print(strat)
      print(f"Training Score: {run.getStrategyStat(strat)}")
      valResTuple = valEvaluator.evaluate(strat)  
      par2 = Z3StrategyEvaluator.caculateTimePar2(valResTuple, valSize, 1)
      print(f"Validation: solved {valResTuple[0]} instances with rlimit {valResTuple[1]} and time {valResTuple[2]}; par2: {par2}")
      if par2 < bestPar2:
         bestPar2 = par2
         bestStrat = strat
    print(f"Best Strat: \n{bestStrat}")

if __name__ == "__main__":
    main()
