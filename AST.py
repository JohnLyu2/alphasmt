TACTIC_NONTERM = "<tactic>"


# The AST for Strategy, instead of CFG derivation 
class ASTNode:
    def __init__(self, nodeStr):
        self.name = nodeStr
        self.isTerminal = True
        if self.name.startswith("<"):
            self.isTerminal = False
        self.children = []

class StratAST:
    def __init__(self):
        self.root = ASTNode(TACTIC_NONTERM)