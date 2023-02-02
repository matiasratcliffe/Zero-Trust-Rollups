from brownie import ClientImplementation, ExecutionBroker
from ..auxiliar.accountsManager import AccountsManager
from .broker import Broker


class Client:
    def getInstance():
        if (len(ClientImplementation) > 0):
            return Client.fromAddress(ClientImplementation[-1].address)
        else:
            return Client.create(AccountsManager.getFromIndex(0), Broker.getInstance())

    def create(_owner, _broker):
        ClientImplementation.deploy(
            _broker.instance.address,
            {"from": _owner}
        )
        return Client.fromAddress(ClientImplementation[-1])

    def fromAddress(address):
        instance = ClientImplementation.at(address)
        client = Client()
        client.instance = instance
        client.owner = AccountsManager.getFromKey(str(instance.owner()))
        client.broker = Broker.fromAddress(str(instance.brokerContract()))
        return client

    def __eq__(self, other):
        return self.instance.address == other.instance.address

    def submitRequest(self, inputData, payment=1e+16, requestedInsurance=1e+18, postProcessingGas=2e+4, claimDelay=0):
        pass

    def cancelRequest(self, requestID):
        pass

    def sendFunds(self, amount):
        pass

    def withdrawFunds(self, amount):
        pass

    def getFunds(self):
        pass
