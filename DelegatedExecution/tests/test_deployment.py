from scripts.classes.utils.contractProvider import BrokerFactory, ClientFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from brownie.network.account import Account as brownieAccount
from brownie.network.contract import ProjectContract as brownieContract
from brownie import network


class TestDeployment:
    def setup_method(self, method):
        Logger.logIndentation=0

    def teardown_method(self, method):
        pass

    def test_accounts(self):
        account = Accounts.getAccount()
        assert account.__class__ == brownieAccount

    def test_broker(self):
        broker = BrokerFactory.getInstance()
        assert broker.__class__ == brownieContract

    def test_client(self):
        if network.show_active() == "development":
            account = Accounts.getAccount()
            broker = BrokerFactory.getInstance()
            client = ClientFactory.create(owner=account, broker=broker)
        else:
            client = ClientFactory.getInstance()
            account = Accounts.getFromKey(client.owner())
            broker = BrokerFactory.at(address=client.brokerContract())
            assert account.address == client.owner()
            assert broker.address == client.brokerContract()