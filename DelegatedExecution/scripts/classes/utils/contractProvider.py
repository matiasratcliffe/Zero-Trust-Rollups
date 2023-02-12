from brownie import ExecutionBroker, ClientImplementation, config, network
from scripts.classes.utils.accountsManager import AccountsManager
from scripts.classes.utils.logger import Logger


@Logger.LogClassMethods
class BrokerFactory:
    def getInstance():
        if "brokerContractAddress" in config["networks"][network.show_active()]:
            return ExecutionBroker.at(config["networks"][network.show_active()]["brokerContractAddress"])
        elif (len(ExecutionBroker) > 0):
            return ExecutionBroker[-1]
        else:
            return BrokerFactory.create()

    def create():
        ExecutionBroker.deploy(
            {"from": AccountsManager.getAccount()},
            publish_source=config["networks"][network.show_active()]["verify"]
        )
        return ExecutionBroker[-1]

@Logger.LogClassMethods
class ClientFactory:
    def getInstance():
        if "clientContractAddress" in config["networks"][network.show_active()]:
            return ExecutionBroker.at(config["networks"][network.show_active()]["clientContractAddress"])
        elif (len(ClientImplementation) > 0):
            return ClientImplementation[-1]
        else:
            return ClientFactory.create(AccountsManager.getAccount(), BrokerFactory.getInstance())

    def create(_owner, _broker):
        ClientImplementation.deploy(
            _broker.address,
            {"from": _owner},
            publish_source=config["networks"][network.show_active()]["verify"]
        )
        return ClientImplementation[-1]