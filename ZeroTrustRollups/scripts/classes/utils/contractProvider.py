from brownie import ExecutionBroker, APIProvider, APIConsumer, config, network
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger


@Logger.LogClassMethods()
class BrokerFactory:
    ACCEPTANCE_STAKE = 1e15  # 2 dollar aprox
    ACCEPTANCE_GRACE_PERIOD = 5

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
            BrokerFactory.ACCEPTANCE_GRACE_PERIOD,
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
            return APIProviderFactory.at(address=config["networks"][network.show_active()]["APIProviderContractAddress"])
        elif (APIProviderFactory.count() > 0):
            return APIProviderFactory.at(index=-1)
        else:
            return APIProviderFactory.create(Accounts.getAccount())

    def create(account=None):
        if account == None:
            account = Accounts.getAccount()
        APIProvider.deploy(
            {"from": account},
            publish_source=config["networks"][network.show_active()]["verify"]
        )
        return APIProviderFactory.at(index=-1)
    
    def at(index=None, address=None):
        if address and not index:
            return APIProvider.at(address)
        if index and not address:
            return APIProvider[index]
        raise "This method requires 1 keyValue parameter (address XOR index)"

    def count():
        return len(APIProvider)

@Logger.LogClassMethods()
class APIConsumerFactory:
    def getInstance():
        if "APIConsumerContractAddress" in config["networks"][network.show_active()]:
            return APIConsumerFactory.at(address=config["networks"][network.show_active()]["APIConsumerContractAddress"])
        elif (APIConsumerFactory.count() > 0):
            return APIConsumerFactory.at(index=-1)
        else:
            return APIConsumerFactory.create(BrokerFactory.getInstance(), APIProviderFactory.getInstance(), Accounts.getAccount())

    def create(broker, apiProvider, account=None):
        if account == None:
            account = Accounts.getAccount()
        APIConsumer.deploy(
            broker.address,
            apiProvider.address,
            {"from": account},
            publish_source=config["networks"][network.show_active()]["verify"]
        )
        return APIConsumerFactory.at(index=-1)
    
    def at(index=None, address=None):
        if address and not index:
            return APIConsumer.at(address)
        if index and not address:
            return APIConsumer[index]
        raise "This method requires 1 keyValue parameter (address XOR index)"

    def count():
        return len(APIConsumer)