import sys
sys.path.append('..')

from alphasmt.mcts import MCTSNode, MCTS_RUN
from alphasmt.environment import StrategyGame
from alphasmt.evaluator import Z3StrategyEvaluator
from alphasmt.parser import *
from alphasmt.selector import *


def main():
    # test tokenizer
    t_lst = Strategy_Tokenizer('(using-params qfnra-nlsat :inline_vars true:seed 1000 :factor true)')
    for t in t_lst:
        print(t)

    s1strat0 = "(then simplify solve-eqs (using-params qfnra-nlsat :inline_vars true:seed 1000 :factor true) )"
    parse_res = s1_strat_parse(s1strat0)
    for t in parse_res:
        print(str(t))

    # test convert_strats_to_act_lists
    tset0 = set()
    tset0.add(s1strat0)

    converted_lst, solver_dict, preprocess_dict = convert_strats_to_act_lists(tset0)
    print(converted_lst)
    print(solver_dict)
    print(preprocess_dict)

    # # test parser
    # strat0 = Strategy_Parse(' ( if  is-qfbv-eq bv1-blast sat)')
    # print(strat0)  
    # strat1 = Strategy_Parse('smt')
    # # strat2 = Strategy_Parse('( if  (> num-consts 20) ( then   bv1-blast sat) (then simplify sat))')
    # print(strat1)
    # strat2 = Strategy_Parse(' ( if  (> size 5) bv1-blast (using-params qfnra-nlsat :inline_vars true:seed 1000 :factor true))')  
    # print(strat2)
    # strat3 = Strategy_Parse('(using-params qfnra-nlsat :inline_vars true:seed 1000 :factor true)')  
    # print(strat3)
    # strat4 = Strategy_Parse('(then simplify (using-params qfnra-nlsat :inline_vars true:seed 1000 :factor true) )')  
    # print(strat4)
    # strat5 = Strategy_Parse('(then simplify bv1-blast (if is-qfbv-eq (using-params qfnra-nlsat :inline_vars true:seed 1000 :factor true) sat))')
    # print(strat5)
    # strat6 = Strategy_Parse('(then simplify (if is-qfbv-eq (using-params qfnra-nlsat :inline_vars true:seed 1000 :factor true) (if (> size 5) (then simplify bv1-blast sat) sat)))')
    # print(strat6)

if __name__ == "__main__":
    main()
