from brownie import network, accounts
from random import randint

class AccountsManager:
    def getAccount():
        return AccountsManager.getFromIndex(randint(0, len(accounts)-1))
    
    def getFromIndex(index):
        return accounts[index]

    def getFromKey(key):
        return accounts.at(key)