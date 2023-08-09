import sys
sys.path.append('..')

from alphasmt.AST import DerivationAST
from alphasmt.MCTS import MCTSNode, MCTS_RUN
from alphasmt.Environment import StrategyGame
from alphasmt.Evaluator import Z3StrategyEvaluator


def main():
    # # AST tests
    # print("CFG AST tests")
    # newStrat = DerivationAST("QF_NIA")
    # print(newStrat.findFstNonTerm())
    # print(newStrat.legalActions())
    # newStrat.applyRule(1)
    # print(newStrat.findFstNonTerm())
    # print(newStrat)
    # print(newStrat.legalActions())
    # strat_cp0 = newStrat.clone()
    # print(strat_cp0)
    # print(newStrat)
    # newStrat.applyRule(20)
    # print(newStrat.legalActions())
    # newStrat.applyRule(0)
    # print(newStrat.legalActions())
    # newStrat.applyRule(10)
    # print(newStrat)
    # strat_cp1 = newStrat.clone()
    # print(strat_cp0)
    # print(strat_cp1)
    # assert (newStrat.isTerminal())

    # # Evaluator tests
    # print("\nEvaluator tests")
    # eval1 = Z3StrategyEvaluator(
    #     "/Users/zhengyanglumacmini/Desktop/AlphaSMT/Experiments/Benchmarks/test1")
    # print(eval1.benchmarkLst)
    # print(eval1.evaluate('smt'))
    # print(eval1.evaluate('(try-for smt 300)'))
    # print(eval1.results)

    # MCTS tests
    print("\nCFG AST tests")
    root = MCTSNode()
    run = MCTS_RUN(30, root, "/Users/zhengyanglumacmini/Desktop/AlphaSMT/Experiments/Benchmarks/test1", "QF_NIA")
    run.start()
    print(run.root.valueLst)
    print(run.root.value())
    print(run)
    print(run.bestNStrategies(4))


if __name__ == "__main__":
    main()
