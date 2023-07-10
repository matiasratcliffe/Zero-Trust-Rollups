from scripts.classes.utils.contractProvider import APIProviderFactory
from scripts.classes.utils.accountsManager import Accounts
import eth_account
import brownie
import random


class APIProvider:

    def __init__(self):
        self.contract = APIProviderFactory.getInstance()
        self.account = Accounts.getFromKey(self.contract.owner())

    def registerAPI(self, account: brownie.network.account.LocalAccount, idenfitier: str, override=False):
        if not override:
            assert int(str(self.contract.RegisteredAPIs("identifier")), 16) == 0
        self.contract.setAPIAddress(idenfitier, account.address, {"from": self.account})
        return MockAPI(account)

class MockAPI:
    
    def __init__(self, apiProvider, account):
        self.account = account
    
    def getSignedResponse(self):
        message = str(random.randint(10000, 999999999))
        sig = eth_account.Account.sign_message(eth_account.messages.encode_defunct(text=message), self.account.private_key)
        return (bytes(message, 'utf-8'), sig.signature)