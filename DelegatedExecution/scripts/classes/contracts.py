from brownie import ExecutionBroker, ClientImplementation
from scripts.classes.auxiliar.accountsManager import AccountsManager
from brownie.exceptions import VirtualMachineError
from eth_abi import encode_abi, decode_abi
from scripts.logger import Logger
import re


class Acceptance:
    def __init__(self, _acceptor):
        self.acceptor = _acceptor
        #self.timestamp = ?

    def __str__(self):
        return f"(<{self.acceptor.address}>)"

class Submission:
    def __init__(self, _issuer, _timestamp, _result, _solidified):
        self.issuer = _issuer
        self.timestamp = _timestamp
        self.result = _result
        self.solidified = _solidified
    
    def __str__(self):
        return f"(<{self.issuer.address}>, 0x{self.result.hex(), self.solidified})"

class Request:
    def __init__(self, requestID, chainRequest):
        self.id = requestID
        self.input = (int(chainRequest[0][0]), bytes(chainRequest[0][1]))
        self.payment = int(chainRequest[1])
        self.postProcessingGas = int(chainRequest[2])
        self.challengeInsurance = int(chainRequest[3])
        self.claimDelay = int(chainRequest[4])
        self.client = ClientFactory.fromAddress(str(chainRequest[5]))
        self.acceptance = None
        self.submission = None
        if (int(chainRequest[6][0], 16) != 0):
            self.acceptance = Acceptance(
                AccountsManager.getFromKey(str(chainRequest[6][0]))
            )
        if (int(chainRequest[7][0], 16) != 0):
            self.submission = Submission(
                AccountsManager.getFromKey(str(chainRequest[7][0])),
                int(chainRequest[7][1]),
                bytes(chainRequest[7][2]),
                chainRequest[7][3]
            )
        self.cancelled = chainRequest[8]
    
    def __str__(self):
        return f"{{id: {self.id}, input: ({self.input[0]}, 0x{self.input[1].hex()}), payment: {self.payment/1e+18} Eth, postProcessingGas: {self.postProcessingGas/1e+9} Gwei, challengeInsurance: {self.challengeInsurance/1e+18} Eth, claimDelay: {self.claimDelay/3600} Hours, client: {self.client}, cancelled: {self.cancelled}, acceptance: {self.acceptance}, submission: {self.submission}}}"
    
    def __repr__(self):
        return str(self)

@Logger.LogClassMethods
class BrokerFactory:
    ## TODO en el futuro sacar el deployment de las factories, y que las factories solo populen con data de config
    ## TODO OOOO quizas en el futuro pasar fromaddress a la clase contrato, y que el deployment sea de los factories
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

@Logger.LogClassMethods
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
            return Request(requestID, chainRequest)

        def acceptRequest(self, requestID, acceptingAccount):
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

@Logger.LogClassMethods
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

@Logger.LogClassMethods
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
            return self.broker.getRequest(request.return_value)

        def cancelRequest(self, requestID):
            self.instance.cancelRequest(requestID)

        def sendFunds(self, amount):
            self.instance.sendFunds({"from": self.owner, "value": amount})

        def withdrawFunds(self, amount):
            self.instance.withdrawFunds(amount)

        def getFunds(self):
            return self.instance.balance()