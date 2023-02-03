from brownie import ExecutionBroker, ClientImplementation
from scripts.classes.auxiliar.accountsManager import AccountsManager
from scripts.classes.auxiliar.request import Request, Acceptance, Submission
from brownie.exceptions import VirtualMachineError
from eth_abi import encode_abi, decode_abi
import re


class BrokerFactory:
    ## TODO en el futuro sacar el deployment de las factories, y que las factories solo populen con data de config
    def getInstance():
        if (len(ExecutionBroker) > 0):
            return BrokerFactory.fromAddress(ExecutionBroker[-1].address)
        else:
            return BrokerFactory.create()

    def create():
        ExecutionBroker.deploy(
            {"from": AccountsManager.getAccount()}
        )
        return BrokerFactory.fromAddress(ExecutionBroker[-1])

    def fromAddress(address):
        instance = ExecutionBroker.at(address)
        broker = Broker()
        broker.instance = instance
        return broker

class Broker:
        def __eq__(self, other):
            return self.instance.address == other.instance.address

        def getRequests(self):
            requests = []
            try:
                while True:
                    requests.append(self.getRequest(len(requests)))
            except VirtualMachineError as error:
                return requests

        def getRequest(self, requestID):
            chainRequest = self.instance.requests(requestID)
            client = ClientFactory.fromAddress(str(chainRequest[5]))
            request = Request(
                requestID,
                client,
                (int(chainRequest[0][0]), bytes(chainRequest[0][1])),
                int(chainRequest[1]),
                int(chainRequest[2]),
                int(chainRequest[3]),
                int(chainRequest[4])
            )
            if (int(chainRequest[6][0], 16) != 0):
                request.acceptance = Acceptance(
                    AccountsManager.getFromKey(str(chainRequest[6][0]))
                )
            if (int(chainRequest[7][0], 16) != 0):
                request.submission = Submission(
                    AccountsManager.getFromKey(str(chainRequest[7][0])),
                    int(chainRequest[7][1]),
                    bytes(chainRequest[7][2]),
                    chainRequest[7][3]
                )
            request.cancelled = chainRequest[8]
            return request

        def acceptRequest(self, requestID, acceptingAccount):  # TODO sacar eso de que lo asuma None, y que todo lo popule el executor
            request = self.getRequest(requestID)
            self.instance.acceptRequest(requestID, {"from": acceptingAccount, "value": request.challengeInsurance})

        def cancelAcceptance(self, requestID):
            account = self.getRequest(requestID).acceptance.acceptor
            self.instance.cancelAcceptance(requestID, {"from": account})

        def submitResult(self, requestID, result):
            account = self.getRequest(requestID).acceptance.acceptor
            self.instance.submitResult(requestID, result, {"from": account})

        def challengeSubmission(self, requestID, account):
            self.instance.challengeSubmission(requestID, {"from": account})

        def isRequestOpen(self, requestID):
            return self.instance.isRequestOpen(requestID)

        def claimPayment(self, requestID):
            account = self.getRequest(requestID).submission.issuer
            self.instance.claimPayment(requestID, {"from": account})

        def recoverPayment(self, amount, account, destination):
            self.instance.publicTransferFunds(amount, destination, {"from": account})


class ClientFactory:
    def getInstance():
        if (len(ClientImplementation) > 0):
            return ClientFactory.fromAddress(ClientImplementation[-1].address)
        else:
            return ClientFactory.create(AccountsManager.getAccount(), BrokerFactory.getInstance())

    def create(_owner, _broker):
        ClientImplementation.deploy(
            _broker.instance.address,
            {"from": _owner}
        )
        return ClientFactory.fromAddress(ClientImplementation[-1])

    def fromAddress(address):
        instance = ClientImplementation.at(address)
        client = Client()
        client.instance = instance
        client.owner = AccountsManager.getFromKey(str(instance.owner()))
        client.broker = BrokerFactory.fromAddress(str(instance.brokerContract()))
        return client


class Client:
        def __str__(self):
            return f"<{self.instance.address}>"

        def __eq__(self, other):
            return self.instance.address == other.instance.address

        def encodeInput(self, functionToRun, data):
            memberRegex = "([A-Za-z][A-Za-z0-9]*)\s+[_A-Za-z][_A-Za-z0-9]*;"
            dataStruct = self.instance.getInputStructure(functionToRun)
            return (functionToRun, encode_abi(re.findall(memberRegex, dataStruct), data))

        def createRequest(self, requestInput, payment=1e+16, requestedInsurance=1e+18, postProcessingGas=2e13, claimDelay=0, funds=0):
            transactionData = {"from": self.owner}
            if (funds > 0):
                transactionData["value"] = funds * 1e+18
            request = self.instance.submitRequest(
                payment,
                requestInput,
                postProcessingGas,
                requestedInsurance,
                claimDelay,
                transactionData
            )
            request.wait(1)
            return Request(request.return_value, self, requestInput, payment, postProcessingGas, requestedInsurance, claimDelay)

        def cancelRequest(self, requestID):
            self.instance.cancelRequest(requestID)

        def sendFunds(self, amount):
            self.instance.sendFunds({"from": self.owner, "value": amount})

        def withdrawFunds(self, amount):
            self.instance.withdrawFunds(amount)

        def getFunds(self):
            return self.instance.balance()