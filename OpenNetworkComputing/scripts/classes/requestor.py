



class Requestor:

    def __init__(self, broker, account) -> None:
        self.broker = broker
        self.account = account
    
    def createRequest(self, inputStateReference="", codeReference="", amountOfExecutors=3, executionPower=1000):
        pass