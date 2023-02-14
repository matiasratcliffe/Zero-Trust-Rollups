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


class TestRequestor:
    def setup_method(self, method):
        Logger.logIndentation=0

    def teardown_method(self, method):
        pass

    def test_creation(self):
        if network.show_active() == "development":
            account = Accounts.getAccount()
            broker = BrokerFactory.getInstance()
            client = ClientFactory.create(account, broker)
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
        valueToSend = ownerOriginalBalance // 10
        assert valueToSend > 0
        requestor.sendFunds(valueToSend)
        assert requestor.getFunds() == valueToSend
        assert requestor.owner.balance() == ownerOriginalBalance - valueToSend
        #TODO tener en cuenta el gas

    def test_withdraw_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        requestor.withdrawFunds(requestor.getFunds())  # This is just in case there are funds left from another test
        valueToSend = requestor.owner.balance() // 10
        assert valueToSend > 0
        requestor.sendFunds(valueToSend)
        ownerOriginalBalance = requestor.owner.balance()
        requestor.withdrawFunds(valueToSend)
        assert requestor.owner.balance() == ownerOriginalBalance + valueToSend
        #TODO tener en cuenta el gas

    def test_oversend_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        with pytest.raises(ValueError):
            requestor.sendFunds(requestor.owner.balance() + 1)

    def test_overwithdraw_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        with pytest.raises(VirtualMachineError, match="revert: Insufficient funds"):
            requestor.withdrawFunds(requestor.getFunds() + 1)
    
    def test_encode_input(self):
        requestor = Requestor(ClientFactory.getInstance())
        function = 1
        data = [10]
        encoded_tuple = requestor._encodeInput(function, data)
        assert encoded_tuple[0] == function
        assert tuple(data) == decode(requestor._getFunctionTypes(function), encoded_tuple[1])
    
    def test_encode_input_non_existing_function(self):
        requestor = Requestor(ClientFactory.getInstance())
        with pytest.raises(ValueOutOfBounds):
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
        request = broker.requests(reqID)
        assert request[0][0] == functionToRun
        assert decode(requestor._getFunctionTypes(functionToRun), request[0][1]) == tuple(dataArray)
        assert request[1] == payment
        assert request[2] == postProcessingGas
        assert request[3] == requestedInsurance
        assert request[4] == claimDelay
        assert request[5] == requestor.client.address
        assert int(request[6][0], 16) == 0
        assert int(request[7][0], 16) == 0
        assert request[8] == False
    
    def test_get_non_existing_request(self):
        broker = BrokerFactory.getInstance()
        reqID = 0
        with pytest.raises(VirtualMachineError):
            while True:
                broker.requests(reqID)
                reqID += 1

    def test_create_request_and_fund(self):
        requestor = Requestor(ClientFactory.getInstance())
        requestor.withdrawFunds(requestor.getFunds())  # This is just in case there are funds left from another test
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e+18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        request = broker.requests(reqID)
        assert request[5] == requestor.client.address

    def test_create_request_without_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        requestor.withdrawFunds(requestor.getFunds())  # This is just in case there are funds left from another test
        with pytest.raises(VirtualMachineError, match="revert: Insufficient funds"):
            requestor.createRequest(functionToRun=1, dataArray=[10])

    def test_create_request_with_excess_post_processing_gas(self):
        requestor = Requestor(ClientFactory.getInstance())
        with pytest.raises(VirtualMachineError, match="revert: The post processing gas cannot takeup all of the supplied ether"):
            requestor.createRequest(
                functionToRun=1,
                dataArray=[10],
                payment=1e+17,
                postProcessingGas=1e+17,
                funds=1e+18
            )

    def test_cancel_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        request = broker.requests(reqID)
        assert request[8] == False
        requestor.cancelRequest(reqID)
        request = broker.requests(reqID)
        assert request[8] == True

    def test_cancel_non_existing_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        reqID = 0
        try:
            while True:
                broker.requests(reqID)
                reqID += 1
        except VirtualMachineError:
            pass
        with pytest.raises(VirtualMachineError, match="revert: Index out of range"):
            requestor.cancelRequest(reqID)

    def test_cancel_cancelled_request(self):
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        requestor.cancelRequest(reqID)
        with pytest.raises(VirtualMachineError, match="revert: The request was already cancelled"):
            requestor.cancelRequest(reqID)

    def test_cancel_accepted_request(self):
        Logger.log("#########################################################"*3, color=Logger.colors.RED, raw=True)
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        request = broker.requests(reqID)
        assert request[8] == False
        executor = Executor(Accounts.getAccount(), broker, True)
        executor._acceptRequest(reqID)
        assert broker.requests(reqID)[6][0] == executor.account
        with pytest.raises(VirtualMachineError, match="revert: You cant cancel an accepted request"):
            requestor.cancelRequest(reqID)

    def test_cancel_accepted_then_unnacepted_request(self):
        Logger.log("#########################################################"*3, color=Logger.colors.RED, raw=True)
        requestor = Requestor(ClientFactory.getInstance())
        reqID = requestor.createRequest(functionToRun=1, dataArray=[10], funds=1e18)
        broker = BrokerFactory.at(address=requestor.client.brokerContract())
        request = broker.requests(reqID)
        assert request[8] == False
        executor = Executor(Accounts.getAccount(), broker, True)
        executor._acceptRequest(reqID)
        assert broker.requests(reqID)[6][0] == executor.account
        executor._cancelAcceptance(reqID)
        assert int(broker.requests(reqID)[6][0], 16) == 0
        requestor.cancelRequest(reqID)
        request = broker.requests(reqID)
        assert request[8] == True

    # Low level tests

    def test_cancel_foreign_request(self):
        pass

    def test_withdraw_funds_foreign_account(self):
        pass

    def test_create_request_foreign_account(self):
        pass