import logging
import math
import copy
from alphasmt.Environment import StrategyGame

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s'))
log.addHandler(log_handler)

INIT_Q = 1
C_UCB = 0.1
STEP_ALPHA = 0.3

C_UCT = 0.3

# to-do: move to somewhere else later/change it into inputs
PARAMS = {
    # timeout
    2: {
        "timeout": [2, 4, 8, 16]
    },
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
    def __init__(self, logger, action_history=[]):
        # self.envn = envn
        self.visitCount = 0
        self.actionHistory = action_history # 
        self.valueLst = []
        self.children = {}
        self.reward = 0  # always 0 for now
        self._setParamMABs()
        self.logger = logger

    def __str__(self):
        return str(self.actionHistory)

    def isExpanded(self):
        return bool(self.children)

    def hasParamMABs(self):
        return len(self.actionHistory)>0 and self.actionHistory[-1] in PARAMS.keys()

    def _setParamMABs(self):
        if not self.hasParamMABs(): return
        self.params = PARAMS[self.actionHistory[-1]]
        self.MABs = {}
        self.selected = {}
        for param in self.params.keys():
            MABdict = {}
            for paramValue in self.params[param]:
                MABdict[paramValue] = [0, INIT_Q] # (visit count, q estimation) 
            self.MABs[param] = MABdict
            self.selected[param] = None

    # the argument action is only for log
    def _ucb(self, action_pair, action):
        visitCount, qScore = action_pair
        exploreScore = C_UCB * \
            math.sqrt(math.log(self.visitCount + 1) / # check ucb 1
                      (visitCount + 0.001))
        ucb = qScore + exploreScore
        self.logger.debug(f"  Value of {action}: count: Q value: {qScore:.05f}; Exp: {exploreScore:.05f} ({visitCount}/{self.visitCount}); UCB: {ucb:.05f}")
        return ucb

    def _selectMAB(self, param, remain_time):
        MABdict = self.MABs[param]
        selected = None
        bestUCB = -1
        for valueCandidate, pair in MABdict.items():
            if param == "timeout" and valueCandidate >= remain_time:
                continue
            ucb = self._ucb(pair, valueCandidate)
            if ucb > bestUCB:
                bestUCB = ucb
                selected = valueCandidate
        assert(bestUCB > 0)
        return selected

    def selectMABs(self, remain_time):
        for param in self.params.keys():
            self.logger.debug(f"\n  Select MAB of {param}")
            selectV = self._selectMAB(param, remain_time)
            self.logger.debug(f"  Selected value: {selectV}\n")
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
    def __init__(self, num_simulations, training_set, logic, timeout, batch_size, log_folder, root = None):
        # to-do: pack some into config
        self.numSimulations = num_simulations
        self.discount = 1  # now set to 1
        self.c_uct = C_UCT 
        self.trainingSet = training_set
        self.logic = logic
        self.timeout = timeout
        self.batchSize = batch_size
        self.resDatabase = {}
        self.sim_log = logging.getLogger("simulation")
        self.sim_log.setLevel(logging.DEBUG)
        simlog_handler = logging.FileHandler(f"{log_folder}/mcts_simulations.log")
        self.sim_log.addHandler(simlog_handler)
        if not root: root = MCTSNode(self.sim_log)
        self.root = root

    def _uct(self, childNode, parentNode, action):
        valueScore = 0
        if childNode.visitCount > 0:
            valueScore = childNode.reward + self.discount * childNode.value()
        exploreScore = self.c_uct * \
            math.sqrt(math.log(parentNode.visitCount) /
                      (childNode.visitCount + 0.001))
        uct = valueScore + exploreScore
        self.sim_log.debug(f"  Value of {action}: count: Q value: {valueScore:.05f}; Exp: {exploreScore:.05f} ({childNode.visitCount}/{parentNode.visitCount}); UCT: {uct:.05f}")
        return uct

    def _select(self):
        searchPath = [self.root]
        node = self.root
        # does not consider the root has MABs
        while node.isExpanded() and not self.env.isTerminal():
            self.sim_log.debug(f"\n  Select at {node}")
            # may add randomness when the UCTs are the same
            _, action, node = max((self._uct(childNode, node, action), action, childNode)
                                  for action, childNode in node.children.items())
            self.sim_log.debug(f"  Selected action {action}")
            remainTime = self.env.getRemainTime() if action == 2 else None
            params = node.selectMABs(remainTime) if node.hasParamMABs() else None
            searchPath.append(node)
            self.env.step(action, params)
        return node, searchPath

    @staticmethod
    def _expandNode(node, actions, reward, logger):
        node.reward = reward
        for action in actions:
            # childEnvn = node.envn.step(action)
            history = copy.deepcopy(node.actionHistory)
            history.append(action)
            node.children[action] = MCTSNode(logger, history)

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
        self.env = StrategyGame(self.trainingSet, self.logic, self.timeout, self.batchSize)
        selectNode, searchPath = self._select()
        self.sim_log.info("Selected Node: " + str(selectNode))
        self.sim_log.info("Selected Strategy ParseTree: " + str(self.env))
        if self.env.isTerminal():
            self.sim_log.info("Terminal Strategy: no rollout")
            value = self.env.getValue(self.resDatabase)
        else:
            actions = self.env.legalActions()
            # now reward is always 0 at each step
            MCTS_RUN._expandNode(selectNode, actions, 0, self.sim_log)
            self._rollout()
            self.sim_log.info("Rollout Strategy: " + str(self.env))
            value = self.env.getValue(self.resDatabase)
        self.sim_log.info("Final Return: " + str(value) + "\n")
        self._backup(searchPath, value)

    def start(self):
        for i in range(self.numSimulations):
            log.info(f"Simulation {i} starts")
            self.sim_log.info(f"Simulation {i} starts")
            self._oneSimulation()

    def bestNStrategies(self, n):
        if n > len(self.resDatabase):
            n = len(self.resDatabase)
        return sorted(self.resDatabase, key=self.resDatabase.get, reverse=True)[:n]

    def getStrategyStat(self, strat):
        return self.resDatabase[strat]