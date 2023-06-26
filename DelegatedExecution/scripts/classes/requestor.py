from scripts.classes.utils.contractProvider import ClientFactory, BrokerFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from brownie.convert.datatypes import HexString
from eth_abi import encode
import re


@Logger.LogClassMethods()
class Requestor:
    def __init__(self, clientContract):
        self.client = ClientFactory.at(address=clientContract)
        self.owner = Accounts.getFromKey(self.client.owner())

    def _getFunctionTypes(self, function):
        memberRegex = r"([A-Za-z][A-Za-z0-9]*)\s+[_A-Za-z][_A-Za-z0-9]*;"
        dataStruct = self.client.getInputStructure(function)
        return re.findall(memberRegex, dataStruct)

    def _encodeInput(self, functionToRun, data):
        return (functionToRun, HexString(encode(self._getFunctionTypes(functionToRun), data), "bytes"))

    def createRequest(self, functionToRun, dataArray, payment=1e+16, postProcessingGas=2e13, requestedInsurance=1e+18, claimDelay=0, funds=0, gasPrice=None):
        transactionData = { "from": self.owner, "value": funds }
        if (gasPrice != None):
            transactionData["gas_price"] = gasPrice
        request = self.client.submitRequest(
            payment,
            self._encodeInput(functionToRun, dataArray),
            postProcessingGas,
            requestedInsurance,
            claimDelay,
            transactionData
        )
        request.wait(1)
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
        broker.publicizeRequest(requestID, {"from": self.owner})