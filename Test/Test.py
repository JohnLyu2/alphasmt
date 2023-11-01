import sys
sys.path.append('..')

from alphasmt.cfg_tree import DerivationAST
from alphasmt.mcts import MCTSNode, MCTS_RUN
from alphasmt.environment import StrategyGame
from alphasmt.evaluator import Z3StrategyEvaluator


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

    # Evaluator tests
    print("\nEvaluator tests")
    eval1 = Z3StrategyEvaluator(
        "/Users/zhengyanglumacmini/Desktop/AlphaSMT/Experiments/Benchmarks/test1", 1, 2)
    print(eval1.benchmarkLst)

    print(eval1.evaluate('sat'))
    print(eval1.evaluate('(if is-qfbv-eq (then bv1-blast sat) (then simplify sat))'))
    # print(eval1.evaluate('(or-else (try-for (or-else (try-for smt 300) (or-else (then nla2bv smt) qfnra-nlsat)) 300) smt)'))
    # print(eval1.results)

    # MCTS tests
    # print("\nCFG AST tests")
    # root = MCTSNode()
    # run = MCTS_RUN(30, root, "/Users/zhengyanglumacmini/Desktop/AlphaSMT/Experiments/Benchmarks/test1", "QF_NIA")
    # run.start()
    # print(run.root.valueLst)
    # print(run.root.value())
    # print(run)
    # print(run.bestNStrategies(4))


if __name__ == "__main__":
    main()
