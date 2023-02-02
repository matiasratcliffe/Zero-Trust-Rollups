from ..auxiliar.accountsManager import AccountsManager
from ..auxiliar.request import Request
from brownie import ExecutionBroker


class Broker:
    def getInstance():
        if (len(ExecutionBroker) > 0):
            return ExecutionBroker.fromAddress(ExecutionBroker[-1].address)
        else:
            return ExecutionBroker.create(AccountsManager.getFromIndex(0), Broker.getInstance())

    def create(_creatorAccount):
        ExecutionBroker.deploy(
            {"from": _creatorAccount}
        )
        return Broker.fromAddress(ExecutionBroker[-1])

    def fromAddress(address):
        instance = ExecutionBroker.at(address)
        broker = Broker()
        broker.instance = instance
        return broker

    def __eq__(self, other):
        return self.instance.address == other.instance.address

    def acceptRequest(self, acceptingAccount):
        pass