import math

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

    # def legalActions(self):
    #     return list(self.action_dict.keys())

    def applyRule(self, action, params):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        func = self.action_dict[action]
        func(params)
        self.expandType = action

    # because of the added self.parent, old clone codes cannot be used
    # def childrenClone(self):
    #     chldCpLst = []
    #     for child in self.children:
    #         chldCpLst.append(child.clone())
    #     return chldCpLst

class TacticTerminal(DerivationNode):
    def __init__(self, name, params, parent): # tactic terminals do not have children 
        super().__init__(None, None, parent)
        self.name = name
        self.params = params
        # self._setParamMABs()

    def __str__(self):
        if not self.params:
          return self.name 
        tacticWithParamsStr = " (using-params " + self.name
        for param in self.params:
            paramStr = " :" + param + " " + str(self.params[param])
            tacticWithParamsStr += paramStr
        tacticWithParamsStr += ")"
        return tacticWithParamsStr

    def hasParams(self):
        return not self.params

    # def _setParamMABs(self):
    #     if not self.hasParams(): return
    #     self.MABs = {}
    #     self.selected = {}
    #     self.totalVisit = 0
    #     for param in self.params.keys():
    #         MABdict = {}
    #         for paramValue in self.params[param]:
    #             MABdict[paramValue] = [0, INIT_Q] # (visit count, q estimation) 
    #         self.MABs[param] = MABdict
    #         self.selected[param] = None

    # def _uct(self, action_pair):
    #     visitCount, qScore = action_pair
    #     exploreScore = C_UCT * \
    #         math.sqrt(math.log(self.totalVisit + 0.001) /
    #                   (visitCount + 0.001))
    #     return qScore + exploreScore
        

    # def _selectMAB(self, param):
    #     MABdict = self.MABs[param]
    #     _, selectValue = max((self._uct(pair), valueCanadidate)
    #                               for valueCanadidate, pair in MABdict.items())
    #     return selectValue

    # def selectMABs(self):
    #     for param in self.params.keys():
    #         selectV = self._selectMAB(param)
    #         self.selected[param] = selectV

    # def backup(self, returnV):
    #     self.totalVisit += 1
    #     for param in self.params.keys():
    #         MABdict = self.MABs[param]
    #         selectedV = self.selected[param]
    #         MABdict[selectedV][0] += 1
    #         MABdict[selectedV][1] = MABdict[selectedV][1] + STEP_ALPHA * (returnV - MABdict[selectedV][1]) # exponential recency-weighted average
    #         self.selected[param] = None

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
            # 25 - 31 are BV only
            25: "purify-arith",
            26: "max-bv-sharing",
            27: "aig",
            28: "reduce-bv-size",
            29: "ackermannize_bv",
            30: "bit-blast", 
            31: "bv1-blast",
            # 32 - 34 are BV only
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
        if self.logic == "BV":
            upbound = 30 if rollout else 31
            return actions + [i for i in range(25,upbound)]
        elif self.logic == "QF_NIA":
            return actions + [i for i in range(32,35)]
        elif self.logic == "QF_NRA":
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

    # def clone(self):
    #     childrenCp = self.childrenClone()
    #     return PreprocessNonterm(self.logic, childrenCp, self.expandType)


class SolvingNonterm(DerivationNode):
    def __init__(self, logic, parent, children = None, expand_type = None):
        super().__init__(children, expand_type, parent)
        self.logic = logic
        self.action_dict = {
            10: "smt",
            11: "qfnra-nlsat" # not for BV
        }

    def __str__(self):
        if self.isLeaf():
            return f"<SolvingTactic>({self.logic})"
        return str(self.children[0])

    def isTerminal(self):
        return False

    def legalActions(self, rollout = False):
        if self.logic == "BV":
            return [10]
        return list(self.action_dict.keys())

    def applyRule(self, action, params):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        tactic_name = self.action_dict[action]
        # params = TACTIC_PARAMS[tactic_name] if tactic_name in TACTIC_PARAMS else None
        selected = TacticTerminal(tactic_name, params, self)
        self.children.append(selected)
        self.expandType = action

    # def clone(self):
    #     childrenCp = self.childrenClone()
    #     return SolvingNonterm(self.logic, childrenCp, self.expandType)