



class Requestor:

    def __init__(self, broker, account) -> None:
        self.broker = broker
        self.account = account
    
    def createRequest(self, inputStateReference="", codeReference="", amountOfExecutors=3, executionPower=1000):
        value = (executionPower * amountOfExecutors) + self.broker.BASE_STAKE_AMOUNT()
        return self.broker.submitRequest(inputStateReference, codeReference, amountOfExecutors, executionPower, {"from": self.account, "value": value}).return_value