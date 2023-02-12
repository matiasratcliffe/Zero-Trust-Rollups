from brownie import network, config, accounts
from random import randint


class AccountsManager:
    def getAccount():
        if len(accounts) == 0:
            AccountsManager._loadAccounts()
        return AccountsManager.getFromIndex(randint(0, len(accounts)-1))
    
    def _loadAccounts():
        if network.show_active() in config["wallets"]:
            for privateKey in config["wallets"][network.show_active()]:
                accounts.add(privateKey)
        else:
            raise f"No accounts provided for network: {network.show_active()}"

    def getFromIndex(index):
        return accounts[index]

    def getFromKey(key):
        return accounts.at(key)