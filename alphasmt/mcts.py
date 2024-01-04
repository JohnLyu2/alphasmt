import logging
import math
import copy
from alphasmt.environment import StrategyGame

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s','%Y-%m-%d %H:%M:%S'))
log.addHandler(log_handler)

INIT_Q = 0 

# to-do: move to somewhere else later/change it into inputs
# qf_lia may need to add some to simplify and ctx-simplify
PARAMS = {
    # timeout
    # 2: {
    #     "timeout": [2, 4, 8, 16]
    # },
    # "smt"
    10: {
        "random_seed": [i * 100 for i in range(6)]
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
    },
    # "add-bounds"
    36: {
        "add_bound_lower": [-2, -4, -8, -16, -32],
        "add_bound_upper": [2, 4, 8, 16, 32]
    },
    # "pb2bv"
    8: {
        "pb2bv_all_clauses_limit": [4, 8, 16, 32, 64],
    },
    # "lia2pb"
    38: {
        "lia2pb_max_bits": [16, 32, 64, 128],
    },
}

class MCTSNode():
    def __init__(self, is_mean, logger, c_ucb, is_log, action_history=[]):
        self.isMean = is_mean
        self.c_ucb = c_ucb
        # self.alpha = alpha
        self.visitCount = 0
        self.actionHistory = action_history # 
        self.valueEst = 0
        self.children = {}
        self.reward = 0  # always 0 for now
        self._setParamMABs()
        self.logger = logger
        self.is_log = is_log

    def __str__(self):
        return str(self.actionHistory)

    def isExpanded(self):
        return bool(self.children)

    def hasParamMABs(self):
        if len(self.actionHistory) == 0: return False
        lastestAction = self.actionHistory[-1]
        return lastestAction in PARAMS.keys()

    def _setParamMABs(self):
        if not self.hasParamMABs(): return
        lastestAction = self.actionHistory[-1]
        self.params = PARAMS[lastestAction]
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
        if self.is_log:
            self.logger.debug(f"  Value of {action}: Q value: {qScore:.05f}; Exp: {exploreScore:.05f} ({visitCount}/{self.visitCount}); UCB: {ucb:.05f}")
        return ucb

    # rename parameter values; easily confuesed with the value of a node
    def _selectMAB(self, param):
        MABdict = self.MABs[param]
        selected = None
        bestUCB = -1
        for valueCandidate, pair in MABdict.items():
            # if param == "timeout" and valueCandidate >= remain_time:
            #     continue
            ucb = self._ucb(pair, valueCandidate)
            if ucb > bestUCB:
                bestUCB = ucb
                selected = valueCandidate
        assert(bestUCB >= 0)
        return selected

    def selectMABs(self):
        for param in self.params.keys():
            if self.is_log:
                self.logger.debug(f"\n  Select MAB of {param}")
            selectV = self._selectMAB(param)
            if self.is_log:
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
    def __init__(self, stage, config, bench_lst, logic, value_type, log_folder, tmp_folder, batch_size = 1, root = None):
        self.stage = stage
        self.config = config
        self.numSimulations = config['sim_num']
        self.isMean = config['is_mean_est']
        self.discount = 1  # now set to 1
        self.c_uct = config['c_uct']
        # self.alpha = alpha
        self.trainingLst = bench_lst
        self.logic = logic
        self.timeout = config['timeout']
        self.is_log = config['is_log']
        self.valueType = value_type
        self.batchSize = batch_size
        if self.stage == 1:
            self.c_ucb = config['c_ucb']
            self.resDatabase = {}
        else:
            self.c_ucb = None
            self.resDatabase = config['s2dict']['res_cache']
        self.sim_log = logging.getLogger(f"s{self.stage}mcts")
        self.sim_log.propagate = False
        self.sim_log.setLevel(logging.DEBUG)
        simlog_handler = logging.FileHandler(f"{log_folder}/s{self.stage}mcts.log")
        self.sim_log.addHandler(simlog_handler)
        self.tmpFolder = tmp_folder
        if not root: root = MCTSNode(self.isMean, self.sim_log, self.c_ucb, self.is_log)
        self.root = root
        self.bestReward = -1
        self.bestStrat = None

    def _uct(self, childNode, parentNode, action):
        valueScore = childNode.reward + self.discount * childNode.valueEst
        exploreScore = self.c_uct * \
            math.sqrt(math.log(parentNode.visitCount) /
                      (childNode.visitCount + 0.001))
        uct = valueScore + exploreScore
        if self.is_log:
            self.sim_log.debug(f"  Value of {action}: Q value: {valueScore:.05f}; Exp: {exploreScore:.05f} ({childNode.visitCount}/{parentNode.visitCount}); UCT: {uct:.05f}")
        return uct

    def _select(self):
        searchPath = [self.root]
        node = self.root
        # does not consider the root has MABs
        while node.isExpanded() and not self.env.isTerminal():
            if self.is_log:
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
            if self.is_log:
                self.sim_log.debug(f"  Selected action {selected}")
            # remainTime = self.env.getRemainTime() if selected == 2 else None
            params = node.selectMABs() if node.hasParamMABs() else None
            searchPath.append(node)
            self.env.step(selected, params)
        return node, searchPath

    def _expandNode(self, node, actions, reward):
        node.reward = reward
        for action in actions:
            history = copy.deepcopy(node.actionHistory)
            history.append(action)
            node.children[action] = MCTSNode(self.isMean, self.sim_log, self.c_ucb, self.is_log, history)

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
        self.env = StrategyGame(self.stage, self.trainingLst, self.logic, self.timeout, self.config, self.batchSize, tmp_dir=self.tmpFolder)
        selectNode, searchPath = self._select()
        if self.is_log:
            self.sim_log.info("Selected Node: " + str(selectNode))
            self.sim_log.info("Selected Strategy ParseTree: " + str(self.env))
        if self.env.isTerminal():
            if self.is_log:
                self.sim_log.info("Terminal Strategy: no rollout")
            value = self.env.getValue(self.resDatabase, self.valueType)
        else:
            actions = self.env.legalActions()
            # now reward is always 0 at each step
            self._expandNode(selectNode, actions, 0)
            self._rollout()
            if self.is_log:
                self.sim_log.info(f"Rollout Strategy: {self.env}")
            value = self.env.getValue(self.resDatabase, self.valueType)
        if value > self.bestReward:
            self.bestReward = value
            self.bestStrat = str(self.env)
            log.info(f"At sim {self.num_sim}, new best reward found: {value:.5f}")
        if self.is_log:
            self.sim_log.info(f"Final Return: {value}\n")
        self._backup(searchPath, value)

    def start(self):
        for i in range(self.numSimulations):
            self.num_sim = i
            if self.stage == 1:
                log.info(f"Simulation {i} starts")
            if self.is_log:
                self.sim_log.info(f"Simulation {i} starts")
            self._oneSimulation()

    def bestNStrategies(self, n):
        if n > len(self.resDatabase):
            n = len(self.resDatabase)
        return sorted(self.resDatabase, key=self.resDatabase.get, reverse=True)[:n]

    def getStrategyStat(self, strat):
        return self.resDatabase[strat]
    
    def getResDict(self):
        return self.resDatabase
    
    def getBestStrat(self):
        return self.bestStrat
