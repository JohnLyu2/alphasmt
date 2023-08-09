from TacticNode import *

class FailableStratNonterm(DerivationNode):
    def __init__(self, logic, children = None, expand_type = None):
        super().__init__(children, expand_type)
        self.logic = logic
        self.action_dict = {
            5: self.applyBVRule, # <FailableStrategy>(QF_NIA) := (then nla2bv <Strategy>(BV))
            6: self.applyTryRule # <FailableStrategy>(QF_NIA/BV) := (try-for <Strategy>(QF_NIA/BV) <timeout>)
        }

    def __str__(self):
        if self.isLeaf():
            return f"<FailableStrategy>({self.logic})"
        if self.expandType == 5:
            returnStr = "(then " + \
                str(self.children[0]) + " " + str(self.children[1]) + ")"
            return returnStr
        if self.expandType == 6:
            returnStr = "(try-for " + \
                str(self.children[0]) + " " + "300" + ")" # to-do: make it modularize later
            return returnStr

    def isTerminal(self):
        return False

    def legalActions(self):
        if self.logic == "BV":
            return [6]
        return list(self.action_dict.keys())

    def applyBVRule(self, params):
        # params = TACTIC_PARAMS[tactic_name] if tactic_name in TACTIC_PARAMS else None
        self.children.append(TacticTerminal("nla2bv", params))
        self.children.append(StrategyNonterm("BV")) # use <strategy> but with different tactic sets

    def applyTryRule(self, params):
        self.children.append(StrategyNonterm(self.logic))

    def clone(self):
        childrenCp = self.childrenClone()
        return FailableStratNonterm(self.logic, childrenCp, self.expandType)


class StrategyNonterm(DerivationNode):
    def __init__(self, logic, children = None, expand_type = None):
        super().__init__(children, expand_type)
        self.logic = logic
        self.action_dict = {
            0: self.applySolveRule,  # <Strategy> := <SolvingTactic>
            1: self.applyThenRule,   # <Strategy> := (then <PreprocessTactic> <Strategy>)
            2: self.applyOrElseRule  # <Strategy> := (or-else <FailableStrategy> <Strategy>)
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
            returnStr = "(or-else " + \
                str(self.children[0]) + " " + str(self.children[1]) + ")"
            return returnStr

    def isTerminal(self):
        return False

    def applyThenRule(self, params):
        self.children.append(PreprocessNonterm(self.logic, params))
        self.children.append(StrategyNonterm(self.logic))

    def applySolveRule(self, params):
        self.children.append(SolvingNonterm(self.logic)) 

    def applyOrElseRule(self, params):
        self.children.append(FailableStratNonterm(self.logic))
        self.children.append(StrategyNonterm(self.logic))

    def clone(self):
        childrenCp = self.childrenClone()
        return StrategyNonterm(self.logic, childrenCp, self.expandType)
    
# CFG derivation tree
class DerivationAST():
    def __init__(self, logic, root = None):
        self.logic = logic
        if root is None:
            self.root = StrategyNonterm(logic)
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

    def clone(self):
        rootCopy = self.root.clone()
        return DerivationAST(self.logic, rootCopy)