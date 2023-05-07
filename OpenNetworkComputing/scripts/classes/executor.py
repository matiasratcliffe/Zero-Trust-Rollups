


class Executor:

    def __init__(self, broker, account, register=False, stake=None):
        self.broker = broker
        self.account = account
        if register:
            if stake == None:
                stake = broker.BASE_STAKE_AMOUNT()
            self.broker.registerExecutor({"from": self.account, "value": stake})
    
    def getData(self):
        return dict(self.broker.getExecutorByAddress(self.account))

    def pauseExecutor(self, withdraw=False):
        if self.broker.getExecutorStateByAddress(self.account) == "active":
            return self.broker.pauseExecutor(withdraw, {"from": self.account})
        else:
            raise Exception("asdsadsadsadsad")
    
    def activateExecutor(self, funds=0):
        if self.broker.getExecutorStateByAddress(self.account) == "inactive":
            return self.broker.activateExecutor({"from": self.account, "value": funds})
        else:
            raise Exception("asdsadsadsad")

    def solveRound(self):
        if self.broker.getExecutorStateByAddress(self.account) == "locked":
            executor = dict(self.broker.getExecutorByAddress(self.account))
            request = dict(self.broker.requests(executor["assignedRequestID"]))
            #TODO deberia chequear que la request no este closed? si ese es el caso explota todo
