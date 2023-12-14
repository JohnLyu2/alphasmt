import sys
sys.path.append('..')


from alphasmt.strat_tree import *
from alphasmt.selector import *

def main():
    # s1_0 = S1StrategyAST("QF_NIA")
    # print(s1_0)
    # print(f"Is s1_0 in terminal state: {s1_0.isTerminal()}")
    # s1_0.applyRule(0, None)
    # print(s1_0)
    # s1_0.applyRule(11, None)
    # print(s1_0)

    s1_1 = StrategyAST(1, "QF_NRA", 10)
    s1_1.applyRule(1, None)
    print(s1_1)
    print(s1_1.findFstNonTerm())
    s1_1.applyRule(22, None)
    print(s1_1)
    s1_1.applyRule(0, None)
    s1_1.applyRule(11, None)
    print(s1_1)
    print(f"sm2 strategy: {s1_1}")
    print(s1_1.get_linear_strategies())

    # stage 2
    ln_strat0 = "smt"
    ln_strat1 = "(then (using-params simplify :elim_and true :som true :blast_distinct true :flat true :hi_div0 true :local_ctx true :hoist_mul true :push_ite_bv true :pull_cheap_ite true) ctx-simplify propagate-values qfnra-nlsat)"
    ln_strat2 = "(then (using-params nla2bv :nla2bv_max_bv_size 4) smt)"
    ln_strat3 = "(then card2bv cofactor-term-ite elim-uncnstr qfnra-nlsat)"

    strats = [ln_strat0, ln_strat1, ln_strat2, ln_strat3]

    act_lst, solver_dict, preprocess_dict, s1strat2acts = convert_strats_to_act_lists(strats)

    s2_0 = StrategyAST(2, "QF_NRA", 10, act_lst, solver_dict, preprocess_dict)
    print(s2_0)
    s2_0.applyRule(2, None)
    print(s2_0)
    print(f"legal actions: {s2_0.legalActions()}")
    s2_0.applyRule(1, None)
    print(s2_0)
    print(f"legal actions: {s2_0.legalActions()}")
    s2_0.applyRule(1000, None)
    print(s2_0)
    print(f"legal actions: {s2_0.legalActions()}")
    s2_0.applyRule(2004, None)
    print(s2_0)
    print(f"legal actions: {s2_0.legalActions()}")


if __name__ == "__main__":
    main()