from scripts.classes.utils.contractProvider import BrokerFactory, ClientFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from brownie.convert.datatypes import HexString
from scripts.classes.requestor import Requestor
from scripts.classes.executor import Executor
from brownie import network
import pytest
import time


class TestExecutor:
    def setup(self):
        pass

    def teardown(self):
        pass

    def setup_method(self, method):
        Logger.indentationLevel=0

    def teardown_method(self, method):
        network.event.event_watcher.reset()

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
        assert int(dict(broker.requests(reqID))["acceptance"][0], 16) == 0
        executor._acceptRequest(reqID)
        assert dict(broker.requests(reqID))["acceptance"][0] == executor.account

    def test_accept_cancelled_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        requestor.cancelRequest(reqID)
        assert dict(broker.requests(reqID))["cancelled"] == True
        with pytest.raises(Exception, match="The request was cancelled"):
            executor._acceptRequest(reqID)

    def test_accept_accepted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        assert int(dict(broker.requests(reqID))["acceptance"][0], 16) == 0
        executor._acceptRequest(reqID)
        with pytest.raises(Exception, match="There already is an unexpired acceptance for this request"):
            executor._acceptRequest(reqID)

    def test_overtake_expired_acceptance(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        assert int(dict(broker.requests(reqID))["acceptance"][0], 16) == 0
        originalBalance1 = executor1.account.balance()
        transaction1 = executor1._acceptRequest(reqID)
        assert dict(broker.requests(reqID))["acceptance"][0] == executor1.account
        assert executor1.account.balance() == originalBalance1 - (transaction1.gas_used * transaction1.gas_price) - dict(broker.requests(reqID))["challengeInsurance"]
        with pytest.raises(Exception, match="There already is an unexpired acceptance for this request"):
            executor2._acceptRequest(reqID)
        time.sleep(6)
        originalBalance1 = executor1.account.balance()
        originalBalance2 = executor2.account.balance()
        transaction2 = executor2._acceptRequest(reqID)
        assert dict(broker.requests(reqID))["acceptance"][0] == executor2.account
        assert executor2.account.balance() == originalBalance2 - (transaction2.gas_used * transaction2.gas_price) - dict(broker.requests(reqID))["challengeInsurance"]
        assert executor1.account.balance() == originalBalance1 + dict(broker.requests(reqID))["challengeInsurance"]

    def test_accept_submitted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        executor._submitResult(reqID, result)
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor.account
        assert dict(dict(broker.requests(reqID))["submission"])["result"] == result
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == False
        with pytest.raises(Exception, match="There is already a submission for this request"):
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
        assert int(dict(broker.requests(reqID))["acceptance"][0], 16) == 0
    
    def test_cancel_acceptance_on_non_existing_request(self):
        executor = Executor(Accounts.getAccount(), BrokerFactory.getInstance(), populateBuffers=False)
        with pytest.raises(Exception):
            executor._cancelAcceptance(executor.broker.requestCount())
        del executor

    def test_cancel_acceptance_on_unaccepted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        with pytest.raises(Exception, match="There is no acceptor for the provided requestID"):
            executor._cancelAcceptance(reqID)
        del executor

    def test_cancel_acceptance_on_submitted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        executor._submitResult(reqID, result)
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor.account
        with pytest.raises(Exception, match="This request already has a submission"):
            executor._cancelAcceptance(reqID)
        del executor

    def test_cancel_foreign_acceptance(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        assert dict(broker.requests(reqID))["acceptance"][0] == executor1.account
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
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor.account
        assert dict(dict(broker.requests(reqID))["submission"])["result"] == result
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == False

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
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor1.account
        assert dict(dict(broker.requests(reqID))["submission"])["result"] == alteredResult
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == False
        originalBalance = executor2.account.balance()
        transaction = executor2._challengeSubmission(reqID)
        challengeSuccess = transaction.return_value
        assert challengeSuccess == True
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor2.account
        assert dict(dict(broker.requests(reqID))["submission"])["result"] == result
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == True
        assert executor2.account.balance() == originalBalance - (transaction.gas_used * transaction.gas_price) + dict(broker.requests(reqID))["payment"] + dict(broker.requests(reqID))["challengeInsurance"]
        Logger.log(f"Pre-Challenge balance: {originalBalance} ----- Post-Challenge balance: {executor2.account.balance()}")

    def test_challenge_correct_submission(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        result = executor1._computeResult(reqID)
        executor1._submitResult(reqID, result)
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor1.account
        assert dict(dict(broker.requests(reqID))["submission"])["result"] == result
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == False
        originalBalance1 = executor1.account.balance()
        originalBalance2 = executor2.account.balance()
        transaction = executor2._challengeSubmission(reqID)
        challengeSuccess = transaction.return_value
        assert challengeSuccess == False
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor1.account
        assert dict(dict(broker.requests(reqID))["submission"])["result"] == result
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == True
        assert executor1.account.balance() == originalBalance1 + dict(broker.requests(reqID))["payment"] + dict(broker.requests(reqID))["challengeInsurance"]
        assert executor2.account.balance() == originalBalance2 - (transaction.gas_used * transaction.gas_price)

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
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == False
        executor._challengeSubmission(reqID)
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == True
        with pytest.raises(Exception, match="The challenged submission has already solidified"):
            executor._challengeSubmission(reqID)

    def test_claim_payment(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        originalBalance = executor.account.balance()
        transaction1 = executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        transaction2 = executor._submitResult(reqID, result)
        time.sleep(2)
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor.account
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == False
        preClaimBalance = executor.account.balance()
        time.sleep(3)
        transaction3 = broker.claimPayment(reqID, {"from": executor.account})
        time.sleep(2)
        assert transaction3.return_value == True
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor.account
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == True
        assert executor.account.balance() == preClaimBalance - (transaction1.gas_used * transaction1.gas_price) - (transaction2.gas_used * transaction2.gas_price) - (transaction3.gas_used * transaction3.gas_price) + dict(broker.requests(reqID))["payment"] + dict(broker.requests(reqID))["challengeInsurance"]
        Logger.log(f"Pre-Execution balance: {originalBalance} ----- Post-Execution balance: {executor.account.balance()}")

    def test_claim_payment_for_unsubmitted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        with pytest.raises(Exception, match="There are no submissions for the provided request"):
            broker.claimPayment(reqID, {"from": Accounts.getAccount()})

    def test_claim_foreign_payment(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        executor._submitResult(reqID, result)
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor.account
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == False
        with pytest.raises(Exception, match="This payment does not belong to you"):
            broker.claimPayment(reqID, {"from": Accounts.getFromIndex(1)})

    def test_claim_solidified_payment(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        alteredResult = HexString((int.from_bytes(executor._computeResult(reqID), "big") + 1), "bytes32")
        executor._submitResult(reqID, alteredResult)
        executor._challengeSubmission(reqID)
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == True
        with pytest.raises(Exception, match="The provided request has already solidified"):
            broker.claimPayment(reqID, {"from": executor.account})

    def test_claim_premature_payment(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18, claimDelay=3600)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        executor._submitResult(reqID, result)
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor.account
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == False
        with pytest.raises(Exception, match="The claim delay hasn't passed yet"):
            broker.claimPayment(reqID, {"from": executor.account})

    def test_populate_unaccepted_requests_buffer(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=True)
        assert reqID in executor.unacceptedRequests

    def test_populate_unsolidified_submissions_buffer(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        result = executor1._computeResult(reqID)
        executor1._submitResult(reqID, result)
        executor2 = Executor(Accounts.getAccount(), broker, populateBuffers=True)
        assert reqID in executor2.unsolidifiedSubmissions

    def test_listen_to_request_created_event(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        time.sleep(4)
        assert reqID in executor.unacceptedRequests

    def test_listen_to_acceptance_cancelled_event(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        executor1._acceptRequest(reqID)
        executor2 = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        assert reqID not in executor2.unacceptedRequests
        executor1._cancelAcceptance(reqID)
        time.sleep(5)
        assert reqID in executor2.unacceptedRequests

    def test_listen_to_request_cancelled_event(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=True)
        assert reqID in executor.unacceptedRequests
        requestor.cancelRequest(reqID)
        time.sleep(2)
        assert reqID not in executor.unacceptedRequests

    def test_listen_to_request_accepted_event(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        executor2 = Executor(Accounts.getAccount(), broker, populateBuffers=True)
        assert reqID in executor2.unacceptedRequests
        executor1._acceptRequest(reqID)
        time.sleep(2)
        assert reqID not in executor2.unacceptedRequests

    def test_listen_to_result_submitted_event(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        result = executor1._computeResult(reqID)
        executor2 = Executor(Accounts.getAccount(), broker, populateBuffers=True)
        assert reqID not in executor2.unsolidifiedSubmissions
        executor1._submitResult(reqID, result)
        time.sleep(4)
        assert reqID in executor2.unsolidifiedSubmissions

    def test_listen_to_request_solidified_event(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        alteredResult = HexString((int.from_bytes(executor1._computeResult(reqID), "big") + 1), "bytes32")
        executor1._submitResult(reqID, alteredResult)
        executor2 = Executor(Accounts.getAccount(), broker, populateBuffers=True)
        assert reqID in executor2.unsolidifiedSubmissions
        executor1._challengeSubmission(reqID)
        time.sleep(3) # TODO ver tema timers si es por el exceso de threads, si al matarlos se relaja
        assert reqID not in executor2.unsolidifiedSubmissions

    def test_solver_loop_round(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        time.sleep(3)
        executor.solverLoopRound()
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor.account
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == False
        assert executor._challengeSubmission(reqID).return_value == False  # TODO me parece que es mejor si el challenge me la solidifica

    def test_challenger_loop_round_erroneous_submission(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        alteredResult = HexString((int.from_bytes(executor1._computeResult(reqID), "big") + 1), "bytes32")
        executor1._submitResult(reqID, alteredResult)
        time.sleep(3)
        executor2.challengerLoopRound()
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor2.account
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == True

    def test_challenger_loop_round_correct_submission(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        result = executor1._computeResult(reqID)
        executor1._submitResult(reqID, result)
        time.sleep(3)
        executor2.challengerLoopRound()  # As the original result is correct, the function does not transact with the challengeSubmission function, leaving the request unsolidified
        assert dict(dict(broker.requests(reqID))["submission"])["issuer"] == executor1.account
        assert dict(dict(broker.requests(reqID))["submission"])["solidified"] == False

    #TODO test post process result