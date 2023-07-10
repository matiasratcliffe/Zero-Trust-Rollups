from scripts.classes.utils.contractProvider import APIConsumerFactory, BrokerFactory
from scripts.classes.utils.accountsManager import Accounts
from brownie.convert.datatypes import HexString
from eth_abi import encode
import re


class APIConsumer:
    def __init__(self, APIConsumerContract):
        self.client = APIConsumerFactory.at(address=APIConsumerContract.address)
        self.owner = Accounts.getFromKey(self.client.owner())

    def _getFunctionTypes(self):
        memberRegex = r"([A-Za-z][A-Za-z0-9]*)\s+[_A-Za-z][_A-Za-z0-9]*;"
        dataStruct = self.client.getInputDataStructure()
        return ["("+",".join(re.findall(memberRegex, dataStruct))+")"]

    def _encodeInput(self, data):
        return HexString(encode(self._getFunctionTypes(), [tuple(data)]), "bytes")
    
    def createRequest(self, data, payment=1e+10, funds=0, gasPrice=None):
        transactionData = { "from": self.owner, "value": funds }
        if (gasPrice != None):
            transactionData["gas_price"] = gasPrice
        request = self.client.submitRequest(
            payment,
            self._encodeInput(data),
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