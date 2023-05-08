from scripts.classes.utils.contractProvider import BrokerFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from scripts.classes.requestor import Requestor
from scripts.classes.executor import Executor
import pytest
import time


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
        broker = BrokerFactory.create()
        account1 = Accounts.getFromIndex(0)
        account2 = Accounts.getFromIndex(1)
        account3 = Accounts.getFromIndex(2)
        Executor(broker, account1, True)
        Executor(broker, account2, True)
        Executor(broker, account3, True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input reference", "code reference", amountOfExecutors=3, executionPower=1000)
        request = dict(requestor.broker.requests(reqID))
        assert request["clientAddress"] == requestor.account
        assert request["closed"] == False
        assert request["codeReference"] == "code reference"
        assert request["id"] == reqID
        assert request["inputStateReference"] == "input reference"
        assert request["executionPowerPaidFor"] == 1000
        assignedExecutors = [dict(requestor.broker.taskAssignmentsMap(reqID, i))["executorAddress"] for i in range(3)]
        assert broker.getExecutorStateByAddress(account1) == "locked"
        assert broker.getExecutorStateByAddress(account2) == "locked"
        assert broker.getExecutorStateByAddress(account3) == "locked"
        assert account1 in assignedExecutors
        assert account2 in assignedExecutors
        assert account3 in assignedExecutors
        for i in range(3):
            taskAssignment = dict(requestor.broker.taskAssignmentsMap(reqID, i))
            assert int(taskAssignment["result"].hex(), 16) == 0
            assert taskAssignment["submitted"] == False

    def test_submit_request_even_amount_of_executors(self):
        executor = Requestor(BrokerFactory.create(), Accounts.getAccount())
        with pytest.raises(Exception, match="You must choose an odd amount of executors"):
            executor.createRequest(amountOfExecutors=2)

    def test_submit_request_exceed_available_executors(self):
        executor = Requestor(BrokerFactory.create(), Accounts.getAccount())
        with pytest.raises(Exception, match="You exceeded the number of available executors"):
            executor.createRequest(amountOfExecutors=1)

    def test_submit_request_exceed_allowed_executors(self):
        executor = Requestor(BrokerFactory.create(), Accounts.getAccount())
        with pytest.raises(Exception, match="You exceeded the maximum number of allowed executors per request"):
            executor.createRequest(amountOfExecutors=executor.broker.MAXIMUM_EXECUTORS_PER_REQUEST() + 2)

    def test_submit_request_exceed_allowed_power(self):
        executor = Requestor(BrokerFactory.create(), Accounts.getAccount())
        with pytest.raises(Exception, match="You exceeded the maximum allowed execution power per request"):
            executor.createRequest(executionPower=executor.broker.MAXIMUM_EXECUTION_POWER() + 1)

    def test_submit_request_mismatch_value(self):
        broker = BrokerFactory.getInstance()
        Executor(broker, Accounts.getAccount(), True)
        with pytest.raises(Exception, match="The value sent in the request must be the ESCROW_STAKE_AMOUNT plus the execution power you intend to pay for evrey executor"):
            broker.submitRequest("", "", 1, 1000, {"from": Accounts.getAccount()})

    def test_rotate_all_executors(self):
        broker = BrokerFactory.create()
        account1 = Accounts.getFromIndex(0)
        account2 = Accounts.getFromIndex(1)
        account3 = Accounts.getFromIndex(2)
        Executor(broker, account1, True)
        Executor(broker, account2, True)
        Executor(broker, account3, True)
        assert broker.getExecutorStateByAddress(account1) == "active"
        assert broker.getExecutorStateByAddress(account2) == "active"
        assert broker.getExecutorStateByAddress(account3) == "active"
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input reference", "code reference", amountOfExecutors=3, executionPower=1000)
        
        account4 = Accounts.getFromIndex(3)
        account5 = Accounts.getFromIndex(4)
        account6 = Accounts.getFromIndex(5)
        Executor(broker, account4, True)
        Executor(broker, account5, True)
        Executor(broker, account6, True)
        time.sleep(broker.EXECUTION_TIME_FRAME_SECONDS())

        requestor.rotateExecutors(reqID)
        assignedExecutors = [dict(requestor.broker.taskAssignmentsMap(reqID, i))["executorAddress"] for i in range(3)]        
        assert account1 not in assignedExecutors
        assert account2 not in assignedExecutors
        assert account3 not in assignedExecutors
        assert broker.getExecutorStateByAddress(account1) == "inactive"
        assert broker.getExecutorStateByAddress(account2) == "inactive"
        assert broker.getExecutorStateByAddress(account3) == "inactive"
        assert account4 in assignedExecutors
        assert account5 in assignedExecutors
        assert account6 in assignedExecutors
        assert broker.getExecutorStateByAddress(account4) == "locked"
        assert broker.getExecutorStateByAddress(account5) == "locked"
        assert broker.getExecutorStateByAddress(account6) == "locked"
        raise "asd"

    def test_rotate_one_executor(self):
        raise "implement this"

    def test_rotate_no_executors_completion(self):
        raise "implement this"

    def test_rotate_no_executors_premature(self):
        raise "implement this"

    def test_rotate_executors_all_exceeded_but_none_available(self):
        raise "implement this"

    def test_rotate_executors_all_exceeded_but_only_some_available(self):
        raise "implement this"

    def test_rotate_foreign_request(self):
        broker = BrokerFactory.create()
        Executor(broker, Accounts.getAccount(), True)
        requestor1 = Requestor(broker, Accounts.getFromIndex(0))
        requestor2 = Requestor(broker, Accounts.getFromIndex(1))
        reqID = requestor1.createRequest(amountOfExecutors=1)
        with pytest.raises(Exception, match="You cant rotate a request that was not made by you"):
            requestor2.rotateExecutors(reqID)