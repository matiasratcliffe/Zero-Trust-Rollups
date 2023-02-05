class iBrokerFactory:
    def getInstance():
        raise "This is an interface instance"

    def create():
        raise "This is an interface instance"

    def fromAddress(address):
        raise "This is an interface instance"

class iBroker:
        def getRequests(self):
            raise "This is an interface instance"

        def getRequest(self, requestID):
            raise "This is an interface instance"

        def acceptRequest(self, requestID, acceptingAccount):
            raise "This is an interface instance"

        def cancelAcceptance(self, requestID):
            raise "This is an interface instance"

        def submitResult(self, requestID, result):
            raise "This is an interface instance"

        def challengeSubmission(self, requestID, account):
            raise "This is an interface instance"

        def isRequestOpen(self, requestID):
            raise "This is an interface instance"

        def claimPayment(self, requestID):
            raise "This is an interface instance"

        def recoverPayment(self, amount, account, destination):
            raise "This is an interface instance"