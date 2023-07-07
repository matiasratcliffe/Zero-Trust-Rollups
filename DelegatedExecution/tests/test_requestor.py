from scripts.classes.utils.contractProvider import BrokerFactory, ClientFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from scripts.classes.requestor import Requestor
from scripts.classes.executor import Executor
from brownie.exceptions import VirtualMachineError
from eth_abi.exceptions import ValueOutOfBounds
from eth_abi import decode
from brownie import network
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
        network.event.event_watcher.reset()

    def test_creation(self):
        if network.show_active() == "development":
            account = Accounts.getAccount()
            broker = BrokerFactory.getInstance()
            client = ClientFactory.create(broker, account)
        else:
            client = ClientFactory.getInstance()
            account = Accounts.getFromKey(client.owner())
            broker = BrokerFactory.at(address=client.brokerContract())
        requestor = Requestor(client)
        assert requestor.owner.address == account.address
        assert requestor.client.address == client.address
        assert BrokerFactory.at(address=requestor.client.brokerContract()) == broker

    def test_send_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        requestor.withdrawFunds(requestor.getFunds())  # This is just in case there are funds left from another test
        ownerOriginalBalance = requestor.owner.balance()
        valueToSend = ownerOriginalBalance // 100
        assert valueToSend > 0
        transaction = requestor.sendFunds(valueToSend)
        assert requestor.getFunds() == valueToSend
        assert requestor.owner.balance() == ownerOriginalBalance - valueToSend - (transaction.gas_used * transaction.gas_price)

    def test_withdraw_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        requestor.withdrawFunds(requestor.getFunds())  # This is just in case there are funds left from another test
        valueToSend = requestor.owner.balance() // 100
        assert valueToSend > 0
        requestor.sendFunds(valueToSend)
        ownerOriginalBalance = requestor.owner.balance()
        transaction = requestor.withdrawFunds(valueToSend)
        assert requestor.owner.balance() == ownerOriginalBalance + valueToSend - (transaction.gas_used * transaction.gas_price)

    def test_oversend_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        with pytest.raises(ValueError):
            requestor.sendFunds(requestor.owner.balance() + 1)

    def test_overwithdraw_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        with pytest.raises(Exception, match="Insufficient funds"):
            requestor.withdrawFunds(requestor.getFunds() + 1)
    
    def test_encode_input(self):
        requestor = Requestor(ClientFactory.getInstance())
        function = 1
        data = [10]
        encoded_tuple = requestor._encodeInput(function, data)
        assert encoded_tuple[0] == function
        assert (tuple(data),) == decode(requestor._getFunctionTypes(function), encoded_tuple[1])
    
    def test_encode_input_non_existing_function(self):
        requestor = Requestor(ClientFactory.getInstance())
        with pytest.raises(Exception, match="Invalid function ID"):
            requestor._encodeInput(4, [10])

    def test_create_request_with_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        requestor.sendFunds(1e+18)
        functionToRun = 1
        dataArray = [10]
        payment = 1e+16
        postProcessingGas = 2e13
        requestedInsurance = 1e+17
        claimDelay = 100
        reqID = requestor.createRequest(functionToRun, dataArray, payment, postProcessingGas, requestedInsurance, claimDelay)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        request = dict(broker.requests(reqID))
        assert request["id"] == reqID
        assert dict(request["input"])["functionToRun"] == functionToRun
        assert decode(requestor._getFunctionTypes(functionToRun), dict(request["input"])["data"]) == (tuple(dataArray),)
        assert request["payment"] == payment
        assert request["postProcessingGas"] == postProcessingGas
        assert request["challengeInsurance"] == requestedInsurance
        assert request["claimDelay"] == claimDelay
        assert request["client"] == requestor.client.address
        assert int(request["acceptance"][0], 16) == 0
        assert int(dict(request["submission"])["issuer"], 16) == 0
        assert request["cancelled"] == False
    
    def test_get_non_existing_request(self):
        broker = BrokerFactory.getInstance()
        with pytest.raises(VirtualMachineError):
            broker.requests(broker.requestCount())

    def test_create_request_and_fund(self):
        requestor = Requestor(ClientFactory.getInstance())
        requestor.withdrawFunds(requestor.getFunds())  # This is just in case there are funds left from another test
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e+18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        request = dict(broker.requests(reqID))
        assert request["client"] == requestor.client.address

    def test_create_request_without_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        requestor.withdrawFunds(requestor.getFunds())  # This is just in case there are funds left from another test
        with pytest.raises(Exception, match="Insufficient funds"):
            requestor.createRequest(functionToRun=1, dataArray=[10])

    def test_create_request_with_excess_post_processing_gas(self):
        requestor = Requestor(ClientFactory.getInstance())
        with pytest.raises(Exception, match="The post processing gas cannot takeup all of the supplied ether"):
            requestor.createRequest(
                functionToRun=1,
                dataArray=[10],
                payment=1e+17,
                postProcessingGas=1e+17,
                funds=1e+18,
                gasPrice=1
            )

    def test_cancel_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e16)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        assert dict(broker.requests(reqID))["cancelled"] == False
        requestor.cancelRequest(reqID)
        time.sleep(2)
        assert dict(broker.requests(reqID))["cancelled"] == True

    def test_cancel_non_existing_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        with pytest.raises(Exception, match="Index out of range"):
            requestor.cancelRequest(broker.requestCount())

    def test_cancel_foreign_request(self):
        assert Accounts.count() >= 2
        account1 = Accounts.getFromIndex(0)
        account2 = Accounts.getFromIndex(1)
        broker = BrokerFactory.getInstance()
        requestor1 = Requestor(ClientFactory.create(owner=account1, broker=broker))
        requestor2 = Requestor(ClientFactory.create(owner=account2, broker=broker))
        reqID = requestor1.createRequest(functionToRun=1, dataArray=[10], funds=1e16)
        with pytest.raises(Exception, match="You cant cancel a request that was not made by you"):
            requestor2.cancelRequest(reqID)

    def test_cancel_cancelled_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e16)
        requestor.cancelRequest(reqID)
        with pytest.raises(Exception, match="The request was already cancelled"):
            requestor.cancelRequest(reqID)

    def test_cancel_accepted_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e16)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        assert dict(broker.requests(reqID))["cancelled"] == False
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        time.sleep(2)
        assert dict(broker.requests(reqID))["acceptance"][0] == executor.account
        with pytest.raises(Exception, match="You cant cancel an accepted request"):
            requestor.cancelRequest(reqID)

    def test_cancel_accepted_then_unnacept_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1)
        time.sleep(2)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        assert dict(broker.requests(reqID))["cancelled"] == False
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        executor._acceptRequest(reqID)
        time.sleep(3)
        assert dict(broker.requests(reqID))["acceptance"][0] == executor.account
        executor._cancelAcceptance(reqID)
        time.sleep(4)
        assert int(dict(broker.requests(reqID))["acceptance"][0], 16) == 0
        requestor.cancelRequest(reqID)
        time.sleep(3)
        assert dict(broker.requests(reqID))["cancelled"] == True

    def test_publicize_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e16)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        executor = Executor(Accounts.getAccount(), broker, populateBuffers=False)
        assert reqID not in executor.unacceptedRequests
        requestor.publicizeRequest(reqID)
        time.sleep(4)
        assert reqID in executor.unacceptedRequests

    # Low level tests

    def test_withdraw_funds_only_owner(self):
        assert Accounts.count() >= 2
        account1 = Accounts.getFromIndex(0)
        account2 = Accounts.getFromIndex(1)
        broker = BrokerFactory.getInstance()
        client = ClientFactory.create(owner=account1, broker=broker)
        with pytest.raises(Exception, match="Function accessible only by the owner"):
            client.withdrawFunds(client.balance(), {'from': account2})

    def test_cancel_request_only_owner(self):
        assert Accounts.count() >= 2
        account1 = Accounts.getFromIndex(0)
        account2 = Accounts.getFromIndex(1)
        broker = BrokerFactory.getInstance()
        requestor = Requestor(ClientFactory.create(owner=account1, broker=broker))
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e16)
        with pytest.raises(Exception, match="Function accessible only by the owner"):
            requestor.client.cancelRequest(reqID, {'from': account2})

    def test_submit_request_only_owner(self):
        assert Accounts.count() >= 2
        account1 = Accounts.getFromIndex(0)
        account2 = Accounts.getFromIndex(1)
        broker = BrokerFactory.getInstance()
        client = ClientFactory.create(owner=account1, broker=broker)
        with pytest.raises(Exception, match="Function accessible only by the owner"):
            client.submitRequest(
                1e+16,
                (0, 0),  # This would yield an error on the broker but the request should never make it out of the client contract
                2e13,
                1e+17,
                100,
                {'from': account2, 'value': 1}
            )

    def test_process_result_only_broker(self):
        client = ClientFactory.getInstance()
        account = Accounts.getFromKey(client.owner())
        with pytest.raises(Exception, match="Can only be called by the registered broker contract"):
            client.processResult(
                0,  # This would yield an error but the call should never make it past the modifiers
                {'from': account}
            )