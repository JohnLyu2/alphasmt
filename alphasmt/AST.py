from alphasmt.TacticNode import *


MAX_TIMEOUT_STRAT = 3
# class FailableStratNonterm(DerivationNode):
#     def __init__(self, logic, parent, children = None, expand_type = None):
#         super().__init__(children, expand_type, parent)
#         self.logic = logic
#         self.action_dict = {
#             5: self.applyBVRule, # <FailableStrategy>(QF_NIA) := (then nla2bv <Strategy>(BV))
#             6: self.applyTryRule # <FailableStrategy>(QF_NIA/BV) := (try-for <Strategy>(QF_NIA/BV) <timeout>)
#         }

#     def __str__(self):
#         if self.isLeaf():
#             return f"<FailableStrategy>({self.logic})"
#         if self.expandType == 5:
#             returnStr = "(then " + \
#                 str(self.children[0]) + " " + str(self.children[1]) + ")"
#             return returnStr
#         if self.expandType == 6:
#             returnStr = "(try-for " + \
#                 str(self.children[0]) + " " + "300" + ")" # to-do: make it modularize later
#             return returnStr

#     def isTerminal(self):
#         return False

#     def legalActions(self):
#         if self.logic == "BV":
#             return [6]
#         return list(self.action_dict.keys())

#     def applyBVRule(self, params):
#         # params = TACTIC_PARAMS[tactic_name] if tactic_name in TACTIC_PARAMS else None
#         self.children.append(TacticTerminal("nla2bv", params, self))
#         self.children.append(StrategyNonterm("BV", self)) # use <strategy> but with different tactic sets

#     def applyTryRule(self, params):
#         self.children.append(StrategyNonterm(self.logic, self))

    # def clone(self):
    #     childrenCp = self.childrenClone()
    #     return FailableStratNonterm(self.logic, childrenCp, self.expandType)


class StrategyNonterm(DerivationNode):
    def __init__(self, logic, timeout, timeout_status, parent, children = None, expand_type = None):
        super().__init__(children, expand_type, parent)
        self.logic = logic
        self.timeout = timeout
        self.timeoutStatus = timeout_status # -1: itself a timed strategy; otherwise: number of timed strategies already tried beforehand
        self.action_dict = {
            0: self.applySolveRule,  # <Strategy> := <SolvingTactic>
            1: self.applyThenRule,   # <Strategy> := (then <PreprocessTactic> <Strategy>)
            2: self.applyTimeoutRule,  # <Strategy> := (or-else (try-for <Strategy>(QF_NIA/BV) <timeout>) <Strategy>(QF_NIA/BV))
            5: self.apply2BVRule  # <Strategy>(QF_NIA) := (or-else (then nla2bv <Strategy>(BV)) <Strategy>(QF_NIA))
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

    def isTerminal(self):
        return False

    def legalActions(self):
        actions = [0, 1]
        if self.timeoutStatus >= 0 and self.timeoutStatus < MAX_TIMEOUT_STRAT:
            actions.append(2)
        if self.logic == "QF_NIA":
            actions.append(5)
        return actions

    def applyThenRule(self, params):
        self.children.append(PreprocessNonterm(self.logic, self))
        self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, self))

    def applySolveRule(self, params):
        self.children.append(SolvingNonterm(self.logic, self)) 

    def applyTimeoutRule(self, params):
        assert(self.timeoutStatus != -1 and self.timeoutStatus < MAX_TIMEOUT_STRAT)
        tryTimeout = params["timeout"]
        remainTimeout = self.timeout - tryTimeout
        assert(remainTimeout > 0)
        self.children.append(StrategyNonterm(self.logic, tryTimeout, -1, self))
        self.children.append(StrategyNonterm(self.logic, remainTimeout, self.timeoutStatus+1, self))

    def apply2BVRule(self, params):
        self.children.append(TacticTerminal("nla2bv", params, self))
        self.children.append(StrategyNonterm("BV", self.timeout, self.timeoutStatus, self)) # use <strategy> but with different tactic sets
        self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, self))

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

    def legalActions(self):
        if self.isTerminal(): return []
        return self.findFstNonTerm().legalActions()

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