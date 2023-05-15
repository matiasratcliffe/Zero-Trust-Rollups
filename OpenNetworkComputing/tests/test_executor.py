from scripts.classes.utils.contractProvider import BrokerFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from scripts.classes.requestor import Requestor
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
        broker = BrokerFactory.create()
        executor = Executor(broker, account)
        assert executor.account.address == account.address
        assert BrokerFactory.at(address=executor.broker) == broker
    
    def test_create_and_register_new_executor_check_state(self):
        broker = BrokerFactory.create()
        executor = Executor(broker, Accounts.getAccount(), True)
        assert broker.getExecutorStateByAddress(executor.account) == "active"
        executorData = executor.getData()
        assert executorData["accurateSolvings"] == 0
        assert executorData["assignedRequestID"] == 0
        assert executorData["inaccurateSolvings"] == 0
        assert executorData["timesPunished"] == 0
        assert executorData["executorAddress"] == executor.account
        assert executorData["lockedWei"] == broker.BASE_STAKE_AMOUNT()

    def test_get_data_of_non_registered_executor(self):
        executor = Executor(BrokerFactory.create(), Accounts.getAccount())
        with pytest.raises(Exception, match="This address does not belong to a registered executor"):
            executor.getData()
        with pytest.raises(Exception, match="This address does not belong to a registered executor"):
            executor.broker.getExecutorStateByAddress(executor.account)

    def test_create_existing_executor_check_state(self):
        broker = BrokerFactory.create()
        account = Accounts.getAccount()
        Executor(broker, account, True)
        assert broker.getExecutorStateByAddress(account) == "active"
        executor = Executor(broker, account, False)
        assert broker.getExecutorStateByAddress(executor.account) == "active"

    def test_create_and_register_existing_executor(self):
        broker = BrokerFactory.create()
        account = Accounts.getAccount()
        Executor(broker, account, True)
        assert broker.getExecutorStateByAddress(account) == "active"
        with pytest.raises(Exception, match="This address is already registered as an active executor"):
            Executor(broker, account, True)

    def test_resgiter_executor_without_enough_stake(self):
        with pytest.raises(Exception, match="To register an executor you must provide at least the minimum escrow stake amount"):
            Executor(BrokerFactory.create(), Accounts.getAccount(), True, 0)

    def test_pause_executor(self):
        executor = Executor(BrokerFactory.create(), Accounts.getAccount(), True)
        assert executor.broker.getExecutorStateByAddress(executor.account) == "active"
        executor.pauseExecutor()
        assert executor.broker.getExecutorStateByAddress(executor.account) == "inactive"
        assert executor.getData()['lockedWei'] == executor.broker.BASE_STAKE_AMOUNT()
    
    def test_pause_paused_executor(self):
        executor = Executor(BrokerFactory.create(), Accounts.getAccount(), True)
        executor.pauseExecutor()
        assert executor.broker.getExecutorStateByAddress(executor.account) == "inactive"
        with pytest.raises(Exception, match="This address does not belong to an active executor"):
            executor.pauseExecutor()
    
    def test_pause_non_registered_executor(self):
        executor = Executor(BrokerFactory.create(), Accounts.getAccount())
        with pytest.raises(Exception, match="This address does not belong to an active executor"):
            executor.pauseExecutor()

    def test_pause_executor_withdraw(self):
        executor = Executor(BrokerFactory.create(), Accounts.getAccount(), True)
        assert executor.broker.getExecutorStateByAddress(executor.account) == "active"
        stake = executor.getData()["lockedWei"]
        originalBalance = executor.account.balance()
        transaction = executor.pauseExecutor(True)
        assert executor.broker.getExecutorStateByAddress(executor.account) == "inactive"
        assert executor.account.balance() == originalBalance - (transaction.gas_used * transaction.gas_price) + stake
        assert executor.getData()['lockedWei'] == 0

    def test_register_already_present_inactive_executor(self):
        broker = BrokerFactory.create()
        account = Accounts.getAccount()
        executor = Executor(broker, account, True)
        executor.pauseExecutor()
        assert executor.broker.getExecutorStateByAddress(executor.account) == "inactive"
        with pytest.raises(Exception, match="The executor is already present, but inactive"):
            Executor(broker, account, True)

    def test_activate_executor(self):
        broker = BrokerFactory.create()
        account = Accounts.getAccount()
        executor = Executor(broker, account, True)
        executor.pauseExecutor()
        assert executor.broker.getExecutorStateByAddress(executor.account) == "inactive"
        executor.activateExecutor()
        assert executor.broker.getExecutorStateByAddress(executor.account) == "active"

    def test_activate_non_paused_executor(self):
        executor = Executor(BrokerFactory.create(), Accounts.getAccount(), True)
        with pytest.raises(Exception, match="This address does not belong to a paused executor"):
            executor.activateExecutor()
    
    def test_activate_non_registered_executor(self):
        executor = Executor(BrokerFactory.create(), Accounts.getAccount())
        with pytest.raises(Exception, match="This address does not belong to a paused executor"):
            executor.activateExecutor()

    def test_activate_executor_without_enough_stake(self):
        executor = Executor(BrokerFactory.create(), Accounts.getAccount(), True)
        executor.pauseExecutor(True)
        with pytest.raises(Exception, match="You must provide some Wei to reach the minimum escrow stake amount"):
            executor.activateExecutor()

    def test_activate_executor_providing_stake(self):
        executor = Executor(BrokerFactory.create(), Accounts.getAccount(), True)
        executor.pauseExecutor(True)
        executor.activateExecutor(executor.broker.BASE_STAKE_AMOUNT())
        assert executor.broker.getExecutorStateByAddress(executor.account) == "active"

    def test_register_already_present_busy_executor(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        requestor = Requestor(broker, Accounts.getAccount())
        requestor.createRequest("input reference", "code reference", amountOfExecutors=1, executionPower=1000)
        assert executor1.getState() == "locked"
        with pytest.raises(Exception, match="The executor is already present, but busy"):
            Executor(broker, Accounts.getFromIndex(0), True)

    def test_submit_trivial_result(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        requestor = Requestor(broker, Accounts.getAccount())
        inputReference = "input reference"
        codeReference = "code reference"
        reqID = requestor.createRequest(inputReference, codeReference, amountOfExecutors=1, executionPower=1000)
        result1 = executor1._getFinalState(inputReference, codeReference, 1000)
        executor1._submitSignedHash(reqID, result1)
        assert dict(broker.taskAssignmentsMap(reqID, executor1.getData()["taskAssignmentIndex"]))["submitted"] == True
        assert dict(broker.taskAssignmentsMap(reqID, executor1.getData()["taskAssignmentIndex"]))["solidified"] == False
        assert int(dict(broker.taskAssignmentsMap(reqID, executor1.getData()["taskAssignmentIndex"]))["signedResultHash"].hex(), 16) != 0
        assert dict(broker.requests(reqID))["submissionsLocked"] == True