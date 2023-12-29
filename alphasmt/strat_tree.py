import copy
from alphasmt.selector import search_next_action

MAX_TIMEOUT_STRAT = 3
MAX_BRANCH_DEPTH = 2
TIMEOUTS = [1, 2, 4, 8]

class ASTNode():
    def __init__(self):
        self.children = []
        self.parent = None
        
    def isLeaf(self):
        return len(self.children) == 0

    def isTactic(self):
        return False

    # make change this to unify with the way in S2Strategy
    def applyRule(self, action, params):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        func = self.action_dict[action]
        func(params)

    # only used for leaf nodes
    def addChildren(self, children):
        assert (self.isLeaf())
        assert (len(children) > 0)
        self.children = children
        for i in range(len(children)):
            children[i].parent = self
            children[i].pos = i

    # replace the pos'th child with the new children
    def replaceChild(self, child, pos):
        assert (not self.isLeaf())
        assert (pos < len(self.children))
        self.children[pos] = child
        child.parent = self
        child.pos = pos
        
class Root(ASTNode):
    def __init__(self):
        super().__init__()

    def __str__(self):
        assert len(self.children) == 1
        return str(self.children[0])

    def isTerminal(self):
        return True
    
    def getLnStrats(self, timeout):
        return self.children[0].getLnStrats([([], timeout)])
    
class TimeOutNode0(ASTNode):
    def __init__(self, remain_time, s1_lst, solver_dict, preprocess_dict):
        super().__init__()
        self.remain_time = remain_time
        self.s1strat_lst = s1_lst
        self.solver_dict = solver_dict
        self.preprocess_dict = preprocess_dict

    def __str__(self):
        return f"<TimeOutNode>"

    def isTerminal(self):
        return False

    def legalActions(self, rollout = False):
        candidates = TIMEOUTS
        return [t for t in candidates if t < self.remain_time]

    def applyRule(self, action, params):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        branchingNode = TimeOutNode1(action)
        tryout_strat = S2Strategy(action, self.s1strat_lst, self.solver_dict, self.preprocess_dict)
        default_strat = S2Strategy(self.remain_time - action, self.s1strat_lst, self.solver_dict, self.preprocess_dict)
        self.parent.replaceChild(branchingNode, self.pos)
        branchingNode.addChildren([tryout_strat, default_strat])

class TimeOutNode1(ASTNode):
    def __init__(self, timeout):
        super().__init__()
        self.timeout = timeout

    def __str__(self):
        return f"(or-else (try-for {self.children[0]} {self.timeout * 1000}) {self.children[1]})"

    def isTerminal(self):
        return True

    def getLnStrats(self, precede_strats):
        assert len(precede_strats) == 1
        precede_strat = precede_strats[0][0]
        precede_timeout = precede_strats[0][1]
        assert (precede_timeout > self.timeout)
        prec_leftcp = [(copy.deepcopy(precede_strat), self.timeout)]
        prec_rightcp = [(copy.deepcopy(precede_strat), precede_timeout)]
        return self.children[0].getLnStrats(prec_leftcp) + self.children[1].getLnStrats(prec_rightcp)

# class ProbeTerminal(ASTNode):
#     def __init__(self, name, value, parent):
#         super().__init__()
#         self.name = name
#         self.value = value

#     def __str__(self):
#         return f"{self.name} {self.value}"

#     def isTerminal(self):
#         return True

# class ProbeSelectorNonterm(ASTNode):
#     def __init__(self):
#         super().__init__()
#         self.action_dict = {
#             50: "num-consts", 
#             51: "num-exprs",
#             52: "size"
#         }

#     def __str__(self):
#         if self.isLeaf():
#             return f"<Probe + Value>"
#         return str(self.children[0])
    
#     def isTerminal(self):
#         return False
    
#     def legalActions(self, rollout = False):
#         return list(self.action_dict.keys())
    
#     # to be checked
#     def applyRule(self, action, params):
#         assert (self.isLeaf())
#         assert (action in self.legalActions())
#         probe_name = self.action_dict[action]
#         value = params['value']
#         selected = ProbeTerminal(probe_name, value, self)
#         self.children.append(selected)

class TacticNode(ASTNode):
    def __init__(self, name, params, s2actID = None): # tactic terminals do not have children 
        super().__init__()
        self.name = name
        self.params = params
        self.s2actID = s2actID
        # self._setParamMABs()

    def _tactic_str(self):
        if not self.params: return f"{self.name}"
        tactic_str = f"(using-params {self.name}"
        for param in self.params:
            paramStr = " :" + param + " " + str(self.params[param])
            tactic_str += paramStr
        tactic_str += ")"
        return tactic_str

    def __str__(self):
        tactic_str = self._tactic_str()
        if self.isLeaf():
            return tactic_str
        elif self._is_first_then():
            return f"(then {tactic_str} {self.children[0]})"
        else:
            return f"{tactic_str} {self.children[0]}"

    def isTactic(self):
        return True

    def _is_first_then(self):
        if self.isLeaf(): return False
        if self.parent.isTactic(): return False
        return True
        
    # def _is_last_then(self):
    #     if not self.isLeaf(): return False
    #     if self.parent.isTactic(): return True
    #     return False

    # def smt2str(self):
    #     tactic_str = self._tactic_str()
    #     if self._is_first_then():
    #         tactic_str = f"(then {tactic_str}"
    #     elif self._is_last_then():
    #         tactic_str = f"{tactic_str})"
    #     if self.isLeaf():
    #         return tactic_str
    #     else:
    #         return f"{tactic_str} {self.children[0].smt2str()}"

    # in stage 2, tactic parameters are part of the name string; always return False for stage 2
    def hasParams(self):
        return not self.params

    def isTerminal(self):
        return True

    def getLnStrats(self, precede_strats):
        for strat_tup in precede_strats:
            strat_tup[0].append(self.s2actID)
        if self.isLeaf():
            return precede_strats
        return self.children[0].getLnStrats(precede_strats)

    # def clone(self):
    #     return TacticTerminal(self.name, self.params) # name and params are not modified; no deep copy here

class PreprocessTactic(ASTNode):
    def __init__(self, logic):
        super().__init__()
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
            34: "cofactor-term-ite",
            # 35 - 38 are QF_LIA only
            35: "propagate-ineqs",
            36: "add-bounds",
            37: "normalize-bounds",
            38: "lia2pb",
        }

    def __str__(self):
        # if self.isLeaf():
        #     return f"<PreprocessTactic>({self.logic})"
        return f"<PreprocessTactic>({self.logic}) {self.children[0]}"

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
        elif self.logic == "QF_LIA":
            return actions + [i for i in range(35,39)]
        else: 
            raise Exception("unexpected smt logic")

    def applyRule(self, action, params):
        assert (action in self.legalActions())
        tactic_name = self.action_dict[action]
        # params = TACTIC_PARAMS[tactic_name] if tactic_name in TACTIC_PARAMS else None
        selected = TacticNode(tactic_name, params, action)
        self.parent.replaceChild(selected, self.pos)
        selected.addChildren(self.children)

class SolverTactic(ASTNode):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.action_dict = {
            10: "smt",
            11: "qfnra-nlsat", # for QF_NIA and QF_NRA
            12: "sat",
            13: "qfbv", # only for QF_BV
            14: "qfnia", # only for QF_NIA
            15: "qfnra", # only for QF_NRA
            16: "qflia" # only for QF_LIA
        }

    def __str__(self):
        return f"<SolverTactic>({self.logic})"

    def isTerminal(self):
        return False

    def legalActions(self, rollout = False):
        actions = [10]
        if self.logic == "QF_BV":
            return actions + [13]
        elif self.logic == "QF_NIA":
            return actions + [11, 14]
        elif self.logic == "QF_NRA":
            return actions + [11, 15]
        elif self.logic == "QF_LIA":
            return actions + [16]
        elif self.logic == "SAT":
            return actions + [12]
        else: 
            raise Exception("unexpected smt logic")

    def applyRule(self, action, params):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        tactic_name = self.action_dict[action]
        selected = TacticNode(tactic_name, params, action)
        self.parent.replaceChild(selected, self.pos)

class S1Strategy(ASTNode):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.action_dict = {
            0: self.applySolverRule,  # <S1Strategy> := <SolverTactic>
            1: self.applyThenRule,  # <S1Strategy> := (then <PreprocessTactic> <S1Strategy>)
            5: self.applyNla2BVRule,  # <S1Strategy>(QF_NIA/QF_NRA) := (then nla2bv <S1Strategy>(QF_BV))
            7: self.applyBitBlastRule,  # <S1Strategy>(BV) := (then simplify bit-blast <S1Strategy>(SAT))
            8: self.applyPb2BvRule # <S1Strategy>(QF_LIA) := (then pb2bv <S1Strategy>(QF_BV))
        }

    def __str__(self):
        return f"<S1Strategy>({self.logic})"

    def isTerminal(self):
        return False
        
    def legalActions(self, rollout = False):
        actions = [0, 1]
        if (not rollout) and (self.logic == "QF_NIA" or self.logic == "QF_NRA"):
            actions.append(5)
        if (self.logic == "QF_BV"):
            actions.append(7)
        if (self.logic == "QF_LIA"):
            actions.append(8)
        return actions

    def applySolverRule(self, params):
        assert self.parent
        self.parent.replaceChild(SolverTactic(self.logic), self.pos)

    def applyThenRule(self, params):
        assert self.parent
        preprocessor = PreprocessTactic(self.logic)
        self.parent.replaceChild(preprocessor, self.pos)
        preprocessor.addChildren([S1Strategy(self.logic)])

    def applyNla2BVRule(self, params):
        nla2bv_node = TacticNode("nla2bv", params)
        self.parent.replaceChild(nla2bv_node, self.pos)
        qf_bv_strat = S1Strategy("QF_BV")
        nla2bv_node.addChildren([qf_bv_strat])

    def applyPb2BvRule(self, params):
        pb2bv_node = TacticNode("pb2bv", params)
        self.parent.replaceChild(pb2bv_node, self.pos)
        qf_bv_strat = S1Strategy("QF_BV")
        pb2bv_node.addChildren([qf_bv_strat])

    def applyBitBlastRule(self, params):
        simplify_node = TacticNode("simplify", None)
        bit_blast_node = TacticNode("bit-blast", params)
        self.parent.replaceChild(simplify_node, self.pos)
        simplify_node.addChildren([bit_blast_node])
        bit_blast_node.addChildren([S1Strategy("SAT")])

class S2Strategy(ASTNode):
    def __init__(self, timeout, s1_lst, solver_dict, preprocess_dict):
        super().__init__()
        self.timeout = timeout
        self.action_lst = [2,# timeout rule
                           ]
        self.solver_action_dict = solver_dict
        self.preprocess_action_dict = preprocess_dict
        self.s1strat_lst = s1_lst

    def __str__(self):
        return f"<S2Strategy>"

    def isTerminal(self):
        return False
    
    def getCurActPath(self):
        reverse_path = []
        cur_node = self.parent
        while cur_node:
            if cur_node.isTactic():
                reverse_path.append(cur_node.s2actID)
            cur_node = cur_node.parent
        return list(reversed(reverse_path))

    def legalActions(self, rollout = False): 
        cur_path = self.getCurActPath()
        tac_actions = search_next_action(cur_path, self.s1strat_lst)
        legal_actions = tac_actions
        if (not rollout) and (len(tac_actions) > 1) and (self.timeout > TIMEOUTS[0]):
            legal_actions.append(2) # timeout rule
        return legal_actions 
    
    def applySolverRule(self, action):
        tactic, tac_params = self.solver_action_dict[action]
        tac_node = TacticNode(tactic, tac_params, action)
        self.parent.replaceChild(tac_node, self.pos)

    def applyThenRule(self, action):
        tactic, tac_params = self.preprocess_action_dict[action]
        tac_node = TacticNode(tactic, tac_params, action)
        self.parent.replaceChild(tac_node, self.pos)
        s2strat = S2Strategy(self.timeout, self.s1strat_lst, self.solver_action_dict, self.preprocess_action_dict)
        tac_node.addChildren([s2strat])

    def applyTimeoutRule(self):
        self.parent.replaceChild(TimeOutNode0(self.timeout, self.s1strat_lst, self.solver_action_dict, self.preprocess_action_dict), self.pos)

    def applyRule(self, action, params): # params is no use here
        assert (self.isLeaf())
        assert (action in self.legalActions())
        if action == 2: # timeout rule
            self.applyTimeoutRule()
        elif action in self.solver_action_dict:
            self.applySolverRule(action)
        elif action in self.preprocess_action_dict:
            self.applyThenRule(action)
        else:
            raise Exception("unexpected action")

# class StrategyNonterm(ASTNode):
#     def __init__(self, logic, timeout, timeout_status, branch_status, parent, children = None, expand_type = None, bv1blast = True):
#         super().__init__(children, expand_type, parent)
#         self.logic = logic
#         self.timeout = timeout
#         self.timeoutStatus = timeout_status # -1: itself a timed strategy; otherwise: number of timed strategies already tried beforehand
#         self.branchStatus = branch_status # -1: no further branching allowed; otherwise: depth of branching (0 means root)
#         self.bv1blast = bv1blast # for QF_BV, is bv1blast applicable; for other logics, it is meaningless
#         self.action_dict = {
#             0: self.applySolveRule,  # <Strategy> := <SolverTactic>
#             1: self.applyThenRule,  # <Strategy> := (then <PreprocessTactic> <Strategy>)
#             2: self.applyTimeoutRule,  # <Strategy> := (or-else (try-for <Strategy> <timeout>) <Strategy>)
#             3: self.applyIfRule,  # <Strategy> := (if (> <num-probe> <percentile-value>) <Strategy> <Strategy>)
#             5: self.apply2BVRule,  # <Strategy>(QF_NIA) := (or-else (then nla2bv <Strategy>(QF_BV)) <Strategy>(QF_NIA))
#             6: self.applyBV1BlastRule,  # <Strategy>(QF_BV) := (if is-qfbv-eq (then bv1-blast <Strategy>(QF_BV) <Strategy>(QF_BV))
#             7: self.applyBitBlastRule  # <Strategy>(BV) := (then simplify bit-blast <Strategy>(SAT))
#         }

#     def __str__(self):
#         if self.isLeaf():
#             return f"<Strategy>({self.logic})"
#         # hardcoded
#         if self.expandType == 1:
#             returnStr = "(then " + \
#                 str(self.children[0]) + " " + str(self.children[1]) + ")"
#             return returnStr
#         elif self.expandType == 0:
#             return str(self.children[0])
#         elif self.expandType == 2:
#             returnStr = f"(or-else (try-for {self.children[0]} {self.children[0].timeout * 1000}) {self.children[1]})"
#             return returnStr
#         elif self.expandType == 3:
#             returnStr = f"(if (> {self.children[0]}) {self.children[1]} {self.children[2]})"
#             return returnStr
#         elif self.expandType == 5:
#             returnStr = f"(or-else (then {self.children[0]} {self.children[1]}) {self.children[2]})"
#             return returnStr
#         elif self.expandType == 6:
#             returnStr = f"(if is-qfbv-eq (then {self.children[0]} {self.children[1]}) {self.children[2]})"
#             return returnStr
#         elif self.expandType == 7:
#             returnStr = f"(then {self.children[0]} {self.children[1]} {self.children[2]})"
#             return returnStr
#         else:
#             raise Exception("unexpected action")

#     def isTerminal(self):
#         return False

#     def legalActions(self, rollout = False):
#         actions = [0, 1]
#         if (not rollout) and self.timeoutStatus >= 0 and self.timeoutStatus < MAX_TIMEOUT_STRAT:
#             actions.append(2)
#         if (not rollout) and self.branchStatus >= 0 and self.branchStatus < MAX_BRANCH_DEPTH:
#             actions.append(3)
#         if (not rollout) and (self.logic == "QF_NIA" or self.logic == "QF_NRA"):
#             actions.append(5)
#         if (self.logic == "QF_BV"):
#             actions.append(7)
#             if self.bv1blast:
#                 actions.append(6)
#         return actions

#     def applyThenRule(self, params):
#         self.children.append(PreprocessTactic(self.logic, self))
#         self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, branch_status=-1, parent=self, bv1blast=self.bv1blast))

#     def applySolveRule(self, params):
#         self.children.append(SolverTactic(self.logic, self)) 

#     def applyTimeoutRule(self, params):
#         assert(self.timeoutStatus != -1 and self.timeoutStatus < MAX_TIMEOUT_STRAT)
#         tryTimeout = params["timeout"]
#         remainTimeout = self.timeout - tryTimeout
#         assert(remainTimeout > 0)
#         self.children.append(StrategyNonterm(self.logic, tryTimeout, -1, branch_status=self.branchStatus, parent=self, bv1blast=self.bv1blast))
#         self.children.append(StrategyNonterm(self.logic, remainTimeout, self.timeoutStatus+1, branch_status=self.branchStatus, parent=self, bv1blast=self.bv1blast))

#     def applyIfRule(self, params):
#         assert(self.branchStatus != -1 and self.branchStatus < MAX_BRANCH_DEPTH)
#         self.children.append(ProbeSelectorNonterm(parent=self))
#         self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, self.branchStatus+1, parent=self, bv1blast=self.bv1blast))
#         self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, self.branchStatus+1, parent=self, bv1blast=self.bv1blast))

#     def apply2BVRule(self, params):
#         self.children.append(TacticNode("nla2bv", params, self))
#         self.children.append(StrategyNonterm("QF_BV", self.timeout, self.timeoutStatus, branch_status=-1, parent=self)) # use <strategy> but with different tactic sets
#         self.children.append(StrategyNonterm(self.logic, self.timeout, self.timeoutStatus, branch_status=self.branchStatus, parent=self))

#     def applyBV1BlastRule(self, params):
#         self.children.append(TacticNode("bv1-blast", params, self))
#         self.children.append(StrategyNonterm(logic="QF_BV", timeout=self.timeout, timeout_status=self.timeoutStatus, branch_status=-1, parent=self, bv1blast=False))
#         self.children.append(StrategyNonterm(logic="QF_BV", timeout=self.timeout, timeout_status=self.timeoutStatus, branch_status=self.branchStatus, parent=self, bv1blast=False))

#     def applyBitBlastRule(self, params):
#         self.children.append(TacticNode(name="simplify", params=None, parent=self))
#         self.children.append(TacticNode(name="bit-blast", params=params, parent=self)) # now the parameter for this action is for the tactic bit-blaster
#         self.children.append(StrategyNonterm(logic="SAT", timeout=self.timeout, timeout_status=-1, branch_status=-1, parent=self, bv1blast=self.bv1blast)) # for sat formula do not introduce timeout

    # def clone(self):
    #     childrenCp = self.childrenClone()
    #     return StrategyNonterm(self.logic, childrenCp, self.expandType)

# probably Stage 1 and Stage 2 strategies can be merged
class StrategyAST():
    def __init__(self, stage, logic, timeout, s1_lst = None, solver_dict = None, preprocess_dict = None):
        self.logic = logic
        self.timeout = timeout
        self.root = Root()
        if stage == 1:
            self.root.addChildren([S1Strategy(logic)])
        else:
            self.root.addChildren([S2Strategy(timeout, s1_lst, solver_dict, preprocess_dict)])

    def __str__(self):
        return str(self.root)

    # def smt2str(self):
    #     assert self.isTerminal()
    #     return self.root.children[0].smt2str()

    @staticmethod
    def _findFstNonTermRec(nonterm_stack):
        if not len(nonterm_stack):
            return None
        node2Search = nonterm_stack.pop()
        if not node2Search.isTerminal():
            return node2Search
        else:
            for childNode in reversed(node2Search.children):
                nonterm_stack.append(childNode)
        return StrategyAST._findFstNonTermRec(nonterm_stack)

    # return the depth-first first nontermial node in the tree; if nonexist, return None
    def findFstNonTerm(self):
        nonterm_stack = [self.root]
        return StrategyAST._findFstNonTermRec(nonterm_stack)

    def isTerminal(self):
        return not bool(self.findFstNonTerm())

    def legalActions(self, rollout = False):
        if self.isTerminal(): return []
        return self.findFstNonTerm().legalActions(rollout)

    def applyRule(self, action, params):
        assert (not self.isTerminal())
        node = self.findFstNonTerm()
        node.applyRule(action, params)

    # do not consider predicate branching for now
    def get_linear_strategies(self):
        assert self.isTerminal()
        return self.root.getLnStrats(self.timeout)
         
# CFG derivation tree
# class DerivationAST():
#     def __init__(self, logic, timeout, root = None):
#         self.logic = logic
#         if root is None:
#             self.root = StrategyNonterm(logic, timeout, timeout_status = 0, branch_status = 0, parent = None)
#         else:
#             self.root = root

#     def __str__(self):
#         return str(self.root)
    
#     @staticmethod
#     def _findFstNonTermRec(search_stack):
#         if not len(search_stack):
#             return None
#         node2Search = search_stack.pop()
#         if node2Search.isLeaf():
#             return node2Search
#         else:
#             for childNode in reversed(node2Search.children):
#                 if not childNode.isTerminal():
#                     search_stack.append(childNode)
#         return DerivationAST._findFstNonTermRec(search_stack)

#     # return the depth-first first nontermial node in the tree; if nonexist, return None
#     def findFstNonTerm(self):
#         searchStack = [self.root]
#         return DerivationAST._findFstNonTermRec(searchStack)

#     def isTerminal(self):
#         return not bool(self.findFstNonTerm())

#     def legalActions(self, rollout = False):
#         if self.isTerminal(): return []
#         return self.findFstNonTerm().legalActions(rollout)

#     def applyRule(self, action, params):
#         assert (not self.isTerminal())
#         node = self.findFstNonTerm()
#         node.applyRule(action, params)

    # def clone(self):
    #     rootCopy = self.root.clone()
    #     return DerivationAST(self.logic, rootCopy)