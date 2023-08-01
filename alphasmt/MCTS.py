import math
import copy
from alphasmt.Environment import StrategyGame


class MCTSNode():
    def __init__(self, envn, action_history=[]):
        self.envn = envn
        self.visitCount = 0
        self.actionHistory = action_history # 
        self.valueLst = []
        self.children = {}
        self.reward = 0  # always 0 for now

    def __str__(self):
        return str(self.actionHistory)

    def isExpanded(self):
        return bool(self.children)

    def isTerminal(self):
        return self.envn.isTerminal()

    def value(self):
        if self.visitCount == 0:  # will this be called anytime?
            return 0
        return max(self.valueLst)

# A MCTS run starting at a particular node as root; this framework only works for deterministric state transition


class MCTS_RUN():
    def __init__(self, num_simulations, root):
        # to-do: pack some into config
        self.numSimulations = num_simulations
        self.discount = 1  # now set to 1
        self.c_uct = 1
        self.root = root
        self.resDatabase = {}

    def _uct(self, childNode, parentNode):
        valueScore = 0
        if childNode.visitCount > 0:
            valueScore = childNode.reward + self.discount * childNode.value()
        exploreScore = self.c_uct * \
            math.sqrt(math.log(parentNode.visitCount) /
                      (childNode.visitCount + 0.001))
        return valueScore + exploreScore

    def _select(self):
        searchPath = [self.root]
        node = self.root
        while node.isExpanded() and not node.isTerminal():
            # may add randomness when the UCTs are the same
            _, action, node = max((self._uct(childNode, node), action, childNode)
                                  for action, childNode in node.children.items())
            searchPath.append(node)
            # self.env.step(action)
        return node, searchPath

    @staticmethod
    def _expandNode(node, actions, reward):
        node.reward = reward
        for action in actions:
            childEnvn = node.envn.step(action)
            history = copy.deepcopy(node.actionHistory)
            history.append(action)
            node.children[action] = MCTSNode(childEnvn, history)

    @staticmethod
    def _rollout(node):
        return node.envn.rollout()

    def _backup(self, searchPath, sim_value):
        value = sim_value
        for node in reversed(searchPath):
            node.valueLst.append(value)
            node.visitCount += 1
            value = node.reward + self.discount * value

    def _oneSimulation(self):
        # now does not consider the root is not the game start
        selectNode, searchPath = self._select()
        print("Selected Node: " + str(selectNode))
        print("Selected Strategy ParseTree: " + str(selectNode.envn))
        if selectNode.isTerminal():
            print("Terminal Strategy: no rollout")
            value = selectNode.envn.getValue(self.resDatabase)
        else:
            actions = selectNode.envn.legalActions()
            # now reward is always 0 at each step
            MCTS_RUN._expandNode(selectNode, actions, 0)
            rolloutGame = MCTS_RUN._rollout(selectNode)
            print("Rollout Strategy: " + str(rolloutGame))
            value = rolloutGame.getValue(self.resDatabase)
        print("Final Return: " + str(value) + "\n")
        self._backup(searchPath, value)

    def start(self):
        for i in range(self.numSimulations):
            print(f"Simulation {i} starts")
            self._oneSimulation()

    def bestNStrategies(self, n):
        if n > len(self.resDatabase):
            n = len(self.resDatabase)
        return sorted(self.resDatabase, key=self.resDatabase.get, reverse=True)[:n]
