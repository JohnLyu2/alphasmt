import random
import copy
from alphasmt.AST import DerivationAST
from alphasmt.Evaluator import Z3StrategyEvaluator


class StrategyGame():
    def __init__(self, training_set, logic):
        self.strategyAST = DerivationAST(logic)
        self.simulator = Z3StrategyEvaluator(training_set) # shallow copy for clone

    def __str__(self) -> str:
        return str(self.strategyAST)

    def isTerminal(self):
        return self.strategyAST.isTerminal()

    def legalActions(self):
        return self.strategyAST.legalActions()

    def step(self, action, params):
        self.strategyAST.applyRule(action, params)

    def rollout(self):
        assert(not self.isTerminal())
        while not self.isTerminal():
            actions = self.legalActions()
            # action = random.choice(actions)
            action = actions[0]
            self.step(action, None)

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