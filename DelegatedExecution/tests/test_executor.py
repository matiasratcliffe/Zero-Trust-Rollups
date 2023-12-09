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
        self.reference_gas_price = 58160642908  # 58 GWei

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
        assert int(broker.requests(reqID).dict()["acceptance"][0], 16) == 0
        executor._acceptRequest(reqID)
        assert broker.requests(reqID).dict()["acceptance"][0] == executor.account

    def test_accept_cancelled_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        requestor.cancelRequest(reqID)
        assert broker.requests(reqID).dict()["cancelled"] == True
        with pytest.raises(Exception, match="The request was cancelled"):
            executor._acceptRequest(reqID)

    def test_accept_accepted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        assert int(broker.requests(reqID).dict()["acceptance"][0], 16) == 0
        executor._acceptRequest(reqID)
        with pytest.raises(Exception, match="There already is an unexpired acceptance for this request"):
            executor._acceptRequest(reqID)

    def test_overtake_expired_acceptance(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        assert int(broker.requests(reqID).dict()["acceptance"][0], 16) == 0
        originalBalance1 = executor1.account.balance()
        transaction1 = executor1._acceptRequest(reqID)
        assert broker.requests(reqID).dict()["acceptance"][0] == executor1.account
        assert executor1.account.balance() == originalBalance1 - (transaction1.gas_used * transaction1.gas_price) - broker.requests(reqID).dict()["challengeInsurance"]
        with pytest.raises(Exception, match="There already is an unexpired acceptance for this request"):
            executor2._acceptRequest(reqID)
        time.sleep(6)
        originalBalance1 = executor1.account.balance()
        originalBalance2 = executor2.account.balance()
        transaction2 = executor2._acceptRequest(reqID)
        assert broker.requests(reqID).dict()["acceptance"][0] == executor2.account
        assert executor2.account.balance() == originalBalance2 - (transaction2.gas_used * transaction2.gas_price) - broker.requests(reqID).dict()["challengeInsurance"]
        assert executor1.account.balance() == originalBalance1 + broker.requests(reqID).dict()["challengeInsurance"]

    def test_accept_submitted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        executor._submitResult(reqID, result)
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor.account
        assert broker.requests(reqID).dict()["submission"].dict()["result"] == result
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == False
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
        assert int(broker.requests(reqID).dict()["acceptance"][0], 16) == 0
    
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
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor.account
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
        assert broker.requests(reqID).dict()["acceptance"][0] == executor1.account
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
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor.account
        assert broker.requests(reqID).dict()["submission"].dict()["result"] == result
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == False

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
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor1.account
        assert broker.requests(reqID).dict()["submission"].dict()["result"] == alteredResult
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == False
        originalBalance = executor2.account.balance()
        transaction = executor2._challengeSubmission(reqID)
        challengeSuccess = transaction.return_value
        assert challengeSuccess == True
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor2.account
        assert broker.requests(reqID).dict()["submission"].dict()["result"] == result
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == True
        assert executor2.account.balance() == originalBalance - (transaction.gas_used * transaction.gas_price) + broker.requests(reqID).dict()["payment"] + broker.requests(reqID).dict()["challengeInsurance"]
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
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor1.account
        assert broker.requests(reqID).dict()["submission"].dict()["result"] == result
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == False
        originalBalance1 = executor1.account.balance()
        originalBalance2 = executor2.account.balance()
        transaction = executor2._challengeSubmission(reqID)
        challengeSuccess = transaction.return_value
        assert challengeSuccess == False
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor1.account
        assert broker.requests(reqID).dict()["submission"].dict()["result"] == result
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == True
        assert executor1.account.balance() == originalBalance1 + broker.requests(reqID).dict()["payment"] + broker.requests(reqID).dict()["challengeInsurance"]
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
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == False
        executor._challengeSubmission(reqID)
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == True
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
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor.account
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == False
        preClaimBalance = executor.account.balance()
        time.sleep(3)
        transaction3 = executor._claimPayment(reqID)
        time.sleep(2)
        assert transaction3.return_value == True
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor.account
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == True
        assert executor.account.balance() == preClaimBalance - (transaction1.gas_used * transaction1.gas_price) - (transaction2.gas_used * transaction2.gas_price) - (transaction3.gas_used * transaction3.gas_price) + broker.requests(reqID).dict()["payment"] + broker.requests(reqID).dict()["challengeInsurance"]
        Logger.log(f"Pre-Execution balance: {originalBalance} ----- Post-Execution balance: {executor.account.balance()}")

    def test_claim_payment_for_unsubmitted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        with pytest.raises(Exception, match="There are no submissions for the provided request"):
            requestor.client.claimPayment(reqID, {"from": Accounts.getAccount()})

    def test_claim_foreign_payment(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        executor._submitResult(reqID, result)
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor.account
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == False
        with pytest.raises(Exception, match="This payment does not belong to you"):
            requestor.client.claimPayment(reqID, {"from": Accounts.getFromIndex(1)})

    def test_claim_solidified_payment(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        alteredResult = HexString((int.from_bytes(executor._computeResult(reqID), "big") + 1), "bytes32")
        executor._submitResult(reqID, alteredResult)
        executor._challengeSubmission(reqID)
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == True
        with pytest.raises(Exception, match="The provided request has already solidified"):
            executor._claimPayment(reqID)

    def test_claim_premature_payment(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18, claimDelay=3600)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        result = executor._computeResult(reqID)
        executor._submitResult(reqID, result)
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor.account
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == False
        with pytest.raises(Exception, match="The claim delay hasn't passed yet"):
            executor._claimPayment(reqID)

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

    def test_solver_loop_round(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        executor.unacceptedRequests = [reqID]
        executor.solverLoopRound()
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor.account
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == False
        assert executor._challengeSubmission(reqID).return_value == False

    def test_challenger_loop_round_erroneous_submission(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        alteredResult = HexString((int.from_bytes(executor1._computeResult(reqID), "big") + 1), "bytes32")
        executor1._submitResult(reqID, alteredResult)
        executor2.unsolidifiedSubmissions = [reqID]
        executor2.challengerLoopRound()
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor2.account
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == True

    def test_challenger_loop_round_correct_submission(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor1._acceptRequest(reqID)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        result = executor1._computeResult(reqID)
        executor1._submitResult(reqID, result)
        executor2.unsolidifiedSubmissions = [reqID]
        executor2.challengerLoopRound()  # As the original result is correct, the function does not transact with the challengeSubmission function, leaving the request unsolidified
        assert broker.requests(reqID).dict()["submission"].dict()["issuer"] == executor1.account
        assert broker.requests(reqID).dict()["submission"].dict()["solidified"] == False

    def test_find_first_primes(self):
        broker = BrokerFactory.create(account=Accounts.getFromIndex(0))
        requestor = Requestor(ClientFactory.create(broker, owner=Accounts.getFromIndex(1)))
        requestor.sendFunds(1e18)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[3], payment=1e13, postProcessingGas=1e12, requestedInsurance=2e14)
        executor = Executor(Accounts.getFromIndex(0), broker, populateBuffers=True)
        initialFunds = executor.account.balance()
        for i in range(20):
            executor._acceptRequest(reqID + i)
            result = executor._computeResult(reqID + i)
            executor._submitResult(reqID + i, result)
            executor._claimPayment(reqID + i)
        assert executor.account.balance() > initialFunds
        assert list(requestor.client.getPrimes()) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73]

    def test_find_first_primes_with_gas_offchain(self):
        broker = BrokerFactory.create(account=Accounts.getFromIndex(0))
        requestorAccount = Accounts.getFromIndex(1)
        initialFunds = requestorAccount.balance()
        clientContract = ClientFactory.create(broker, owner=requestorAccount, gas_price=self.reference_gas_price)
        requestor = Requestor(clientContract)
        deploymentGas = (initialFunds - requestorAccount.balance()) // self.reference_gas_price 
        request = requestor.createRequest(functionToRun=1, dataArray=[3, 1000], payment=0, postProcessingGas=0,
                                        requestedInsurance=2e14, gas_price=self.reference_gas_price, getTransaction=True)
        reqID = request.return_value
        executorAccount = Accounts.getFromIndex(0)
        executor = Executor(executorAccount, broker, populateBuffers=True)
        initialExecutorFunds = executor.account.balance()
        acceptanceTransaction = executor._acceptRequest(reqID, gas_price=self.reference_gas_price)
        result = executor._computeResult(reqID)
        submissionTransaction = executor._submitResult(reqID, result, gas_price=self.reference_gas_price)
        paymentTransaction = executor._claimPayment(reqID, gas_price=self.reference_gas_price)
        executionCost = initialExecutorFunds - executorAccount.balance()
        print(f"Deployment gas: {deploymentGas}")
        print(f"Request creation gas: {request.gas_used}")
        print("-------------------------------")
        print(f"Acceptance gas: {acceptanceTransaction.gas_used}")
        print(f"Submission gas: {submissionTransaction.gas_used}")
        print(f"Payment gas: {paymentTransaction.gas_used}")
        print("-------------------------------")
        print(clientContract.getPrimes())
        #raise "activate interactive console"
        #assert executor.account.balance() > initialFunds
        #assert list(requestor.client.getPrimes()) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73]

    def test_confirm_result_no_submissions(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        with pytest.raises(Exception, match="There are no submissions for this request"):
            executor._confirmResult(reqID)
    
    def test_confirm_solidified_result(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18, claimDelay=0)
        executor.unacceptedRequests = [reqID]
        executor.solverLoopRound()
        executor._claimPayment(reqID)
        with pytest.raises(Exception, match="This request has already been solidified"):
            executor._confirmResult(reqID)

    def test_confirm_own_result(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        executor.unacceptedRequests = [reqID]
        executor.solverLoopRound()
        with pytest.raises(Exception, match="You cant confirm your own result"):
            executor._confirmResult(reqID)
    
    def test_confirm_result_twice(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        executor1.unacceptedRequests = [reqID]
        executor1.solverLoopRound()
        executor2._confirmResult(reqID)
        with pytest.raises(Exception, match="You have already confirmed this result"):
            executor2._confirmResult(reqID)

    def test_confirm_result_max_confirmations(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        executor3 = Executor(Accounts.getFromIndex(2), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        executor1.unacceptedRequests = [reqID]
        executor1.solverLoopRound()
        executor2._confirmResult(reqID)
        executor3._confirmResult(reqID)
        with pytest.raises(Exception, match="This request has reached max confirmation"):
            executor2._confirmResult(reqID)
    
    def test_confirm_result_wrong_amount_of_insurance(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        executor1.unacceptedRequests = [reqID]
        executor1.solverLoopRound()
        with pytest.raises(Exception, match="You need to deposit a percentage of the insurance fee to confirm"):
            executor2.broker.confirmResult(reqID, {"from": executor2.account})
    
    def test_confirm_correct_result(self):
        requestor = Requestor(ClientFactory.getInstance())
        requestor.togglePostProcessing()
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18, claimDelay=0)
        request = broker.requests(reqID).dict()
        executor1.unacceptedRequests = [reqID]
        executor1.solverLoopRound()
        executor2._confirmResult(reqID)
        requestorOriginalBalance = requestor.client.balance()
        executor1OriginalBalance = executor1.account.balance()
        executor2OriginalBalance = executor2.account.balance()
        tx = executor1._claimPayment(reqID)
        assert requestor.client.balance() == requestorOriginalBalance + (request["payment"] * broker.CONFIRMERS_FEE_PERCENTAGE()) / 100
        assert executor1.account.balance() == executor1OriginalBalance + (request["payment"] + request["challengeInsurance"]) - (tx.gas_used * tx.gas_price)
        assert executor2.account.balance() == executor2OriginalBalance + ((request["payment"] + request["challengeInsurance"]) * broker.CONFIRMERS_FEE_PERCENTAGE()) / 100
        assert False

    def test_confirm_erroneous_result(self):
        requestor = Requestor(ClientFactory.getInstance())
        requestor.togglePostProcessing()
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker, populateBuffers=False)
        executor2 = Executor(Accounts.getFromIndex(1), broker, populateBuffers=False)
        executor3 = Executor(Accounts.getFromIndex(2), broker, populateBuffers=False)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        request = broker.requests(reqID).dict()
        executor1._acceptRequest(reqID)
        result = executor1._computeResult(reqID)
        alteredResult = HexString((int.from_bytes(result, "big") + 1), "bytes32")
        executor1._submitResult(reqID, alteredResult)
        executor2._confirmResult(reqID)
        requestorOriginalBalance = requestor.client.balance()
        executor1OriginalBalance = executor1.account.balance()
        executor2OriginalBalance = executor2.account.balance()
        executor3OriginalBalance = executor3.account.balance()
        tx = executor3._challengeSubmission(reqID)
        assert requestor.client.balance() == requestorOriginalBalance + 2 * (request["payment"] * broker.CONFIRMERS_FEE_PERCENTAGE()) / 100
        assert executor1.account.balance() == executor1OriginalBalance
        assert executor2.account.balance() == executor2OriginalBalance
        assert executor3.account.balance() == executor3OriginalBalance + (request["payment"] + request["challengeInsurance"]) + (request["challengeInsurance"] * broker.CONFIRMERS_FEE_PERCENTAGE()) / 100 - (tx.gas_used * tx.gas_price)