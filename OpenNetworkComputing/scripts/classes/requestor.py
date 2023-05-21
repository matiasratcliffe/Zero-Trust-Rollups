



class Requestor:

    def __init__(self, broker, account) -> None:
        self.broker = broker
        self.account = account
    
    def createRequest(self, inputStateReference="", codeReference="", amountOfExecutors=3, executionPower=1000):
        value = executionPower * amountOfExecutors
        transaction = self.broker.submitRequest(inputStateReference, codeReference, amountOfExecutors, executionPower, {"from": self.account, "value": value})
        transaction.wait(1)
        return transaction.return_value

    def rotateExecutors(self, requestID, customGasPrice=None):
        chainData = {"from": self.account}
        if customGasPrice != None:
            chainData["gas_price"] = f"{customGasPrice} wei"
        transaction = self.broker.rotateExecutors(requestID, chainData)
        transaction.wait(1)
        return transaction # TODO transaction wait for all projects