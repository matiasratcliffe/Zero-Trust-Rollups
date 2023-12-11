from scripts.classes.utils.contractProvider import ClientFactory, BrokerFactory, DummyFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from brownie.convert.datatypes import HexString
from eth_abi import encode
import re


@Logger.LogClassMethods()
class Requestor:
    def __init__(self, clientContract):
        try:
            self.client = ClientFactory.at(address=clientContract.address)
        except:
            self.client = DummyFactory.at(address=clientContract.address)
        self.owner = Accounts.getFromKey(self.client.owner())

    def _getFunctionTypes(self, function):
        memberRegex = r"([A-Za-z][A-Za-z0-9]*)\s+[_A-Za-z][_A-Za-z0-9]*;"
        dataStruct = self.client.getInputStructure(function)
        return ["("+",".join(re.findall(memberRegex, dataStruct))+")"]

    def _encodeInput(self, functionToRun, data):
        return (functionToRun, HexString(encode(self._getFunctionTypes(functionToRun), [tuple(data)]), "bytes"))

    def createRequest(self, functionToRun, dataArray, payment=1e+10, postProcessingGas=2e13, requestedInsurance=1e+15, claimDelay=0, funds=0, gas_price=None, getTransaction=False):
        transactionData = { "from": self.owner, "value": funds }
        if (gas_price != None):
            transactionData["gas_price"] = gas_price
        request = self.client.submitRequest(
            payment,
            self._encodeInput(functionToRun, dataArray),
            postProcessingGas,
            requestedInsurance,
            claimDelay,
            transactionData
        )
        request.wait(1)
        if (getTransaction):
            return request
        else:
            return request.return_value

    def cancelRequest(self, requestID):
        transaction = self.client.cancelRequest(requestID, {"from": self.owner})
        transaction.wait(1)
        return transaction

    def sendFunds(self, amount):
        return self.client.sendFunds({"from": self.owner, "value": amount})

    def withdrawFunds(self, amount):
        return self.client.withdrawFunds(amount, {"from": self.owner})

    def getFunds(self):
        return self.client.balance()

    def publicizeRequest(self, requestID):
        broker = BrokerFactory.at(address=self.client.brokerContract())
        return broker.publicizeRequest(requestID, {"from": self.owner})

    def togglePostProcessing(self):
        return self.client.togglePostProcessing({"from": self.owner})