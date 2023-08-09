import pytest

from alphasmt.MCTS import MCTSNode, MCTS_RUN

# Parameter MABs
root0 = MCTSNode()
root1 = MCTSNode([5])
root2 = MCTSNode([5, 3])
root3 = MCTSNode([5, 3, 20])


def test_hasParamMABs():
    assert not root0.hasParamMABs()
    assert root1.hasParamMABs()
    assert not root2.hasParamMABs()
    assert root3.hasParamMABs()

root1._setParamMABs()
root3._setParamMABs()

def test_setParamMABs():
    assert len(root1.params) == 1
    assert len(root3.params) == 7