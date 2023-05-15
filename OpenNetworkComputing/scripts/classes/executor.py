from scripts.classes.executionState import ExecutionState


class Executor:

    def __init__(self, broker, account, register=False, stake=None):
        self.resultBuffer = ""
        self.broker = broker
        self.account = account
        if register:
            if stake == None:
                stake = broker.BASE_STAKE_AMOUNT()
            self.broker.registerExecutor({"from": self.account, "value": stake})
    
    def getData(self):
        return dict(self.broker.getExecutorByAddress(self.account))
    
    def getState(self):
        return self.broker.getExecutorStateByAddress(self.account)

    def pauseExecutor(self, withdraw=False):
        return self.broker.pauseExecutor(withdraw, {"from": self.account})
    
    def activateExecutor(self, funds=0):
        return self.broker.activateExecutor({"from": self.account, "value": funds})

    def solveRound(self):
        #TODO save result in buffer for later escrow liberation
        if self.broker.getExecutorStateByAddress(self.account) == "locked":
            executor = dict(self.broker.getExecutorByAddress(self.account))
            request = dict(self.broker.requests(executor["assignedRequestID"]))
            #TODO deberia chequear que la request no este closed? si ese es el caso explota todo

    def _getFinalState(self, inputStateReference, codeReference, executionPower): #TODO
        return ExecutionState(123)

    def _submitSignedHash(self, requestID, resultState: ExecutionState):
        #TODO check resultstate is exetutionState
        return self.broker.submitSignedResultHash(requestID, resultState.getSignedHash(self.account.address), {"from": self.account})