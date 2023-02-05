from brownie import ClientImplementation
from scripts.classes.broker import BrokerFactory
from scripts.classes.auxiliar.accountsManager import AccountsManager
from scripts.classes.auxiliar.request import Request
from eth_abi import encode_abi
from scripts.logger import Logger
import re

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
        Logger.log("Instantiated client")
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
            Logger.log(f"Created request: {request.return_value}")
            return Request(request.return_value, self.instance, requestInput, payment, postProcessingGas, requestedInsurance, claimDelay)

        def cancelRequest(self, requestID):
            self.instance.cancelRequest(requestID)

        def sendFunds(self, amount):
            self.instance.sendFunds({"from": self.owner, "value": amount})

        def withdrawFunds(self, amount):
            self.instance.withdrawFunds(amount)

        def getFunds(self):
            return self.instance.balance()