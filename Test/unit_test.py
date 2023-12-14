import pytest
import sys
sys.path.append('..')
from alphasmt.parser import *
from alphasmt.mcts import MCTSNode, MCTS_RUN
from alphasmt.parser import *

# Parameter MABs
# root0 = MCTSNode()
# root1 = MCTSNode([5])
# root2 = MCTSNode([5, 3])
# root3 = MCTSNode([5, 3, 20])

# def test_hasParamMABs():
#     assert not root0.hasParamMABs()
#     assert root1.hasParamMABs()
#     assert not root2.hasParamMABs()
#     assert root3.hasParamMABs()

# root1._setParamMABs()
# root3._setParamMABs()

# def test_setParamMABs():
#     assert len(root1.params) == 1
#     assert len(root3.params) == 7


def test_tokenizer():
    tlst0 = Strategy_Tokenizer(' ( if  is-qfbv-eq ( then   bv1-blast sat) (then simplify sat))')
    tlst1 = Strategy_Tokenizer('smt')
    tlst2 = Strategy_Tokenizer('(using-params qfnra-nlsat :inline_vars true)')
    assert len(tlst0) == 14
    assert len(tlst1) == 1
    assert len(tlst2) == 7