from scripts.classes.utils.contractProvider import BrokerFactory, ClientFactory
from scripts.classes.utils.accountsManager import Accounts
from brownie import network


class TestDeployment:
    def test_accounts(self):
        account = Accounts.getAccount()

    def test_broker(self):
        broker = BrokerFactory.getInstance()

    def test_client(self):
        if network.show_active() == "development":
            account = Accounts.getAccount()
            broker = BrokerFactory.getInstance()
            client = ClientFactory.create(broker, account)
        else:
            client = ClientFactory.getInstance()
            account = Accounts.getFromKey(client.owner())
            broker = BrokerFactory.at(address=client.brokerContract())
            assert account.address == client.owner()
            assert broker.address == client.brokerContract()