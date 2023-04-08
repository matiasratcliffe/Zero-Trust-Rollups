from scripts.classes.utils.contractProvider import BrokerFactory, ClientFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from scripts.classes.requestor import Requestor
from scripts.classes.executor import Executor
from brownie import network


class TestExecutor:
    def setup_method(self, method):
        Logger.indentationLevel=0

    def teardown_method(self, method):
        pass

    # TODO tests de ExecutionBroker y de executor (comportamiento de los buffers y eventos), isrequestopen?
    # TODO tests de transferable

    def test_accept_request(self, requestID):
        pass

    def test_cancel_acceptance(self, requestID):
        pass

    def test_submit_result(self, requestID, result):
        pass
    
    def test_challenge_submission(self, requestID):
        pass

    def solverLoopRound(self):
        pass

    def challengerLoopRound(self):
        pass
