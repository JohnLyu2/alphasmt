
MAX_TIMEOUT_STRAT = 3
MAX_BRANCH_DEPTH = 2

class DerivationNode():
    def __init__(self, children, expand_type, parent): # may not need parent
        if children is None:
            self.children = []
        else:
            self.children = children
        self.expandType = expand_type
        self.parent = parent
        
    # isTerminal and isLeaf is different as a tree may not be complete
    def isLeaf(self):
        if len(self.children):
            return False
        return True


    def applyRule(self, action, params):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        func = self.action_dict[action]
        func(params)
        self.expandType = action

class ProbeTerminal(DerivationNode):
    def __init__(self, name, value, parent):
        super().__init__(None, None, parent)
        self.name = name
        self.value = value

    def __str__(self):
        return f"{self.name} {self.value}"

    def isTerminal(self):
        return True

class ProbeSelectorNonterm(DerivationNode):
    def __init__(self, parent, children = None, expand_type = None):
        super().__init__(children, expand_type, parent)
        self.action_dict = {
            50: "num-consts", 
            51: "num-exprs",
            52: "size"
        }

    def __str__(self):
        if self.isLeaf():
            return f"<Probe + Value>"
        return str(self.children[0])
    
    def isTerminal(self):
        return False
    
    def legalActions(self, rollout = False):
        return list(self.action_dict.keys())
    
    # to be checked
    def applyRule(self, action, params):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        probe_name = self.action_dict[action]
        value = params['value']
        selected = ProbeTerminal(probe_name, value, self)
        self.children.append(selected)
        self.expandType = action

class TacticTerminal(DerivationNode):
    def __init__(self, name, params, parent): # tactic terminals do not have children 
        super().__init__(None, None, parent)
        self.name = name
        self.params = params
        # self._setParamMABs()

    def __str__(self):
        if not self.params:
          return self.name 
        tacticWithParamsStr = "(using-params " + self.name
        for param in self.params:
            paramStr = " :" + param + " " + str(self.params[param])
            tacticWithParamsStr += paramStr
        tacticWithParamsStr += ")"
        return tacticWithParamsStr

    def hasParams(self):
        return not self.params

    def isTerminal(self):
        return True

    # def clone(self):
    #     return TacticTerminal(self.name, self.params) # name and params are not modified; no deep copy here

class PreprocessNonterm(DerivationNode):
    def __init__(self, logic, parent, children = None, expand_type = None):
        super().__init__(children, expand_type, parent)
        self.logic = logic
        self.action_dict = {
            20: "simplify", 
            21: "propagate-values",
            22: "ctx-simplify",
            23: "elim-uncnstr",
            24: "solve-eqs",
            # 25 - 31 are QF_BV only
            25: "purify-arith",
            26: "max-bv-sharing",
            27: "aig",
            28: "reduce-bv-size",
            29: "ackermannize_bv",
            # 30: "bit-blast", # require simplifcation beforehand; otherwise report error
            # 32 - 34 are QF_NIA only
            32: "lia2card",
            33: "card2bv",
            34: "cofactor-term-ite"
        }

    def __str__(self):
        if self.isLeaf():
            return f"<PreprocessTactic>({self.logic})"
        return str(self.children[0])

    def isTerminal(self):
        return False

    def legalActions(self, rollout = False):
        actions = [i for i in range(20,25)]
        if self.logic == "QF_BV":
            return actions + [i for i in range(25,30)]
        elif self.logic == "QF_NIA":
            return actions + [i for i in range(32,35)]
        elif self.logic == "QF_NRA" or self.logic == "SAT":
            return actions
        else: 
            raise Exception("unexpected smt logic")

    def applyRule(self, action, params):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        tactic_name = self.action_dict[action]
        # params = TACTIC_PARAMS[tactic_name] if tactic_name in TACTIC_PARAMS else None
        selected = TacticTerminal(tactic_name, params, self)
        self.children.append(selected)
        self.expandType = action


class SolvingNonterm(DerivationNode):
    def __init__(self, logic, parent, children = None, expand_type = None):
        super().__init__(children, expand_type, parent)
        self.logic = logic
        self.action_dict = {
            10: "smt",
            11: "qfnra-nlsat", # not for BV
            12: "sat"
        }

    def __str__(self):
        if self.isLeaf():
            return f"<SolvingTactic>({self.logic})"
        return str(self.children[0])

    def isTerminal(self):
        return False

    def legalActions(self, rollout = False):
        actions = [10]
        if self.logic == "QF_BV":
            return actions
        elif self.logic == "QF_NIA" or self.logic == "QF_NRA":
            return actions + [11]
        elif self.logic == "SAT":
            return actions + [12]
        else: 
            raise Exception("unexpected smt logic")

    def applyRule(self, action, params):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        tactic_name = self.action_dict[action]
        # params = TACTIC_PARAMS[tactic_name] if tactic_name in TACTIC_PARAMS else None
        selected = TacticTerminal(tactic_name, params, self)
        self.children.append(selected)
        self.expandType = action


class StrategyNonterm(DerivationNode):
    def __init__(self, logic, timeout, timeout_status, branch_status, parent, children = None, expand_type = None, bv1blast = True):
        super().__init__(children, expand_type, parent)
        self.logic = logic
        self.timeout = timeout
        self.timeoutStatus = timeout_status # -1: itself a timed strategy; otherwise: number of timed strategies already tried beforehand
        self.branchStatus = branch_status # -1: no further branching allowed; otherwise: depth of branching (0 means root)
        self.bv1blast = bv1blast # for QF_BV, is bv1blast applicable; for other logics, it is meaningless
        self.action_dict = {
            0: self.applySolveRule,  # <Strategy> := <SolvingTactic>
            1: self.applyThenRule,  # <Strategy> := (then <PreprocessTactic> <Strategy>)
            2: self.applyTimeoutRule,  # <Strategy> := (or-else (try-for <Strategy>(QF_NIA/QF_BV) <timeout>) <Strategy>(QF_NIA/QF_BV))
            3: self.applyIfRule,  # <Strategy> := (if (> <num-probe> <percentile-value>) <Strategy> <Strategy>)
            5: self.apply2BVRule,  # <Strategy>(QF_NIA) := (or-else (then nla2bv <Strategy>(QF_BV)) <Strategy>(QF_NIA))
            6: self.applyBV1BlastRule,  # <Strategy>(QF_BV) := (if is-qfbv-eq (then bv1-blast <Strategy>(QF_BV) <Strategy>(QF_BV))
            7: self.applyBitBlastRule  # <Strategy>(BV) := (then simplify bit-blast <Strategy>(SAT))
        }

    def __str__(self):
        if self.isLeaf():
            return f"<Strategy>({self.logic})"
        # hardcoded
        if self.expandType == 1:
            returnStr = "(then " + \
                str(self.children[0]) + " " + str(self.children[1]) + ")"
            return returnStr
        elif self.expandType == 0:
            return str(self.children[0])
        elif self.expandType == 2:
            returnStr = f"(or-else (try-for {self.children[0]} {self.children[0].timeout * 1000}) {self.children[1]})"
            return returnStr
        elif self.expandType == 3:
            returnStr = f"(if (> {self.children[0]}) {self.children[1]} {self.children[2]})"
            return returnStr
        elif self.expandType == 5:
            returnStr = f"(or-else (then {self.children[0]} {self.children[1]}) {self.children[2]})"
            return returnStr
        elif self.expandType == 6:
            returnStr = f"(if is-qfbv-eq (then {self.children[0]} {self.children[1]}) {self.children[2]})"
            return returnStr
        elif self.expandType == 7:
            returnStr = f"(then {self.children[0]} {self.children[1]} {self.children[2]})"
            return returnStr
        else:
            raise Exception("unexpected action")

    def isTerminal(self):
        return False

    def legalActions(self, rollout = False):
        actions = [0, 1]
        if (not rollout) and self.timeoutStatus >= 0 and self.timeoutStatus < MAX_TIMEOUT_STRAT:
            actions.append(2)
        if (not rollout) and self.branchStatus >= 0 and self.branchStatus < MAX_BRANCH_DEPTH:
            actions.append(3)
        if (not rollout) and (self.logic == "QF_NIA" or self.logic == "QF_NRA"):
            actions.append(5)
        if (self.logic == "QF_BV"):
            actions.append(7)
            if self.bv1blast:
                actions.append(6)
        return actions

    def applyThenRule(self, params):
        self.children.append(PreprocessNonterm(self.logic, self))
        self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, branch_status=-1, parent=self, bv1blast=self.bv1blast))

    def applySolveRule(self, params):
        self.children.append(SolvingNonterm(self.logic, self)) 

    def applyTimeoutRule(self, params):
        assert(self.timeoutStatus != -1 and self.timeoutStatus < MAX_TIMEOUT_STRAT)
        tryTimeout = params["timeout"]
        remainTimeout = self.timeout - tryTimeout
        assert(remainTimeout > 0)
        self.children.append(StrategyNonterm(self.logic, tryTimeout, -1, branch_status=self.branchStatus, parent=self, bv1blast=self.bv1blast))
        self.children.append(StrategyNonterm(self.logic, remainTimeout, self.timeoutStatus+1, branch_status=self.branchStatus, parent=self, bv1blast=self.bv1blast))

    def applyIfRule(self, params):
        assert(self.branchStatus != -1 and self.branchStatus < MAX_BRANCH_DEPTH)
        self.children.append(ProbeSelectorNonterm(parent=self))
        self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, self.branchStatus+1, parent=self, bv1blast=self.bv1blast))
        self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, self.branchStatus+1, parent=self, bv1blast=self.bv1blast))

    def apply2BVRule(self, params):
        self.children.append(TacticTerminal("nla2bv", params, self))
        self.children.append(StrategyNonterm("QF_BV", self.timeout, self.timeoutStatus, branch_status=-1, parent=self)) # use <strategy> but with different tactic sets
        self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, branch_status=self.branchStatus, parent=self))

    def applyBV1BlastRule(self, params):
        self.children.append(TacticTerminal("bv1-blast", params, self))
        self.children.append(StrategyNonterm(logic="QF_BV", timeout=self.timeout, timeout_status=self.timeoutStatus, branch_status=-1, parent=self, bv1blast=False))
        self.children.append(StrategyNonterm(logic="QF_BV", timeout=self.timeout, timeout_status=self.timeoutStatus, branch_status=self.branchStatus, parent=self, bv1blast=False))

    def applyBitBlastRule(self, params):
        self.children.append(TacticTerminal(name="simplify", params=None, parent=self))
        self.children.append(TacticTerminal(name="bit-blast", params=params, parent=self)) # now the parameter for this action is for the tactic bit-blaster
        self.children.append(StrategyNonterm(logic="SAT", timeout=self.timeout, timeout_status=-1, branch_status=-1, parent=self, bv1blast=self.bv1blast)) # for sat formula do not introduce timeout

    # def clone(self):
    #     childrenCp = self.childrenClone()
    #     return StrategyNonterm(self.logic, childrenCp, self.expandType)
    
# CFG derivation tree
class DerivationAST():
    def __init__(self, logic, timeout, root = None):
        self.logic = logic
        if root is None:
            self.root = StrategyNonterm(logic, timeout, timeout_status = 0, branch_status = 0, parent = None)
        else:
            self.root = root

    def __str__(self):
        return str(self.root)

    @staticmethod
    def _findFstNonTermRec(search_stack):
        if not len(search_stack):
            return None
        node2Search = search_stack.pop()
        if node2Search.isLeaf():
            return node2Search
        else:
            for childNode in reversed(node2Search.children):
                if not childNode.isTerminal():
                    search_stack.append(childNode)
        return DerivationAST._findFstNonTermRec(search_stack)

    # return the depth-first first nontermial node in the tree; if nonexist, return None
    def findFstNonTerm(self):
        searchStack = [self.root]
        return DerivationAST._findFstNonTermRec(searchStack)

    def isTerminal(self):
        return not bool(self.findFstNonTerm())

    def legalActions(self, rollout = False):
        if self.isTerminal(): return []
        return self.findFstNonTerm().legalActions(rollout)

    def applyRule(self, action, params):
        assert (not self.isTerminal())
        node = self.findFstNonTerm()
        node.applyRule(action, params)

    def getRemainTime(self):
        assert (2 in self.legalActions())
        return self.findFstNonTerm().timeout

    # def clone(self):
    #     rootCopy = self.root.clone()
    #     return DerivationAST(self.logic, rootCopy)