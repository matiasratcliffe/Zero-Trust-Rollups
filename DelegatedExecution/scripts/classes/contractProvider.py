from brownie import ExecutionBroker, ClientImplementation
from scripts.classes.accountsManager import AccountsManager
from scripts.logger import Logger


@Logger.LogClassMethods
class BrokerFactory:
    ## TODO en el futuro sacar el deployment de las factories, y que las factories solo populen con data de config
    def getInstance():
        if (len(ExecutionBroker) > 0):
            return ExecutionBroker[-1]
        else:
            return BrokerFactory.create()

    def create():
        ExecutionBroker.deploy(
            {"from": AccountsManager.getAccount()}
        )
        return ExecutionBroker[-1]

@Logger.LogClassMethods
class ClientFactory:
    def getInstance():
        if (len(ClientImplementation) > 0):
            return ClientImplementation[-1]
        else:
            return ClientFactory.create(AccountsManager.getAccount(), BrokerFactory.getInstance())

    def create(_owner, _broker):
        ClientImplementation.deploy(
            _broker.address,
            {"from": _owner}
        )
        return ClientImplementation[-1]