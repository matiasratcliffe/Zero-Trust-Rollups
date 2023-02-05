class iClientFactory:
    def getInstance():
        raise "This is an interface instance"

    def create(_owner, _broker):
        raise "This is an interface instance"

    def fromAddress(address):
        raise "This is an interface instance"


class iClient:
        def encodeInput(self, functionToRun, data):
            raise "This is an interface instance"

        def createRequest(self, requestInput, payment=1e+16, requestedInsurance=1e+18, postProcessingGas=2e13, claimDelay=0, funds=0):
            raise "This is an interface instance"

        def cancelRequest(self, requestID):
            raise "This is an interface instance"

        def sendFunds(self, amount):
            raise "This is an interface instance"

        def withdrawFunds(self, amount):
            raise "This is an interface instance"

        def getFunds(self):
            raise "This is an interface instance"