from brownie import ExecutionBroker, PrimeFinder, config, network
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger


@Logger.LogClassMethods()
class BrokerFactory:
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
class ClientFactory:
    def getInstance():
        if "clientContractAddress" in config["networks"][network.show_active()]:
            return ClientFactory.at(address=config["networks"][network.show_active()]["clientContractAddress"])
        elif (ClientFactory.count() > 0):
            return ClientFactory.at(index=-1)
        else:
            return ClientFactory.create(broker=BrokerFactory.getInstance(), owner=Accounts.getAccount())

    def create(broker, owner=None):
        if owner == None:
            owner = Accounts.getAccount()
        PrimeFinder.deploy(
            broker.address,
            {"from": owner},
            publish_source=config["networks"][network.show_active()]["verify"]
        )
        return ClientFactory.at(index=-1)
    
    def at(index=None, address=None):
        if address and not index:
            return PrimeFinder.at(address)
        if index and not address:
            return PrimeFinder[index]
        raise "This method requires 1 keyValue parameter (address XOR index)"

    def count():
        return len(PrimeFinder)