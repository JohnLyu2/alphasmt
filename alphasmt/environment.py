import random
import copy
from alphasmt.cfg_tree import DerivationAST
from alphasmt.evaluator import Z3StrategyEvaluator


class StrategyGame():
    def __init__(self, training_lst, logic, timeout, probe_dict, batch_size, test_factor, tmp_dir):
        self.strategyAST = DerivationAST(logic, timeout)
        self.simulator = Z3StrategyEvaluator(training_lst, timeout, batch_size, test_factor, tmp_dir) # shallow copy for clone
        self.probes = probe_dict

    def __str__(self) -> str:
        return str(self.strategyAST)

    def isTerminal(self):
        return self.strategyAST.isTerminal()

    def getRemainTime(self):
        return self.strategyAST.getRemainTime()

    def legalActions(self, rollout = False):
        return self.strategyAST.legalActions(rollout)

    def step(self, action, params):
        self.strategyAST.applyRule(action, params)

    def rollout(self):
        assert(not self.isTerminal())
        while not self.isTerminal():
            actions = self.legalActions(rollout = True)
            action = random.choice(actions)
            # action = actions[0]
            params = None
            if action in self.probes.keys():
                value = self.probes[action]['value'][1]
                params = {'value': value}
            self.step(action, params)

    def getValue(self, database):
        assert (self.isTerminal())
        stratStr = str(self.strategyAST)
        if stratStr in database:  # does not account for nondeterministism now
            return database[stratStr]
        reward = self.simulator.getReward(stratStr)
        database[stratStr] = reward
        return reward

    def clone(self):
        cp = copy.copy(self)
        cp.strategyAST = self.strategyAST.clone()
        return cp