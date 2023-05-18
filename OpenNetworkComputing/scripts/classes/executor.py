from scripts.classes.executionState import ExecutionState


class Executor:

    def __init__(self, broker, account, register=False, stake=None):
        self.resultsBuffer = {}
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
            #TODO una vez ejecuto, deberia chequear hasta que se lockeen todas las sub?

    def _calculateFinalState(self, requestID): #TODO
        assert self.getData()["assignedRequestID"] == requestID, "You are not assigned to this request"
        if requestID in self.resultsBuffer:
            return self.resultsBuffer[requestID]
        request = dict(self.broker.requests(requestID))
        inputState = request["inputState"]
        codeReference = request["codeReference"]
        executionPower = request["executionPowerPaidFor"]
        self.resultsBuffer[requestID] = ExecutionState(123)
        return self.resultsBuffer[requestID]

    def _submitSignedHash(self, requestID, resultState=None):
        if resultState == None:
            resultState = self.resultsBuffer[requestID]
        return self.broker.submitSignedResultHash(requestID, resultState.getSignedHash(self.account.address), {"from": self.account})
    
    def _liberateResult(self, requestID):
        return self.broker.liberateResult(requestID, str(self.resultsBuffer[requestID]), {"from": self.account}) #TODO tx.wait(1)?