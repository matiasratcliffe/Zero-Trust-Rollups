from random import randint
from scripts.classes.utils.logger import Logger


@Logger.LogClassMethods()
class Requestor:
    def __init__(self, broker, account) -> None:
        self.broker = broker
        self.account = account
    
    def createRequest(self, inputStateReference="", codeReference="", amountOfExecutors=3, executionPower=1000, gas_price=0):
        value = executionPower * amountOfExecutors
        randomSeed = randint(0, (2**256)-1)
        transaction = self.broker.submitRequest(inputStateReference, codeReference, amountOfExecutors, executionPower, randomSeed, 2, {"from": self.account, "value": value, "gas_price": gas_price})
        transaction.wait(1)
        return transaction

    def rotateExecutors(self, requestID, customGasPrice=None):
        chainData = {"from": self.account}
        if customGasPrice != None:
            chainData["gas_price"] = f"{customGasPrice} wei"
        randomSeed = randomSeed = randint(0, (2**256)-1)
        transaction = self.broker.rotateExecutors(requestID, randomSeed, chainData)
        transaction.wait(1)
        return transaction # TODO transaction wait for all projects