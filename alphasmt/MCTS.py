import logging
import math
import copy
from alphasmt.Environment import StrategyGame

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s','%Y-%m-%d %H:%M:%S'))
log.addHandler(log_handler)

INIT_Q = 1 # not important if not exponential recency-weighted average

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
        "hoist_mul": ["true","false"],
        "push_ite_bv": ["true","false"],
        "pull_cheap_ite": ["true","false"]
    },
    # "propagate-values"
    21: {
        "push_ite_bv": ["true","false"]
    },
    # "nla2bv" 
    5: {
        "nla2bv_max_bv_size": [4, 8, 16, 32, 64, 128]
    },
    # "qfnra-nlsat" 
    11: {
        "inline_vars": ["true","false"],
        "factor": ["true","false"],
        "seed": [i * 5 for i in range(6)]
    }
}

class MCTSNode():
    def __init__(self, is_mean, logger, c_ucb, alpha, probe_dict, action_history=[]):
        self.isMean = is_mean
        self.c_ucb = c_ucb
        self.alpha = alpha
        self.visitCount = 0
        self.actionHistory = action_history # 
        self.valueEst = 0
        self.children = {}
        self.reward = 0  # always 0 for now
        self.probeDict = probe_dict
        self._setParamMABs()
        self.logger = logger

    def __str__(self):
        return str(self.actionHistory)

    def isExpanded(self):
        return bool(self.children)

    def hasParamMABs(self):
        if len(self.actionHistory) == 0: return False
        lastestAction = self.actionHistory[-1]
        return (lastestAction in PARAMS.keys() or lastestAction in self.probeDict.keys())

    def _setParamMABs(self):
        if not self.hasParamMABs(): return
        lastestAction = self.actionHistory[-1]
        if lastestAction in PARAMS.keys():
            self.params = PARAMS[lastestAction]
        else:
            self.params = self.probeDict[lastestAction]
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
        exploreScore = self.c_ucb * \
            math.sqrt(math.log(self.visitCount + 1) / # check ucb 1
                      (visitCount + 0.001))
        ucb = qScore + exploreScore
        self.logger.debug(f"  Value of {action}: count: Q value: {qScore:.05f}; Exp: {exploreScore:.05f} ({visitCount}/{self.visitCount}); UCB: {ucb:.05f}")
        return ucb

    # rename parameter values; easily confuesed with the value of a node
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

    def backupMABs(self, reward):
        for param in self.params.keys():
            MABdict = self.MABs[param]
            selectedV = self.selected[param]

            if self.isMean:
                MABdict[selectedV][1] = (MABdict[selectedV][1] * MABdict[selectedV][0] + reward) / (MABdict[selectedV][0] + 1)
            else:
                MABdict[selectedV][1] = max(MABdict[selectedV][1], reward)
            MABdict[selectedV][0] += 1
            self.selected[param] = None


    # def value(self):
    #     if self.visitCount == 0:  # will this be called anytime?
    #         return 0
    #     return max(self.valueLst)

# A MCTS run starting at a particular node as root; this framework only works for deterministric state transition


class MCTS_RUN():
    def __init__(self, num_simulations, is_mean, training_set, logic, timeout, batch_size, log_folder, c_uct, c_ucb, alpha, test_factor, probe_dict, tmp_folder, root = None):
        # to-do: pack some into config
        self.numSimulations = num_simulations
        self.isMean = is_mean
        self.discount = 1  # now set to 1
        self.c_uct = c_uct
        self.c_ucb = c_ucb
        self.alpha = alpha
        self.trainingSet = training_set
        self.logic = logic
        self.timeout = timeout
        self.batchSize = batch_size
        self.resDatabase = {}
        self.sim_log = logging.getLogger("simulation")
        self.sim_log.setLevel(logging.DEBUG)
        simlog_handler = logging.FileHandler(f"{log_folder}/mcts_simulations.log")
        self.sim_log.addHandler(simlog_handler)
        self.testFactor = test_factor
        self.probeDict = probe_dict
        self.tmpFolder = tmp_folder
        if not root: root = MCTSNode(self.isMean, self.sim_log, c_ucb, alpha, self.probeDict)
        self.root = root
        self.bestReward = -1

    def _uct(self, childNode, parentNode, action):
        valueScore = childNode.reward + self.discount * childNode.valueEst
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

            # select in the order as in the list if the same UCT values; put more promising/safer actions earlier in legalActions()
            selected = None 
            bestUCT = -1
            nextNode = None 
            for action, childNode in node.children.items():
                uct = self._uct(childNode, node, action)
                if uct > bestUCT:
                    selected = action
                    bestUCT = uct
                    nextNode = childNode
            assert(bestUCT >= 0)
            node = nextNode
            self.sim_log.debug(f"  Selected action {selected}")
            remainTime = self.env.getRemainTime() if selected == 2 else None
            params = node.selectMABs(remainTime) if node.hasParamMABs() else None
            searchPath.append(node)
            self.env.step(selected, params)
        return node, searchPath

    @staticmethod
    def _expandNode(node, actions, reward, is_mean, c_ucb, alpha, probe_dict, logger):
        node.reward = reward
        for action in actions:
            history = copy.deepcopy(node.actionHistory)
            history.append(action)
            node.children[action] = MCTSNode(is_mean, logger, c_ucb, alpha, probe_dict, history)

    def _rollout(self):
        self.env.rollout()

    def _backup(self, searchPath, sim_value):
        value = sim_value
        for node in reversed(searchPath):
            if self.isMean:
                node.valueEst = (node.valueEst * node.visitCount + value) / (node.visitCount + 1)
            else:
                node.valueEst = max(node.valueEst, value)
            node.visitCount += 1
            value = node.reward + self.discount * value # not applicable now
            if node.hasParamMABs():
                node.backupMABs(value)

    def _oneSimulation(self):
        # now does not consider the root is not the game start
        self.env = StrategyGame(self.trainingSet, self.logic, self.timeout, self.probeDict, self.batchSize, test_factor=self.testFactor, tmp_dir=self.tmpFolder)
        selectNode, searchPath = self._select()
        self.sim_log.info("Selected Node: " + str(selectNode))
        self.sim_log.info("Selected Strategy ParseTree: " + str(self.env))
        if self.env.isTerminal():
            self.sim_log.info("Terminal Strategy: no rollout")
            value = self.env.getValue(self.resDatabase)
        else:
            actions = self.env.legalActions()
            # now reward is always 0 at each step
            MCTS_RUN._expandNode(selectNode, actions, 0, self.isMean, self.c_ucb, self.alpha, self.probeDict, self.sim_log)
            self._rollout()
            self.sim_log.info("Rollout Strategy: " + str(self.env))
            value = self.env.getValue(self.resDatabase)
        if value > self.bestReward:
            self.bestReward = value
            log.info(f"New best reward found: {value:.5f}")
        self.sim_log.info(f"Final Return: {value}\n")
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