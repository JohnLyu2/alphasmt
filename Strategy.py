


class Z3Tactic():
    """The class that represents a single tactic/action
    
    * Within The Same Tactic Name or a Tactic-Parameter-Timeout-Value combination?
    * One tactic can have multiple parameters

    """
    def __init__(self, action_id):
        self.tacticStr = name


# 

class Z3Strategy():
    """The class that represent a strategy
    
    * Tactical for tactics
    * Extension for more flexible strategy structure other than sequence?

    """
    def __init__(self, actionLst):
        self.actionLst = actionLst

    def getValidAction():
        pass

    def apply