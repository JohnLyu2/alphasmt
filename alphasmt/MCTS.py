import math
import copy
from alphasmt.Environment import StrategyGame

INIT_Q = 1
C_UCT = 1
STEP_ALPHA = 0.3

# to-do: move to somewhere else later/change it into inputs
TACTIC_PARAMS = {
    # "simplify"
    20: { 
        "elim_and": ["true","false"],
        "som": ["true","false"],
        "blast_distinct": ["true","false"],
        "flat": ["true","false"],
        "hi_div0": ["true","false"],
        "local_ctx": ["true","false"],
        "hoist_mul": ["true","false"]
    },
    # "nla2bv" 
    5: {
        "nla2bv_max_bv_size": [i * 10 for i in range(11)]
    }
}

class MCTSNode():
    def __init__(self, action_history=[]):
        # self.envn = envn
        self.visitCount = 0
        self.actionHistory = action_history # 
        self.valueLst = []
        self.children = {}
        self.reward = 0  # always 0 for now
        self._setParamMABs()

    def __str__(self):
        return str(self.actionHistory)

    def isExpanded(self):
        return bool(self.children)

    # def isTerminal(self):
    #     return self.env.isTerminal()

    def hasParamMABs(self):
        return len(self.actionHistory)>0 and self.actionHistory[-1] in TACTIC_PARAMS.keys()

    def _setParamMABs(self):
        if not self.hasParamMABs(): return
        self.params = TACTIC_PARAMS[self.actionHistory[-1]]
        self.MABs = {}
        self.selected = {}
        for param in self.params.keys():
            MABdict = {}
            for paramValue in self.params[param]:
                MABdict[paramValue] = [0, INIT_Q] # (visit count, q estimation) 
            self.MABs[param] = MABdict
            self.selected[param] = None

    def _uct(self, action_pair):
        visitCount, qScore = action_pair
        # print("Q: " + str(qScore))
        exploreScore = C_UCT * \
            math.sqrt(math.log(self.visitCount + 1) / # check ucb 1
                      (visitCount + 0.001))
        # print("Exp: " + str(exploreScore))
        return qScore + exploreScore

    def _selectMAB(self, param):
        MABdict = self.MABs[param]
        _, selectValue = max((self._uct(pair), valueCanadidate)
                                  for valueCanadidate, pair in MABdict.items())
        return selectValue

    def selectMABs(self):
        for param in self.params.keys():
            selectV = self._selectMAB(param)
            self.selected[param] = selectV
        return self.selected

    def backupMABs(self, returnV):
        for param in self.params.keys():
            MABdict = self.MABs[param]
            selectedV = self.selected[param]
            MABdict[selectedV][0] += 1
            MABdict[selectedV][1] = MABdict[selectedV][1] + STEP_ALPHA * (returnV - MABdict[selectedV][1]) # exponential recency-weighted average
            self.selected[param] = None


    def value(self):
        if self.visitCount == 0:  # will this be called anytime?
            return 0
        return max(self.valueLst)

# A MCTS run starting at a particular node as root; this framework only works for deterministric state transition


class MCTS_RUN():
    def __init__(self, num_simulations, training_set, logic, root = None):
        # to-do: pack some into config
        self.numSimulations = num_simulations
        self.discount = 1  # now set to 1
        self.c_uct = 1
        if not root: root = MCTSNode()
        self.root = root
        self.trainingSet = training_set
        self.logic = logic
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
        # does not consider the root has MABs
        while node.isExpanded() and not self.env.isTerminal():
            # may add randomness when the UCTs are the same
            _, action, node = max((self._uct(childNode, node), action, childNode)
                                  for action, childNode in node.children.items())
            params = node.selectMABs() if node.hasParamMABs() else None
            searchPath.append(node)
            self.env.step(action, params)
        return node, searchPath

    @staticmethod
    def _expandNode(node, actions, reward):
        node.reward = reward
        for action in actions:
            # childEnvn = node.envn.step(action)
            history = copy.deepcopy(node.actionHistory)
            history.append(action)
            node.children[action] = MCTSNode(history)

    def _rollout(self):
        self.env.rollout()

    def _backup(self, searchPath, sim_value):
        value = sim_value
        for node in reversed(searchPath):
            node.valueLst.append(value)
            node.visitCount += 1
            value = node.reward + self.discount * value
            if node.hasParamMABs():
                node.backupMABs(value)

    def _oneSimulation(self):
        # now does not consider the root is not the game start
        self.env = StrategyGame(self.trainingSet, self.logic)
        selectNode, searchPath = self._select()
        print("Selected Node: " + str(selectNode))
        print("Selected Strategy ParseTree: " + str(self.env))
        if self.env.isTerminal():
            print("Terminal Strategy: no rollout")
            value = self.env.getValue(self.resDatabase)
        else:
            actions = self.env.legalActions()
            # now reward is always 0 at each step
            MCTS_RUN._expandNode(selectNode, actions, 0)
            self._rollout()
            print("Rollout Strategy: " + str(self.env))
            value = self.env.getValue(self.resDatabase)
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

    def getStrategyStat(self, strat):
        return self.resDatabase[strat]