from alphasmt.TacticNode import *

MAX_TIMEOUT_STRAT = 3

class StrategyNonterm(DerivationNode):
    def __init__(self, logic, timeout, timeout_status, parent, children = None, expand_type = None, bv1blast = True):
        super().__init__(children, expand_type, parent)
        self.logic = logic
        self.timeout = timeout
        self.timeoutStatus = timeout_status # -1: itself a timed strategy; otherwise: number of timed strategies already tried beforehand
        self.bv1blast = bv1blast # for QF_BV, is bv1blast applicable
        self.action_dict = {
            0: self.applySolveRule,  # <Strategy> := <SolvingTactic>
            1: self.applyThenRule,  # <Strategy> := (then <PreprocessTactic> <Strategy>)
            2: self.applyTimeoutRule,  # <Strategy> := (or-else (try-for <Strategy>(QF_NIA/QF_BV) <timeout>) <Strategy>(QF_NIA/QF_BV))
            5: self.apply2BVRule,  # <Strategy>(QF_NIA) := (or-else (then nla2bv <Strategy>(QF_BV)) <Strategy>(QF_NIA))
            6: self.applyBV1Blast  # <Strategy>(QF_BV) := (if is-qfbv-eq (then bv1-blast <Strategy>(QF_BV) <Strategy>(QF_BV))
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
        elif self.expandType == 5:
            returnStr = f"(or-else (then {self.children[0]} {self.children[1]}) {self.children[2]})"
            return returnStr
        elif self.expandType == 6:
            returnStr = f"(if is-qfbv-eq (then {self.children[0]} {self.children[1]}) {self.children[2]})"
            return returnStr

    def isTerminal(self):
        return False

    def legalActions(self, rollout = False):
        actions = [0, 1]
        if (not rollout) and self.timeoutStatus >= 0 and self.timeoutStatus < MAX_TIMEOUT_STRAT:
            actions.append(2)
        if (not rollout) and (self.logic == "QF_NIA" or self.logic == "QF_NRA"):
            actions.append(5)
        if (self.logic == "QF_BV") and self.bv1blast:
            actions.append(6)
        return actions

    def applyThenRule(self, params):
        self.children.append(PreprocessNonterm(self.logic, self))
        self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, self,bv1blast=self.bv1blast))

    def applySolveRule(self, params):
        self.children.append(SolvingNonterm(self.logic, self)) 

    def applyTimeoutRule(self, params):
        assert(self.timeoutStatus != -1 and self.timeoutStatus < MAX_TIMEOUT_STRAT)
        tryTimeout = params["timeout"]
        remainTimeout = self.timeout - tryTimeout
        assert(remainTimeout > 0)
        self.children.append(StrategyNonterm(self.logic, tryTimeout, -1, parent=self, bv1blast=self.bv1blast))
        self.children.append(StrategyNonterm(self.logic, remainTimeout, self.timeoutStatus+1, parent=self, bv1blast=self.bv1blast))

    def apply2BVRule(self, params):
        self.children.append(TacticTerminal("nla2bv", params, self))
        self.children.append(StrategyNonterm("QF_BV", self.timeout, self.timeoutStatus, self)) # use <strategy> but with different tactic sets
        self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, self))

    def applyBV1Blast(self, params):
        self.children.append(TacticTerminal("bv1-blast", params, self))
        self.children.append(StrategyNonterm(logic="QF_BV", timeout=self.timeout, timeout_status=self.timeoutStatus, parent=self, bv1blast=False))
        self.children.append(StrategyNonterm(logic="QF_BV", timeout=self.timeout, timeout_status=self.timeoutStatus, parent=self, bv1blast=False))




    # def clone(self):
    #     childrenCp = self.childrenClone()
    #     return StrategyNonterm(self.logic, childrenCp, self.expandType)
    
# CFG derivation tree
class DerivationAST():
    def __init__(self, logic, timeout, root = None):
        self.logic = logic
        if root is None:
            self.root = StrategyNonterm(logic, timeout, 0, None)
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