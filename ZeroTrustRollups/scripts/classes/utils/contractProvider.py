from brownie import ExecutionBroker, APIProvider, config, network
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger


@Logger.LogClassMethods()
class BrokerFactory:
    ACCEPTANCE_STAKE = 1e14

    def getInstance():
        if "brokerContractAddress" in config["networks"][network.show_active()]:
            return BrokerFactory.at(address=config["networks"][network.show_active()]["brokerContractAddress"])
        elif (BrokerFactory.count() > 0):
            return BrokerFactory.at(index=-1)
        else:
            return BrokerFactory.create(Accounts.getAccount())

    def create(account=None):
        if account == None:
            account = Accounts.getAccount()
        ExecutionBroker.deploy(
            BrokerFactory.ACCEPTANCE_STAKE,
            {"from": account},
            publish_source=config["networks"][network.show_active()]["verify"]
        )
        return BrokerFactory.at(index=-1)
    
    def at(index=None, address=None):
        if address and not index:
            return ExecutionBroker.at(address)
        if index and not address:
            return ExecutionBroker[index]
        raise "This method requires 1 keyValue parameter (address XOR index)"

    def count():
        return len(ExecutionBroker)

@Logger.LogClassMethods()
class APIProviderFactory:

    def getInstance():
        if "APIProviderContractAddress" in config["networks"][network.show_active()]:
            return APIProviderFactory.at(address=config["networks"][network.show_active()]["brokerContractAddress"])
        elif (APIProviderFactory.count() > 0):
            return APIProviderFactory.at(index=-1)
        else:
            return APIProviderFactory.create(Accounts.getAccount())

    def create(account=None):
        if account == None:
            account = Accounts.getAccount()
        APIProviderFactory.deploy(
            {"from": account},
            publish_source=config["networks"][network.show_active()]["verify"]
        )
        return BrokerFactory.at(index=-1)
    
    def at(index=None, address=None):
        if address and not index:
            return APIProviderFactory.at(address)
        if index and not address:
            return APIProviderFactory[index]
        raise "This method requires 1 keyValue parameter (address XOR index)"

    def count():
        return len(APIProvider)