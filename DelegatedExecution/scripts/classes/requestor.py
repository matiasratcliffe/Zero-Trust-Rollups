from scripts.classes.utils.contractProvider import ClientFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from eth_abi import encode
import re


@Logger.LogClassMethods
class Requestor:
    def __init__(self, clientContract):
        self.client = ClientFactory.at(address=clientContract)
        self.owner = Accounts.getFromKey(self.client.owner())

    def _getFunctionTypes(self, function):
        memberRegex = r"([A-Za-z][A-Za-z0-9]*)\s+[_A-Za-z][_A-Za-z0-9]*;"
        dataStruct = self.client.getInputStructure(function)
        return re.findall(memberRegex, dataStruct)

    def _encodeInput(self, functionToRun, data):
        return (functionToRun, encode(self._getFunctionTypes(functionToRun), data))

    def createRequest(self, functionToRun, dataArray, payment=1e+16, postProcessingGas=2e13, requestedInsurance=1e+18, claimDelay=0, funds=0):
        transactionData = { "from": self.owner, "value": funds * 1e+18 }
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
        self.client.cancelRequest(requestID, {"from": self.owner})

    def sendFunds(self, amount):
        self.client.sendFunds({"from": self.owner, "value": amount})

    def withdrawFunds(self, amount):
        self.client.withdrawFunds(amount, {"from": self.owner})

    def getFunds(self):
        return self.client.balance()