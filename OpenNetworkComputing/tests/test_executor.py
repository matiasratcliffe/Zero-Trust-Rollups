from scripts.classes.utils.contractProvider import BrokerFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from scripts.classes.executor import Executor
import pytest

class TestExecutor:
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
        executor = Executor(broker, account)
        assert executor.account.address == account.address
        assert BrokerFactory.at(address=executor.broker) == broker
    
    def test_create_and_register_new_executor_check_state(self):
        broker = BrokerFactory.getInstance()
        executor = Executor(broker, Accounts.getAccount(), True)
        assert broker.getExecutorStateByAddress(executor.account) == "active"
        executorData = executor.getData()
        assert executorData["accurateSolvings"] == 0
        assert executorData["assignedRequestID"] == 0
        assert executorData["inaccurateSolvings"] == 0
        assert executorData["timesPunished"] == 0
        assert executorData["executorAddress"] == executor.account
        assert executorData["lockedWei"] == broker.BASE_STAKE_AMOUNT()

    def test_create_existing_executor_check_state(self):
        broker = BrokerFactory.getInstance()
        account = Accounts.getAccount()
        Executor(broker, account, True)
        assert broker.getExecutorStateByAddress(account) == "active"
        executor = Executor(broker, account, False)
        assert broker.getExecutorStateByAddress(account) == "active"

    def test_create_and_register_existing_executor(self):
        broker = BrokerFactory.getInstance()
        account = Accounts.getAccount()
        Executor(broker, account, True)
        assert broker.getExecutorStateByAddress(account) == "active"
        with pytest.raises(Exception, match="This address is already registered as an active executor"):
            Executor(broker, account, True)

    def test_resgiter_executor_without_enough_stake(self):
        with pytest.raises(Exception, match="To register an executor you must provide at least the minimum escrow stake amount"):
            Executor(BrokerFactory.getInstance(), Accounts.getAccount(), True, 0)

    def test_pause_executor(self):
        executor = Executor(BrokerFactory.getInstance(), Accounts.getAccount(), True)
        assert executor.broker.getExecutorStateByAddress(executor.account) == "active"
        executor.pauseExecutor()
        assert executor.broker.getExecutorStateByAddress(executor.account) == "inactive"
        assert executor.getData()['lockedWei'] == executor.broker.BASE_STAKE_AMOUNT()
    
    def test_pause_paused_executor(self):
        raise "implement this"

    def test_pause_executor_withdraw(self):
        executor = Executor(BrokerFactory.getInstance(), Accounts.getAccount(), True)
        assert executor.broker.getExecutorStateByAddress(executor.account) == "active"
        stake = executor.getData()["lockedWei"]
        originalBalance = executor.account.balance()
        transaction = executor.pauseExecutor(True)
        assert executor.broker.getExecutorStateByAddress(executor.account) == "inactive"
        assert executor.account.balance() == originalBalance - (transaction.gas_used * transaction.gas_price) + stake
        assert executor.getData()['lockedWei'] == 0

    def test_register_already_present_inactive_executor(self):
        broker = BrokerFactory.getInstance()
        account = Accounts.getAccount()
        executor = Executor(broker, account, True)
        executor.pauseExecutor()
        assert executor.broker.getExecutorStateByAddress(executor.account) == "inactive"
        with pytest.raises(Exception, match="The executor is already present, but inactive"):
            Executor(broker, account, True)

    def test_activate_executor(self):
        broker = BrokerFactory.getInstance()
        account = Accounts.getAccount()
        executor = Executor(broker, account, True)
        executor.pauseExecutor()
        assert executor.broker.getExecutorStateByAddress(executor.account) == "inactive"

    def test_activate_non_paused_executor(self):
        raise "implement this"

    def test_activate_executor_without_enough_stake(self):
        raise "implement this"

    def test_activate_executor_providing_stake(self):
        raise "implement this"

    def test_register_already_present_busy_executor(self):
        raise "implement this"

