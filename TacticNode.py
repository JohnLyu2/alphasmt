import math

INIT_Q = 1
C_UCT = 1

# to-do: move to somewhere else later/change it into inputs
TACTIC_PARAMS = {
    "simplify": {
        "elim_and": ["True","False"],
		    "som": ["True","False"],
		    "blast_distinct": ["True","False"],
		    "flat": ["True","False"],
		    "hi_div0": ["True","False"],
		    "local_ctx": ["True","False"],
		    "hoist_mul": ["True","False"]
    },
    "nla2bv": {
        "nla2bv_max_bv_size": [i * 10 for i in range(11)]
    }
}

class DerivationNode():
    def __init__(self, children, expand_type):
        if children is None:
            self.children = []
        else:
            self.children = children
        self.expandType = expand_type
            
    # isTerminal and isLeaf is different as a tree may not be complete
    def isLeaf(self):
        if len(self.children):
            return False
        return True

    def legalActions(self):
        return list(self.action_dict.keys())

    def applyRule(self, action):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        func = self.action_dict[action]
        func()
        self.expandType = action

    def childrenClone(self):
        chldCpLst = []
        for child in self.children:
            chldCpLst.append(child.clone())
        return chldCpLst

class TacticTerminal(DerivationNode):
    def __init__(self, name, params): # tactic terminals do not have children 
        super().__init__(None, None)
        self.name = name
        self.params = params
        self._setParamMABs()

    def __str__(self):
        return self.name # to-do: parameter

    def hasParams(self):
        if self.params is None:
            return False
        return True

    def _setParamMABs(self):
        if not self.hasParams(): return
        self.MABs = {}
        self.selected = {}
        self.totalVisit = 0
        for param in self.params.keys():
            MABdict = {}
            for paramValue in self.params[param]:
                MABdict[paramValue] = [0, INIT_Q] # (visit count, q estimation) 
            self.MABs[param] = MABdict
            self.selected[param] = None

    def _uct(self, action_pair):
        visitCount, qScore = action_pair
        exploreScore = C_UCT * \
            math.sqrt(math.log(self.totalVisit + 0.001) /
                      (visitCount + 0.001))
        return qScore + exploreScore
        

    def _selectMAB(self, param):
        MABdict = self.MABs[param]
        _, selectValue = max((self._uct(pair), valueCanadidate)
                                  for valueCanadidate, pair in MABdict.children.items())
        return selectValue

    def selectMABs(self):
        for param in self.params.keys():
            selectV = self._selectMAB(param)
            self.selected[param] = selectV

    def backup(self, returnV):
        self.totalVisit += 1
        for param in self.params.keys():
            MABdict = self.MABs[param]
            selectedV = self.selected[param]
            MABdict[selectedV]

    def isTerminal(self):
        return True

    def clone(self):
        return TacticTerminal(self.name, self.params) # name and params are not modified; no deep copy here

class PreprocessNonterm(DerivationNode):
    def __init__(self, logic, children = None, expand_type = None):
        super().__init__(children, expand_type)
        self.logic = logic
        self.action_dict = {
            20: "simplify", 
            21: "propagate-values",
            22: "ctx-simplify",
            23: "elim-uncnstr",
            24: "solve-eqs",
            25: "max-bv-sharing", # BV only
            26: "bit-blast" # BV only
        }

    def __str__(self):
        if self.isLeaf():
            return f"<PreprocessTactic>({self.logic})"
        return str(self.children[0])

    def isTerminal(self):
        return False

    def legalActions(self): # hardcoded now
        if self.logic == "BV":
            return list(self.action_dict.keys())
        elif self.logic == "QF_NIA":
            return [i for i in range(20,25)]
        else: 
            raise Exception("unexpected smt logic")

    def applyRule(self, action):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        tactic_name = self.action_dict[action]
        params = TACTIC_PARAMS[tactic_name] if tactic_name in TACTIC_PARAMS else None
        selected = TacticTerminal(tactic_name, params)
        self.children.append(selected)
        self.expandType = action

    def clone(self):
        childrenCp = self.childrenClone()
        return PreprocessNonterm(self.logic, childrenCp, self.expandType)


class SolvingNonterm(DerivationNode):
    def __init__(self, logic, children = None, expand_type = None):
        super().__init__(children, expand_type)
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

    def legalActions(self):
        if self.logic == "BV":
            return [10]
        return list(self.action_dict.keys())

    def applyRule(self, action):
        assert (self.isLeaf())
        assert (action in self.legalActions())
        tactic_name = self.action_dict[action]
        params = TACTIC_PARAMS[tactic_name] if tactic_name in TACTIC_PARAMS else None
        selected = TacticTerminal(tactic_name, params)
        self.children.append(selected)
        self.expandType = action

    def clone(self):
        childrenCp = self.childrenClone()
        return SolvingNonterm(self.logic, childrenCp, self.expandType)