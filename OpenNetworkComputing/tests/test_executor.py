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

    def run_full_test(self, amountOfExecutors, resultSize, printInfo):
        resultValue = "9" * resultSize
        broker = BrokerFactory.create(account=Accounts.getFromIndex(0))
        executors = []
        for i in range(amountOfExecutors):
            executors.append(Executor(broker, Accounts.getFromIndex(i + 2), True, gas_price=1))
        requestor = Requestor(broker, Accounts.getFromIndex(1))
        request = requestor.createRequest("input state reference", "code reference", amountOfExecutors=i+1, executionPower=1000)
        requestCreationCost = request.gas_used
        reqID = request.return_value
        results = []
        submissionTXs = []
        firstSubmissionsAvgCost = 0
        for i in range(amountOfExecutors - 1):
            results.append(executors[i]._calculateFinalState(reqID, state_value=resultValue))  # Hardcoded trivial result
            submissionTXs.append(executors[i]._submitSignedHash(reqID, results[i]))
            firstSubmissionsAvgCost += submissionTXs[-1].gas_used / (amountOfExecutors - 1)
        results.append(executors[-1]._calculateFinalState(reqID, state_value=resultValue))  # Hardcoded trivial result
        submissionTXs.append(executors[-1]._submitSignedHash(reqID, results[-1]))
        assert dict(broker.requests(reqID))["submissionsLocked"] == True
        liberationTXs = []
        firstLiberationsAvgCost = 0
        for i in range(amountOfExecutors - 1):
            liberationTXs.append(executors[i]._liberateResult(reqID))
            firstLiberationsAvgCost += liberationTXs[-1].gas_used / (amountOfExecutors - 1)
        assert dict(broker.requests(reqID))["closed"] == False
        assert dict(broker.requests(reqID))["result"] == ('', '0x0000000000000000000000000000000000000000')
        liberationTXs.append(executors[-1]._liberateResult(reqID))
        results[0].signingAddress = broker.address
        assert dict(broker.requests(reqID))["closed"] == True
        assert dict(broker.requests(reqID))["result"] == results[0].toTuple()
        if printInfo:
            for i in range(amountOfExecutors):
                print(f"Executor {i + 1} registration cost: {registrationCosts[i]}")
            print("--------------------------------------------------")
            print(f"Request creation cost: {requestCreationCost}")
            print("--------------------------------------------------")
            for i in range(amountOfExecutors):
                print(f"Hash submission cost {i + 1}: {submissionTXs[i].gas_used}")
            print("--------------------------------------------------")
            for i in range(amountOfExecutors):
                print(f"Result liberation cost {i + 1}: {liberationTXs[i].gas_used}")
        return requestCreationCost, firstSubmissionsAvgCost, submissionTXs[-1].gas_used, firstLiberationsAvgCost, liberationTXs[-1].gas_used

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

    def test_submit_trivial_result_hash(self):
        broker = BrokerFactory.create()
        Executor(broker, Accounts.getFromIndex(0), True)
        Executor(broker, Accounts.getFromIndex(1), True)
        Executor(broker, Accounts.getFromIndex(2), True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input state", "code reference", amountOfExecutors=3, executionPower=1000)
        executor1 = Executor(broker, Accounts.getFromKey(dict(broker.taskAssignmentsMap(reqID, 0))["executorAddress"]), False)
        executor2 = Executor(broker, Accounts.getFromKey(dict(broker.taskAssignmentsMap(reqID, 1))["executorAddress"]), False)
        executor3 = Executor(broker, Accounts.getFromKey(dict(broker.taskAssignmentsMap(reqID, 2))["executorAddress"]), False)
        result1 = executor1._calculateFinalState(reqID)
        result2 = executor2._calculateFinalState(reqID)
        executor1._submitSignedHash(reqID, result1)
        executor2._submitSignedHash(reqID, result2)
        assert executor1.getAssignment()["submitted"] == True
        assert executor1.getAssignment()["liberated"] == False
        assert int(executor1.getAssignment()["signedResultHash"].hex(), 16) != 0
        assert executor2.getAssignment()["submitted"] == True
        assert executor2.getAssignment()["liberated"] == False
        assert int(executor2.getAssignment()["signedResultHash"].hex(), 16) != 0
        assert executor3.getAssignment()["submitted"] == False
        assert executor3.getAssignment()["liberated"] == False
        assert int(executor3.getAssignment()["signedResultHash"].hex(), 16) == 0
        assert dict(broker.requests(reqID))["submissionsLocked"] == False

    def test_submit_last_result_hash(self):
        broker = BrokerFactory.create()
        Executor(broker, Accounts.getFromIndex(0), True)
        Executor(broker, Accounts.getFromIndex(1), True)
        Executor(broker, Accounts.getFromIndex(2), True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input state", "code reference", amountOfExecutors=3, executionPower=1000)
        executor1 = Executor(broker, Accounts.getFromKey(dict(broker.taskAssignmentsMap(reqID, 0))["executorAddress"]), False)
        executor2 = Executor(broker, Accounts.getFromKey(dict(broker.taskAssignmentsMap(reqID, 1))["executorAddress"]), False)
        executor3 = Executor(broker, Accounts.getFromKey(dict(broker.taskAssignmentsMap(reqID, 2))["executorAddress"]), False)
        result1 = executor1._calculateFinalState(reqID)
        result2 = executor2._calculateFinalState(reqID)
        executor1._submitSignedHash(reqID, result1)
        executor2._submitSignedHash(reqID, result2)
        assert executor1.getAssignment()["submitted"] == True
        assert executor1.getAssignment()["liberated"] == False
        assert int(executor1.getAssignment()["signedResultHash"].hex(), 16) != 0
        assert executor2.getAssignment()["submitted"] == True
        assert executor2.getAssignment()["liberated"] == False
        assert int(executor2.getAssignment()["signedResultHash"].hex(), 16) != 0
        assert executor3.getAssignment()["submitted"] == False
        assert executor3.getAssignment()["liberated"] == False
        assert int(executor3.getAssignment()["signedResultHash"].hex(), 16) == 0
        assert dict(broker.requests(reqID))["submissionsLocked"] == False
        result3 = executor3._calculateFinalState(reqID)
        executor3._submitSignedHash(reqID, result3)
        assert executor3.getAssignment()["submitted"] == True
        assert executor3.getAssignment()["liberated"] == False
        assert int(executor3.getAssignment()["signedResultHash"].hex(), 16) != 0
        assert dict(broker.requests(reqID))["submissionsLocked"] == True
    
    def test_submit_result_hash_from_unregistered_executor(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input state", "code referece", amountOfExecutors=1, executionPower=1000)
        result1 = executor1._calculateFinalState(reqID)
        executor1._submitSignedHash(reqID, result1)
        assert dict(broker.requests(reqID))["submissionsLocked"] == True
        with pytest.raises(Exception, match="This address does not belong to a registered executor"):
            executor2 = Executor(broker, Accounts.getFromIndex(1), False)
            result2 = executor2._calculateFinalState(reqID)
            executor2._submitSignedHash(reqID, result2)

    def test_submit_result_hash_to_foreign_request(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input state", "code reference", amountOfExecutors=1, executionPower=1000)
        result1 = executor1._calculateFinalState(reqID)
        executor1._submitSignedHash(reqID, result1)
        assert dict(broker.requests(reqID))["submissionsLocked"] == True
        with pytest.raises(Exception, match="You must be assigned to the provided request to submit a result hash"):
            executor2 = Executor(broker, Accounts.getFromIndex(1), True)
            executor2._submitSignedHash(reqID, result1)

    def test_submit_an_already_submitted_result_hash(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input state", "code reference", amountOfExecutors=1, executionPower=1000)
        result1 = executor1._calculateFinalState(reqID)
        executor1._submitSignedHash(reqID, result1)
        assert dict(broker.requests(reqID))["submissionsLocked"] == True
        with pytest.raises(Exception, match="The result for this request, for this executor, has already been submitted"):
            executor1._submitSignedHash(reqID, result1)
    
    def test_liberate_first_result(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        executor2 = Executor(broker, Accounts.getFromIndex(1), True)
        executor3 = Executor(broker, Accounts.getFromIndex(2), True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input state", "code reference", amountOfExecutors=3, executionPower=1000)
        result1 = executor1._calculateFinalState(reqID)
        executor1._submitSignedHash(reqID, result1)
        result2 = executor2._calculateFinalState(reqID)
        executor2._submitSignedHash(reqID, result2)
        result3 = executor3._calculateFinalState(reqID)
        executor3._submitSignedHash(reqID, result3)
        assert dict(broker.requests(reqID))["submissionsLocked"] == True
        assert executor1.getAssignment()["submitted"] == True
        assert executor1.getAssignment()["liberated"] == False
        assert executor1.getAssignment()["executorAddress"] == executor1.account.address
        executor1._liberateResult(reqID)
        assert executor1.getAssignment()["liberated"] == True
        assert executor1.getAssignment()["signedResultHash"].hex() == result1.getHash().hex()
        result1.signingAddress = broker.address
        assert executor1.getAssignment()["unsignedResultHash"].hex() == result1.getHash().hex()
        assert executor1.getAssignment()["result"] == result1.toTuple()
        assert dict(broker.requests(reqID))["closed"] == False

    def test_liberate_last_result_all_correct(self):
        registrationCosts = []
        firstSubmissionCosts = []
        lastSubmissionCosts = []
        fisrtLiberationCosts = []
        lastLiberationCosts = []
        amountsOfExecutors = [1, 3, 5, 7]
        resultStateSizes = [256, 512, 1024, 2048]
        for resultStateSize in resultStateSizes:
            _registrationCosts = []
            _firstSubmissionCosts = []
            _lastSubmissionCosts = []
            _fisrtLiberationCosts = []
            _lastLiberationCosts = []
            for amountOfExecutors in amountsOfExecutors:
                rC, fSC, lSC, fLC, lLC = self.run_full_test(amountOfExecutors, resultStateSize, printInfo=False)
                _registrationCosts.append(rC)
                _firstSubmissionCosts.append(fSC)
                _lastSubmissionCosts.append(lSC)
                _fisrtLiberationCosts.append(fLC)
                _lastLiberationCosts.append(lLC)
            registrationCosts.append(_registrationCosts)
            firstSubmissionCosts.append(_firstSubmissionCosts)
            lastSubmissionCosts.append(_lastSubmissionCosts)
            fisrtLiberationCosts.append(_fisrtLiberationCosts)
            lastLiberationCosts.append(_lastLiberationCosts)
        print("Registration")
        for line in registrationCosts:
            print(line)
        print("\nFirst Submission")
        for line in firstSubmissionCosts:
            print(line)
        print("\nLast Submission")
        for line in lastSubmissionCosts:
            print(line)
        print("\nFirst Liberation")
        for line in fisrtLiberationCosts:
            print(line)
        print("\nLast Liberation")
        for line in lastLiberationCosts:
            print(line)

        raise "interactive console"
        #TODO ver tema GAS y STAKES

    def test_executor_registration_costs(self):
        broker = BrokerFactory.create()
        executors = []
        for i in range(30):
            executors.append(Executor(broker, Accounts.getFromIndex(i), True))
        for i, executor in enumerate(executors):
            print(f"Executor {(i+1):02d} registration cost: {executor.registrationCost}")
        raise "print results"

    def test_liberate_result_from_unregistered_executor(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input state", "code reference", amountOfExecutors=1, executionPower=1000)
        result1 = executor1._calculateFinalState(reqID)
        executor1._submitSignedHash(reqID, result1)
        assert dict(broker.requests(reqID))["submissionsLocked"] == True
        with pytest.raises(Exception, match="This address does not belong to a registered executor"):
            executor2 = Executor(broker, Accounts.getFromIndex(1), False)
            executor2.broker.liberateResult(reqID, result1.toTuple(), {"from": executor2.account})

    def test_liberate_result_to_foreign_request(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input state", "code reference", amountOfExecutors=1, executionPower=1000)
        result1 = executor1._calculateFinalState(reqID)
        executor1._submitSignedHash(reqID, result1)
        assert dict(broker.requests(reqID))["submissionsLocked"] == True
        with pytest.raises(Exception, match="You must be assigned to the provided request to liberate the result"):
            executor2 = Executor(broker, Accounts.getFromIndex(1), True)
            executor2.broker.liberateResult(reqID, result1.toTuple(), {"from": executor2.account})

    def test_liberate_an_already_liberated_result(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        executor2 = Executor(broker, Accounts.getFromIndex(1), True)
        executor3 = Executor(broker, Accounts.getFromIndex(2), True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input state", "code reference", amountOfExecutors=3, executionPower=1000)
        result1 = executor1._calculateFinalState(reqID)
        result2 = executor2._calculateFinalState(reqID)
        result3 = executor3._calculateFinalState(reqID)
        executor1._submitSignedHash(reqID, result1)
        executor2._submitSignedHash(reqID, result2)
        executor3._submitSignedHash(reqID, result3)
        executor1._liberateResult(reqID)
        with pytest.raises(Exception, match="The result for this request, for this executor, has already been liberated"):
            executor1._liberateResult(reqID)    

    def test_liberate_an_unsubmitted_result(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input state", "code reference", amountOfExecutors=1, executionPower=1000)
        result1 = executor1._calculateFinalState(reqID)
        assert dict(broker.requests(reqID))["submissionsLocked"] == False
        with pytest.raises(Exception, match="You must first submit a signed result hash before you can liberate it"):
            executor1._liberateResult(reqID)

    def test_liberate_result_to_unlocked_request(self):
        broker = BrokerFactory.create()
        executor1 = Executor(broker, Accounts.getFromIndex(0), True)
        Executor(broker, Accounts.getFromIndex(1), True)
        Executor(broker, Accounts.getFromIndex(2), True)
        requestor = Requestor(broker, Accounts.getAccount())
        reqID = requestor.createRequest("input state", "code reference", amountOfExecutors=3, executionPower=1000)
        result1 = executor1._calculateFinalState(reqID)
        executor1._submitSignedHash(reqID, result1)
        assert dict(broker.requests(reqID))["submissionsLocked"] == False
        with pytest.raises(Exception, match="You must wait until all submissions for this request have been locked"):
            executor1._liberateResult(reqID)