


class Executor:

    def __init__(self, broker, account, register=False):
        self.broker = broker
        self.account = account
        if register:
            self.broker.re
    
    def solveRound(self):
        if self.broker.getExecutorStateByAddress(self.account) == "locked":
            executor = dict(self.broker.getExecutorByAddress(self.account))
            request = dict(self.broker.requests(executor["assignedRequestID"]))
            #TODO deberia chequear que la request no este closed? si ese es el caso explota todo
