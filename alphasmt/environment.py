import random
import copy
from alphasmt.strat_tree import StrategyAST
from alphasmt.evaluator import Z3StrategyEvaluator
from alphasmt.utils import solvedNumReward, parNReward


class StrategyGame():
    def __init__(self, stage, training_lst, logic, timeout, s2_config, batch_size, tmp_dir):
        self.stage = stage
        self.benchmarks = training_lst
        if stage == 1:
            self.stratAST = StrategyAST(1, logic, timeout)
        else:
            s1_strats = s2_config['s1_strats']
            solver_dict = s2_config['solver_dict']
            preprocess_dict = s2_config['preprocess_dict']
            self.stratAST = StrategyAST(2, logic, timeout, s1_strats, solver_dict, preprocess_dict)
        self.simulator = Z3StrategyEvaluator(training_lst, timeout, batch_size, tmp_dir) # shallow copy for clone
        self.timeout = timeout

    def __str__(self) -> str:
        return str(self.stratAST)

    # def smt2str(self):
    #     return self.stratAST.smt2str()

    def isTerminal(self):
        return self.stratAST.isTerminal()

    # def getRemainTime(self):
    #     return self.stratAST.getRemainTime()

    def legalActions(self, rollout = False):
        return self.stratAST.legalActions(rollout)

    def step(self, action, params):
        self.stratAST.applyRule(action, params)

    def rollout(self):
        assert(not self.isTerminal())
        while not self.isTerminal():            
            actions = self.legalActions(rollout = True)
            action = random.choice(actions)
            # action = actions[0]
            params = None
            # if action in self.probes.keys():
            #     value = self.probes[action]['value'][1]
            #     params = {'value': value}
            self.step(action, params)

    # every entry in the resLst is (solved, time)
    def getS1ResLst(self, database):
        stratStr = str(self)
        if stratStr in database:  # does not account for nondeterministism now
            return database[stratStr]
        resLst = self.simulator.getResLst(stratStr)
        database[stratStr] = resLst
        return resLst

    def _get_linear_strategies(self):
        return self.stratAST.get_linear_strategies()

    # this function to be tested
    @staticmethod
    def solve_with_cache(benchID, ln_strats, database, timeout):
        time_remain = timeout
        solved = False
        time_used = 0
        for strat, st_timeout in ln_strats:
            cache_res, cache_time = database[tuple(strat)][benchID]
            if st_timeout < cache_time:
                time_remain -= st_timeout
                time_used += st_timeout
            elif time_remain < cache_time:
                time_remain = 0
                time_used += time_remain
            else:
                if cache_res == True:
                    solved = True
                    time_used += cache_time
                    break
                else:
                    time_remain -= cache_time
                    time_used += cache_time
            if time_used >= timeout:
                break
        return solved, time_used
        
    def getS2ResLst(self, database):
        res_lst = []
        for benchID in range(len(self.benchmarks)):
            # later add bench-specific ln strats
            ln_strats = self._get_linear_strategies()
            res_tuple = StrategyGame.solve_with_cache(benchID, ln_strats, database, self.timeout)
            res_lst.append(res_tuple)
        return res_lst
        
    # return a total reward of [0,1] according to the reward type
    def getValue(self, database, reward_type):
        assert (self.isTerminal())
        if self.stage == 1:
            resLst = self.getS1ResLst(database)
        else:
            resLst = self.getS2ResLst(database)
        if reward_type == '#solved':
            return solvedNumReward(resLst)
        elif reward_type == 'par2':
            return parNReward(resLst, 2, self.timeout)
        elif reward_type == 'par10':
            return parNReward(resLst, 10, self.timeout)
        else:
            raise Exception(f"Unknown value type {reward_type}")

    # def clone(self):
    #     cp = copy.copy(self)
    #     cp.stratAST = self.stratAST.clone()
    #     return cp