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
    print("Strategy Candidates: ")
    bestVScore = 0
    bestStrat = None
    for strat in strat_candidates:
      print(strat)
      print(f"Training Score: {run.getStrategyStat(strat)}")
      valScore = valEvaluator.evaluate(strat)
      print(f"Validation Score: {valScore}\n")
      if valScore > bestVScore:
         bestVScore = valScore
         bestStrat = strat
    print(f"Best Strat: \n{bestStrat}")

if __name__ == "__main__":
    main()
