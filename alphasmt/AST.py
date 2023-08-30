from alphasmt.TacticNode import *

MAX_TIMEOUT_STRAT = 3
MAX_BRANCH_DEPTH = 2

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
        self.children.append(StrategyNonterm(self.logic, tryTimeout, -1, branch_status=-1, parent=self, bv1blast=self.bv1blast))
        self.children.append(StrategyNonterm(self.logic, remainTimeout, self.timeoutStatus+1, branch_status=-1, parent=self, bv1blast=self.bv1blast))

    def applyIfRule(self, params):
        assert(self.branchStatus != -1 and self.branchStatus < MAX_BRANCH_DEPTH)
        self.children.append(ProbeSelectorNonterm(parent=self))
        self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, self.branchStatus+1, parent=self, bv1blast=self.bv1blast))
        self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, self.branchStatus+1, parent=self, bv1blast=self.bv1blast))

    def apply2BVRule(self, params):
        self.children.append(TacticTerminal("nla2bv", params, self))
        self.children.append(StrategyNonterm("QF_BV", self.timeout, self.timeoutStatus, branch_status=-1, parent=self)) # use <strategy> but with different tactic sets
        self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, branch_status=-1, parent=self))

    def applyBV1BlastRule(self, params):
        self.children.append(TacticTerminal("bv1-blast", params, self))
        self.children.append(StrategyNonterm(logic="QF_BV", timeout=self.timeout, timeout_status=self.timeoutStatus, branch_status=-1, parent=self, bv1blast=False))
        self.children.append(StrategyNonterm(logic="QF_BV", timeout=self.timeout, timeout_status=self.timeoutStatus, branch_status=-1, parent=self, bv1blast=False))

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