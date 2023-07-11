from scripts.classes.utils.contractProvider import APIProviderFactory, APIConsumerFactory, BrokerFactory
from scripts.classes.utils.accountsManager import Accounts
from eth_abi import decode, encode
import eth_account
import brownie
import random
import re


class APIProvider:
    def __init__(self, APIProviderContract):
        self.contract = APIProviderFactory.at(address=APIProviderContract.address)
        self.account = Accounts.getFromKey(self.contract.owner())

    def registerAPI(self, account: brownie.network.account.LocalAccount, identifier: str, override=False):
        if not override:
            assert int(str(self.contract.RegisteredAPIs(identifier)), 16) == 0
        self.contract.setAPIAddress(identifier, account.address, {"from": self.account})

class MockAPI:
    def __init__(self, account, identifier, resultDataStructure):
        self.account = account
        self.identifier = identifier
        self.resultDataStructure = resultDataStructure
    
    def getSignedResponse(self):
        message = str(random.randint(10000, 999999999))
        sig = eth_account.Account.sign_message(eth_account.messages.encode_defunct(text=message), self.account.private_key)
        memberRegex = r"([A-Za-z][A-Za-z0-9]*)\s+[_A-Za-z][_A-Za-z0-9]*;"
        return encode(["("+",".join(re.findall(memberRegex, self.resultDataStructure))+")"], [(bytes(message, 'utf-8'), bytes(sig.signature))])

class APIOracle:
    def __init__(self, broker, apiProvider, account):
        self.broker = BrokerFactory.at(address=broker.address)
        self.apiProvider = APIProviderFactory.at(address=apiProvider.address)
        self.account = account
    
    def _acceptRequest(self, requestID):
        transaction = self.broker.acceptRequest(requestID, {'from': self.account, 'value': self.broker.ACCEPTANCE_STAKE()})
        transaction.wait(1)
        return transaction
    
    def _resolveRequest(self, requestID):
        request = self.broker.requests(requestID).dict()
        apiConsumer = APIConsumerFactory.at(address=self.broker.requests(requestID).dict()["client"])
        memberRegex = r"([A-Za-z][A-Za-z0-9]*)\s+[_A-Za-z][_A-Za-z0-9]*;"
        identifier = decode(["("+",".join(re.findall(memberRegex, apiConsumer.getInputDataStructure()))+")"], request["input"])[0][0]
        address = self.apiProvider.RegisteredAPIs(identifier)
        api = MockAPI(Accounts.getFromKey(address), identifier, apiConsumer.getResultDataStructure())
        self.broker.submitResult(requestID, api.getSignedResponse(), {"from": self.account})