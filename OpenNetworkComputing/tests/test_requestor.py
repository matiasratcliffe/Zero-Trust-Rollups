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

    def test_creation(self):
        account = Accounts.getAccount()
        broker = BrokerFactory.getInstance()
        requestor = Requestor(broker, account)
        assert requestor.account.address == account.address
        assert BrokerFactory.at(address=requestor.broker) == broker

    def test_submit_request(self):
        raise "implement this"

    def test_submit_request_even_amount_of_executors(self):
        raise "implement this"

    def test_submit_request_exceed_available_executors(self):
        raise "implement this"

    def test_submit_request_exceed_allowed_executors(self):
        raise "implement this"

    def test_submit_request_exceed_allowed_power(self):
        raise "implement this"

    def test_submit_request_mismatch_value(self):
        raise "implement this"

    def test_rotate_all_executors(self):
        raise "implement this"

    def test_rotate_one_executor(self):
        raise "implement this"

    def test_rotate_no_executors_completion(self):
        raise "implement this"

    def test_rotate_no_executors_premature(self):
        raise "implement this"

    def test_rotate_foreign_request(self):
        raise "implement this"
