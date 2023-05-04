from scripts.classes.utils.contractProvider import BrokerFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from scripts.classes.executor import Executor


class TestExecutor:
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
        executor = Executor(broker, account)
        assert executor.account.address == account.address
        assert BrokerFactory.at(address=executor.broker) == broker
    
    def test_create_and_register_new_executor_check_state(self):
        pass

    def test_create_existing_executor_check_state(self):
        pass

    def test_create_and_register_existing_executor(self):
        pass

    def test_register_executor(self):
        broker = BrokerFactory.getInstance()
        executor = Executor(broker, Accounts.getAccount())
        pass

    def test_resgiter_executor_without_enough_stake(self):
        pass

    def test_register_already_present_active_executor(self):
        pass

    def test_pause_executor(self):
        pass

    def test_pause_executor_withdraw(self):
        pass

    def test_register_already_present_inactive_executor(self):
        pass

    def test_activate_executor(self):
        pass

    def test_activate_non_paused_executor(self):
        pass

    def test_activate_executor_without_enough_stake(self):
        pass

    def test_register_already_present_busy_executor(self):
        pass

