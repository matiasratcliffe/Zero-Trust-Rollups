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
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        executor2 = Executor(broker, Accounts.getFromIndex(1), True)
        executor3 = Executor(broker, Accounts.getFromIndex(2), True)
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
        assert executor1.getState() == "locked"
        assert executor2.getState() == "locked"
        assert executor3.getState() == "locked"
        assert executor1.account in assignedExecutors
        assert executor2.account in assignedExecutors
        assert executor3.account in assignedExecutors
        for i in range(3):
            taskAssignment = dict(requestor.broker.taskAssignmentsMap(reqID, i))
            assert int(taskAssignment["signedResultHash"].hex(), 16) == 0
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
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        executor2 = Executor(broker, Accounts.getFromIndex(1), True)
        executor3 = Executor(broker, Accounts.getFromIndex(2), True)
        assert executor1.getState() == "active"
        assert executor2.getState() == "active"
        assert executor3.getState() == "active"
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input reference", "code reference", amountOfExecutors=3, executionPower=1000)

        executor4 = Executor(broker, Accounts.getFromIndex(3), True)
        executor5 = Executor(broker, Accounts.getFromIndex(4), True)
        executor6 = Executor(broker, Accounts.getFromIndex(5), True)
        time.sleep(broker.EXECUTION_TIME_FRAME_SECONDS())

        customGasPrice = 10
        originalBalance = requestor.account.balance()
        transaction = requestor.rotateExecutors(reqID, customGasPrice=customGasPrice)
        assignedExecutors = [dict(requestor.broker.taskAssignmentsMap(reqID, i))["executorAddress"] for i in range(3)]
        assert executor1.account not in assignedExecutors
        assert executor2.account not in assignedExecutors
        assert executor3.account not in assignedExecutors
        assert executor1.getState() == "inactive"
        assert executor2.getState() == "inactive"
        assert executor3.getState() == "inactive"
        assert executor4.account in assignedExecutors
        assert executor5.account in assignedExecutors
        assert executor6.account in assignedExecutors
        assert executor4.getState() == "locked"
        assert executor5.getState() == "locked"
        assert executor6.getState() == "locked"
        assert transaction.gas_price == customGasPrice
        assert requestor.account.balance() > originalBalance - (transaction.gas_used * transaction.gas_price)
        executor1PunishAmount = broker.BASE_STAKE_AMOUNT() - executor1.getData()["lockedWei"]
        executor2PunishAmount = broker.BASE_STAKE_AMOUNT() - executor2.getData()["lockedWei"]
        executor3PunishAmount = broker.BASE_STAKE_AMOUNT() - executor3.getData()["lockedWei"]
        assert executor1PunishAmount > 0
        assert executor1PunishAmount == executor2PunishAmount
        assert executor2PunishAmount == executor3PunishAmount
        assert requestor.account.balance() == originalBalance - (transaction.gas_used * transaction.gas_price) + (executor1PunishAmount + executor2PunishAmount + executor3PunishAmount)
        assert executor4.getData()["lockedWei"] == broker.BASE_STAKE_AMOUNT()
        assert executor5.getData()["lockedWei"] == broker.BASE_STAKE_AMOUNT()
        assert executor6.getData()["lockedWei"] == broker.BASE_STAKE_AMOUNT()

    def test_rotate_one_executor(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        executor2 = Executor(broker, Accounts.getFromIndex(1), True)
        executor3 = Executor(broker, Accounts.getFromIndex(2), True)
        assert executor1.getState() == "active"
        assert executor2.getState() == "active"
        assert executor3.getState() == "active"
        requestor = Requestor(broker, Accounts.getAccount())
        inputReference = "input reference"
        codeReference = "code reference"
        reqID = requestor.createRequest(inputReference, codeReference, amountOfExecutors=3, executionPower=1000)
        result1 = executor1._getFinalState(inputReference, codeReference, 1000)
        result2 = executor2._getFinalState(inputReference, codeReference, 1000)
        assert result1 == result2
        executor1._submitSignedHash(reqID, result1)
        executor2._submitSignedHash(reqID, result2)
        assert dict(broker.taskAssignmentsMap(reqID, executor1.getData()["taskAssignmentIndex"]))["submitted"] == True
        assert dict(broker.taskAssignmentsMap(reqID, executor1.getData()["taskAssignmentIndex"]))["solidified"] == False
        assert dict(broker.taskAssignmentsMap(reqID, executor2.getData()["taskAssignmentIndex"]))["submitted"] == True
        assert dict(broker.taskAssignmentsMap(reqID, executor2.getData()["taskAssignmentIndex"]))["solidified"] == False
        assert dict(broker.taskAssignmentsMap(reqID, executor1.getData()["taskAssignmentIndex"]))["signedResultHash"] != dict(broker.taskAssignmentsMap(reqID, executor2.getData()["taskAssignmentIndex"]))["signedResultHash"]
        assert dict(broker.taskAssignmentsMap(reqID, executor3.getData()["taskAssignmentIndex"]))["submitted"] == False
        assert dict(broker.taskAssignmentsMap(reqID, executor3.getData()["taskAssignmentIndex"]))["solidified"] == False
        assert int(dict(broker.taskAssignmentsMap(reqID, executor3.getData()["taskAssignmentIndex"]))["signedResultHash"].hex(), 16) == 0
        
        executor4 = Executor(broker, Accounts.getFromIndex(3), True)
        executor5 = Executor(broker, Accounts.getFromIndex(4), True)
        executor6 = Executor(broker, Accounts.getFromIndex(5), True)
        executor5.pauseExecutor()
        executor6.pauseExecutor()
        time.sleep(broker.EXECUTION_TIME_FRAME_SECONDS())
        assert executor1.getState() == "locked"
        assert executor2.getState() == "locked"
        assert executor3.getState() == "locked"
        
        customGasPrice = 10
        originalBalance = requestor.account.balance()
        transaction = requestor.rotateExecutors(reqID, customGasPrice)
        executor5.activateExecutor()
        executor6.activateExecutor()
        assignedExecutors = [dict(requestor.broker.taskAssignmentsMap(reqID, i))["executorAddress"] for i in range(3)]
        assert executor3.account not in assignedExecutors
        assert executor5.account not in assignedExecutors
        assert executor6.account not in assignedExecutors
        assert executor3.getState() == "inactive"
        assert executor5.getState() == "active"
        assert executor6.getState() == "active"
        assert executor1.account in assignedExecutors
        assert executor2.account in assignedExecutors
        assert executor4.account in assignedExecutors
        assert executor1.getState() == "locked"
        assert executor2.getState() == "locked"
        assert executor4.getState() == "locked"
        assert transaction.gas_price == customGasPrice
        assert requestor.account.balance() > originalBalance - (transaction.gas_used * transaction.gas_price)
        executor3PunishAmount = broker.BASE_STAKE_AMOUNT() - executor3.getData()["lockedWei"]
        assert executor3PunishAmount > 0
        assert requestor.account.balance() == originalBalance - (transaction.gas_used * transaction.gas_price) + executor3PunishAmount
        assert executor1.getData()["lockedWei"] == broker.BASE_STAKE_AMOUNT()
        assert executor2.getData()["lockedWei"] == broker.BASE_STAKE_AMOUNT()
        assert executor4.getData()["lockedWei"] == broker.BASE_STAKE_AMOUNT()
        assert executor5.getData()["lockedWei"] == broker.BASE_STAKE_AMOUNT()
        assert executor6.getData()["lockedWei"] == broker.BASE_STAKE_AMOUNT()

    def test_rotate_no_executors_completion(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        executor2 = Executor(broker, Accounts.getFromIndex(1), True)
        executor3 = Executor(broker, Accounts.getFromIndex(2), True)
        requestor = Requestor(broker, Accounts.getAccount())
        inputReference = "input reference"
        codeReference = "code reference"
        reqID = requestor.createRequest(inputReference, codeReference, amountOfExecutors=3, executionPower=1000)
        executor4 = Executor(broker, Accounts.getFromIndex(3), True)
        executor5 = Executor(broker, Accounts.getFromIndex(4), True)
        executor6 = Executor(broker, Accounts.getFromIndex(5), True)
        result1 = executor1._getFinalState(inputReference, codeReference, 1000)
        result2 = executor2._getFinalState(inputReference, codeReference, 1000)
        result3 = executor3._getFinalState(inputReference, codeReference, 1000)
        executor1._submitSignedHash(reqID, result1)
        executor2._submitSignedHash(reqID, result2)
        executor3._submitSignedHash(reqID, result3)
        assert executor1.getState() == "locked"
        assert executor2.getState() == "locked"
        assert executor3.getState() == "locked"
        assert executor4.getState() == "active"
        assert executor5.getState() == "active"
        assert executor6.getState() == "active"
        assert dict(broker.taskAssignmentsMap(reqID, executor1.getData()["taskAssignmentIndex"]))["submitted"] == True
        assert dict(broker.taskAssignmentsMap(reqID, executor2.getData()["taskAssignmentIndex"]))["submitted"] == True
        assert dict(broker.taskAssignmentsMap(reqID, executor3.getData()["taskAssignmentIndex"]))["submitted"] == True
        time.sleep(broker.EXECUTION_TIME_FRAME_SECONDS())
        with pytest.raises(Exception, match="All executors for this request have already delivered"):
            requestor.rotateExecutors(reqID)
        assert dict(broker.requests(reqID))["submissionsLocked"] == True
        assert executor1.getState() == "locked"
        assert executor2.getState() == "locked"
        assert executor3.getState() == "locked"
        assert executor4.getState() == "active"
        assert executor5.getState() == "active"
        assert executor6.getState() == "active"

    def test_rotate_no_executors_premature(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        executor2 = Executor(broker, Accounts.getFromIndex(1), True)
        executor3 = Executor(broker, Accounts.getFromIndex(2), True)
        requestor = Requestor(broker, Accounts.getAccount())
        inputReference = "input reference"
        codeReference = "code reference"
        reqID = requestor.createRequest(inputReference, codeReference, amountOfExecutors=3, executionPower=1000)
        executor4 = Executor(broker, Accounts.getFromIndex(3), True)
        executor5 = Executor(broker, Accounts.getFromIndex(4), True)
        executor6 = Executor(broker, Accounts.getFromIndex(5), True)
        assert executor1.getState() == "locked"
        assert executor2.getState() == "locked"
        assert executor3.getState() == "locked"
        assert executor4.getState() == "active"
        assert executor5.getState() == "active"
        assert executor6.getState() == "active"
        requestor.rotateExecutors(reqID)
        assert executor1.getState() == "locked"
        assert executor2.getState() == "locked"
        assert executor3.getState() == "locked"
        assert executor4.getState() == "active"
        assert executor5.getState() == "active"
        assert executor6.getState() == "active"

    def test_rotate_executors_all_exceeded_but_none_available(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        executor2 = Executor(broker, Accounts.getFromIndex(1), True)
        executor3 = Executor(broker, Accounts.getFromIndex(2), True)
        executor4 = Executor(broker, Accounts.getFromIndex(3), True)
        executor5 = Executor(broker, Accounts.getFromIndex(4), True)
        executor6 = Executor(broker, Accounts.getFromIndex(5), True)
        executor4.pauseExecutor()
        executor5.pauseExecutor()
        executor6.pauseExecutor()
        assert executor1.getState() == "active"
        assert executor2.getState() == "active"
        assert executor3.getState() == "active"
        assert executor4.getState() == "inactive"
        assert executor5.getState() == "inactive"
        assert executor6.getState() == "inactive"
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input reference", "code reference", amountOfExecutors=3, executionPower=1000)
        assert executor1.getState() == "locked"
        assert executor2.getState() == "locked"
        assert executor3.getState() == "locked"
        assert executor4.getState() == "inactive"
        assert executor5.getState() == "inactive"
        assert executor6.getState() == "inactive"
        time.sleep(broker.EXECUTION_TIME_FRAME_SECONDS())
        assert requestor.rotateExecutors(reqID).return_value == False
        executor4.activateExecutor()
        executor5.activateExecutor()
        executor6.activateExecutor()
        assert executor1.getState() == "locked"
        assert executor2.getState() == "locked"
        assert executor3.getState() == "locked"
        assert executor4.getState() == "active"
        assert executor5.getState() == "active"
        assert executor6.getState() == "active"

    def test_rotate_executors_all_exceeded_but_only_some_available(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        executor2 = Executor(broker, Accounts.getFromIndex(1), True)
        executor3 = Executor(broker, Accounts.getFromIndex(2), True)
        executor4 = Executor(broker, Accounts.getFromIndex(3), True)
        executor4.pauseExecutor()
        requestor = Requestor(broker, Accounts.getAccount())
        inputReference = "input reference"
        codeReference = "code reference"
        reqID = requestor.createRequest(inputReference, codeReference, amountOfExecutors=3, executionPower=1000)
        executor4.activateExecutor()
        assert executor1.getState() == "locked"
        assert executor2.getState() == "locked"
        assert executor3.getState() == "locked"
        assert executor4.getState() == "active"
        time.sleep(broker.EXECUTION_TIME_FRAME_SECONDS())
        originalBalance = requestor.account.balance()
        transaction = requestor.rotateExecutors(reqID, 10)
        activeExecutors = [executor2, executor3, executor4]
        inactiveExecutor = executor1
        if executor1.getState() == "locked":
            if executor2.getState() == "locked":
                inactiveExecutor = executor3
                activeExecutors = [executor1, executor2, executor4]
            else:
                inactiveExecutor = executor2
                activeExecutors = [executor1, executor3, executor4]
        for i in range(3):
            assert activeExecutors[i].getState() == "locked"
            assert activeExecutors[i].getData()["lockedWei"] == broker.BASE_STAKE_AMOUNT()
            assert activeExecutors[i].getData()["accurateSolvings"] == 0
            assert activeExecutors[i].getData()["inaccurateSolvings"] == 0
            assert activeExecutors[i].getData()["timesPunished"] == 0
            
        punishAmount = broker.BASE_STAKE_AMOUNT() - inactiveExecutor.getData()["lockedWei"]
        assert requestor.account.balance() == originalBalance - (transaction.gas_used * transaction.gas_price) + punishAmount
        assert inactiveExecutor.getState() == "inactive"
        assert inactiveExecutor.getData()["accurateSolvings"] == 0
        assert inactiveExecutor.getData()["inaccurateSolvings"] == 0
        assert inactiveExecutor.getData()["timesPunished"] == 1
        
        for i in range(len(activeExecutors)):
            activeExecutors[i]._submitSignedHash(reqID, activeExecutors[i]._getFinalState(inputReference, codeReference, 1000))
        with pytest.raises(Exception, match="All executors for this request have already delivered"):
            requestor.rotateExecutors(reqID)
        assert dict(broker.requests(reqID))["submissionsLocked"] == True
        assert dict(broker.taskAssignmentsMap(reqID, 0))["submitted"] == True
        assert dict(broker.taskAssignmentsMap(reqID, 0))["solidified"] == False
        assert dict(broker.taskAssignmentsMap(reqID, 1))["submitted"] == True
        assert dict(broker.taskAssignmentsMap(reqID, 1))["solidified"] == False
        assert dict(broker.taskAssignmentsMap(reqID, 2))["submitted"] == True
        assert dict(broker.taskAssignmentsMap(reqID, 2))["solidified"] == False
        assert dict(broker.taskAssignmentsMap(reqID, 0))["signedResultHash"] != dict(broker.taskAssignmentsMap(reqID, 1))["signedResultHash"]
        assert dict(broker.taskAssignmentsMap(reqID, 1))["signedResultHash"] != dict(broker.taskAssignmentsMap(reqID, 2))["signedResultHash"]
        assert dict(broker.taskAssignmentsMap(reqID, 2))["signedResultHash"] != dict(broker.taskAssignmentsMap(reqID, 0))["signedResultHash"]

    def test_rotate_foreign_request(self):
        broker = BrokerFactory.create()
        Executor(broker, Accounts.getAccount(), True)
        requestor1 = Requestor(broker, Accounts.getFromIndex(0))
        requestor2 = Requestor(broker, Accounts.getFromIndex(1))
        reqID = requestor1.createRequest(amountOfExecutors=1)
        with pytest.raises(Exception, match="You cant rotate a request that was not made by you"):
            requestor2.rotateExecutors(reqID)