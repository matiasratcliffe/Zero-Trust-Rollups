from scripts.classes.utils.contractProvider import BrokerFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from scripts.classes.requestor import Requestor


class TestRequestor:
    def setup(self):
        pass

    def teardown(self):
        pass

    def setup_method(self, method):
        Logger.indentationLevel=0

    def teardown_method(self, method):
        pass
        #network.event.event_watcher.reset()

    def test_creation(self):
        account = Accounts.getAccount()
        broker = BrokerFactory.getInstance()
        requestor = Requestor(broker, account)
        assert requestor.account.address == account.address
        assert BrokerFactory.at(address=requestor.broker) == broker