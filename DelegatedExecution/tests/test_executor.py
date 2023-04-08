from scripts.classes.utils.contractProvider import BrokerFactory, ClientFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
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
        executor = Executor(Accounts.getAccount(), broker)
        assert int(broker.requests(reqID)[7][0], 16) == 0
        executor._acceptRequest(reqID)
        time.sleep(2)
        assert broker.requests(reqID)[7][0] == executor.account

    def test_accept_cancelled_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker)
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        requestor.cancelRequest(reqID)
        assert broker.requests(reqID)[9] == True
        with pytest.raises(Exception, match="The request was cancelled"):
            executor._acceptRequest(reqID)

    def test_accept_accepted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker)
        assert int(broker.requests(reqID)[7][0], 16) == 0
        executor._acceptRequest(reqID)
        with pytest.raises(Exception, match="Someone already accepted the request"):
            executor._acceptRequest(reqID)        

    def test_accept_request_wrong_insurance(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
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
        executor = Executor(Accounts.getAccount(), broker)
        executor._acceptRequest(reqID)
        time.sleep(2)
        assert broker.requests(reqID)[7][0] == executor.account
        executor._cancelAcceptance(reqID)
        time.sleep(2)
        assert int(broker.requests(reqID)[7][0], 16) == 0
    
    def test_cancel_acceptance_on_non_existing_request(self):
        executor = Executor(Accounts.getAccount(), BrokerFactory.getInstance(), populateBuffers=False)
        with pytest.raises(Exception):
            executor._cancelAcceptance(executor.broker.requestCount())

    def test_cancel_acceptance_on_unaccepted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker)
        with pytest.raises(Exception, match="There is no acceptance in place for the provided requestID"):
            executor._cancelAcceptance(reqID)

    def test_cancel_acceptance_on_submitted_request(self):
        pass

    def test_cancel_foreign_acceptance(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor1 = Executor(Accounts.getFromIndex(0), broker)
        executor2 = Executor(Accounts.getFromIndex(1), broker)
        executor1._acceptRequest(reqID)
        time.sleep(2)
        assert broker.requests(reqID)[7][0] == executor1.account
        with pytest.raises(Exception, match="You cant cancel an acceptance that does not belong to you"):
            executor2._cancelAcceptance(reqID)

    def test_submit_result(self):
        pass

    def test_submit_result_for_unaccepted_request(self):
        pass
    
    def test_submit_result_for_already_submitted_request(self):
        pass

    def test_submit_result_for_foreign_acceptance(self):
        pass

    def test_challenge_submission(self):
        pass

    def test_challenge_unsibmitted_request(self):
        pass

    def test_challenge_solidified_submission(self):
        pass

    def test_claim_payment(self):
        #TODO test solidified too in here
        pass

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

    # Test Transferable TODO??? worth it???