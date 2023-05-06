


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
        return self.broker.pauseExecutor(withdraw, {"from": self.account})
    
    def activateExecutor(self, funds=0):
        pass

    def solveRound(self):
        if self.broker.getExecutorStateByAddress(self.account) == "locked":
            executor = dict(self.broker.getExecutorByAddress(self.account))
            request = dict(self.broker.requests(executor["assignedRequestID"]))
            #TODO deberia chequear que la request no este closed? si ese es el caso explota todo
