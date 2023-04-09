from scripts.classes.utils.contractProvider import BrokerFactory, ClientFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from brownie.convert.datatypes import HexString
from scripts.classes.requestor import Requestor
from scripts.classes.executor import Executor
import pytest
import time


class TestExecutor:
    def setup_method(self, method):
        Logger.indentationLevel=0

    def teardown_method(self, method):
        pass

    # TODO tests de ExecutionBroker y de executor (comportamiento de los buffers y eventos), isrequestopen?
    # TODO tests de transferable

    def test_is_request_open(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        assert broker.isRequestOpen(reqID) == True
        requestor.cancelRequest(reqID)
        assert broker.isRequestOpen(reqID) == False
    
    def test_request_count(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        originalCount = broker.requestCount()
        requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        assert broker.requestCount() == originalCount + 1

    def test_accept_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        assert int(broker.requests(reqID)[7][0], 16) == 0
        executor._acceptRequest(reqID)
        #time.sleep(2)
        assert broker.requests(reqID)[7][0] == executor.account

    def test_accept_cancelled_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        requestor.cancelRequest(reqID)
        assert broker.requests(reqID)[9] == True
        with pytest.raises(Exception, match="The request was cancelled"):
            executor._acceptRequest(reqID)

    def test_accept_accepted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        assert int(broker.requests(reqID)[7][0], 16) == 0
        executor._acceptRequest(reqID)
        with pytest.raises(Exception, match="Someone already accepted the request"):
            executor._acceptRequest(reqID)        

    def test_accept_request_wrong_insurance(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18, requestedInsurance=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        with pytest.raises(Exception, match="Incorrect amount of insurance provided"):
            broker.acceptRequest(reqID, {'from': Accounts.getAccount(), 'value': 0})
        with pytest.raises(Exception, match="Incorrect amount of insurance provided"):
            broker.acceptRequest(reqID, {'from': Accounts.getAccount(), 'value': 2e+18})

    def test_accept_non_existing_request(self):
        executor = Executor(Accounts.getAccount(), BrokerFactory.getInstance(), populateBuffers=False)
        with pytest.raises(Exception):
            executor._acceptRequest(executor.broker.requestCount())

    def test_cancel_acceptance(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        executor._cancelAcceptance(reqID)
        #time.sleep(2)
        assert int(broker.requests(reqID)[7][0], 16) == 0
    
    def test_cancel_acceptance_on_non_existing_request(self):
        executor = Executor(Accounts.getAccount(), BrokerFactory.getInstance(), populateBuffers=False)
        with pytest.raises(Exception):
            executor._cancelAcceptance(executor.broker.requestCount())

    def test_cancel_acceptance_on_unaccepted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        with pytest.raises(Exception, match="There is no acceptance in place for the provided requestID"):
            executor._cancelAcceptance(reqID)

    def test_cancel_acceptance_on_submitted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        executor._submitResult(reqID, result)
        #time.sleep(2)
        assert broker.requests(reqID)[8][0] == executor.account
        with pytest.raises(Exception, match="This request already has a submission"):
            executor._cancelAcceptance(reqID)

    def test_cancel_foreign_acceptance(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        #time.sleep(2)
        assert broker.requests(reqID)[7][0] == executor1.account
        with pytest.raises(Exception, match="You cant cancel an acceptance that does not belong to you"):
            executor2._cancelAcceptance(reqID)

    def test_submit_result(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        executor._submitResult(reqID, result)
        #time.sleep(2)
        assert broker.requests(reqID)[8][0] == executor.account
        assert broker.requests(reqID)[8][2] == result
        assert broker.requests(reqID)[8][3] == False

    def test_submit_result_for_unaccepted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        result = executor._computeResult(reqID)
        with pytest.raises(Exception, match="You need to accept the request first"):
            executor._submitResult(reqID, result)

    def test_submit_result_for_already_submitted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        executor._submitResult(reqID, result)
        #time.sleep(2)
        with pytest.raises(Exception, match="There is already a submission for this request"):
            executor._submitResult(reqID, result)

    def test_submit_result_for_foreign_acceptance(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        result = executor2._computeResult(reqID)
        with pytest.raises(Exception, match="Someone else has accepted the Request"):
            executor2._submitResult(reqID, result)

    def test_challenge_erroneous_submission(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        result = executor1._computeResult(reqID)
        alteredResult = HexString((int.from_bytes(result, "big") + 1), "bytes32")
        executor1._submitResult(reqID, alteredResult)
        assert broker.requests(reqID)[8][0] == executor1.account
        assert broker.requests(reqID)[8][2] == alteredResult
        assert broker.requests(reqID)[8][3] == False
        originalBalance = executor2.account.balance()
        challengeSuccess = executor2._challengeSubmission(reqID).return_value
        assert challengeSuccess == True
        assert broker.requests(reqID)[8][0] == executor2.account
        assert broker.requests(reqID)[8][2] == result
        assert broker.requests(reqID)[8][3] == True
        Logger.log(f"Pre-Challenge balance: {originalBalance} ----- Post-Challenge balance: {executor2.account.balance()}")
        raise "check with -i challenge gas y por que me emite el evento con un reqID incrementado???"

    def test_challenge_correct_submission(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        result = executor1._computeResult(reqID)
        executor1._submitResult(reqID, result)
        assert broker.requests(reqID)[8][0] == executor1.account
        assert broker.requests(reqID)[8][2] == result
        assert broker.requests(reqID)[8][3] == False
        challengeSuccess = executor2._challengeSubmission(reqID).return_value
        assert challengeSuccess == False
        assert broker.requests(reqID)[8][0] == executor1.account
        assert broker.requests(reqID)[8][2] == result
        assert broker.requests(reqID)[8][3] == False

    def test_challenge_unsibmitted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        with pytest.raises(Exception, match="There are no submissions for the challenged request"):
            executor._challengeSubmission(reqID)
        executor._acceptRequest(reqID)
        with pytest.raises(Exception, match="There are no submissions for the challenged request"):
            executor._challengeSubmission(reqID)

    def test_challenge_solidified_submission(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        alteredResult = HexString((int.from_bytes(executor._computeResult(reqID), "big") + 1), "bytes32")
        executor._submitResult(reqID, alteredResult)
        assert broker.requests(reqID)[8][3] == False
        executor._challengeSubmission(reqID)
        assert broker.requests(reqID)[8][3] == True
        with pytest.raises(Exception, match="The challenged submission has already solidified"):
            executor._challengeSubmission(reqID)

    def test_claim_payment(self):
        requestor = Requestor(ClientFactory.getInstance())  # TODO todos los tests en los que compare gas, revisar que aveces se usa la misma cuenta para el cliente y el executor, aunque quizas, como tomo el original balance despues de la creacion de las requests, no me afecte. pero por prolijidad es mejor separarlo
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        originalBalance = executor.account.balance()
        transaction1 = executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        transaction2 = executor._submitResult(reqID, result)
        time.sleep(2)
        assert broker.requests(reqID)[8][0] == executor.account
        assert broker.requests(reqID)[8][3] == False
        preClaimBalance = executor.account.balance()
        transaction3 = broker.claimPayment(reqID, {"from": executor.account})
        time.sleep(2)
        assert transaction3.return_value == True
        assert broker.requests(reqID)[8][0] == executor.account
        assert broker.requests(reqID)[8][3] == True
        assert executor.account.balance() == preClaimBalance - (transaction1.gas_used * transaction1.gas_price) - (transaction2.gas_used * transaction2.gas_price) - (transaction3.gas_used * transaction3.gas_price) + broker.requests(reqID)[2] + broker.requests(reqID)[4]
        Logger.log(f"Pre-Execution balance: {originalBalance} ----- Post-Execution balance: {executor.account.balance()}")
        #TODO no tengo en cuenta el tema de post processing gas para ver el tema del costo total y la conveniencia


    def test_claim_foreign_payment(self):
        pass

    def test_claim_solidified_payment(self):
        pass

    def test_claim_premature_payment(self):
        pass

    def test_solver_loop_round(self):
        pass

    def test_challenger_loop_round(self):
        pass

    #TODO test post process result
    # Test Transferable TODO??? worth it???