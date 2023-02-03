

## TODO y si executor solo tiene los loops? y el resto lo hace interactuando con broker?
class Executor:
    def __init__(self, account, broker):
        self.account = account
        self.broker = broker

    def computeResult(self, requestID):
        dataInput = self.broker.getRequest(requestID).input
        result = self.broker.getRequest(requestID).client.instance.clientLogic(dataInput)
        return result
    
    def acceptNextOpenRequest(self):
        # lo hago leyendo eventos? do I keep track? lo hago en paralelo?
        pass

    def solverLoop(self):
        pass

    def challengerLoop(self):
        pass
