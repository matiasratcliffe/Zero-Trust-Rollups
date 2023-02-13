from brownie import network, config, accounts
from random import randint


class Accounts:
    def getAccount():
        if Accounts.count() == 0:
            Accounts._loadAccounts()
        return Accounts.getFromIndex(randint(0, len(accounts)-1))
    
    def count():
        return len(accounts)

    def _loadAccounts():
        if network.show_active() in config:
            for privateKey in config[network.show_active()]["wallets"]:
                accounts.add(privateKey)
        else:
            raise BaseException(f"No accounts provided for network: {network.show_active()}")

    def getFromIndex(index):
        return accounts[index]

    def getFromKey(key):
        return accounts.at(key)