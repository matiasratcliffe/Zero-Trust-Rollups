from scripts.classes.utils.contractProvider import BrokerFactory, ClientFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.requestor import Requestor
from brownie.exceptions import VirtualMachineError
from eth_abi.exceptions import ValueOutOfBounds
from eth_abi import decode
from brownie import network
import pytest


class TestRequestor:
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
        ownerOriginalBalance = requestor.owner.balance()
        valueToSend = ownerOriginalBalance // 10
        assert valueToSend > 0
        requestor.sendFunds(valueToSend)
        assert requestor.getFunds() == valueToSend
        assert requestor.owner.balance() == ownerOriginalBalance - valueToSend
        #TODO tener en cuenta el gas

    def test_withdraw_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        valueToSend = requestor.owner.balance() // 10
        assert valueToSend > 0
        requestor.sendFunds(valueToSend)
        ownerOriginalBalance = requestor.owner.balance()
        requestor.withdrawFunds(valueToSend)
        assert requestor.owner.balance() == ownerOriginalBalance + valueToSend
        #TODO tener en cuenta el gas

    def test_oversend_funds(self):
        with pytest.raises(ValueError):
            requestor = Requestor(ClientFactory.getInstance())
            requestor.sendFunds(requestor.owner.balance() + 1)

    def test_overwithdraw_funds(self):
        with pytest.raises(VirtualMachineError, match="revert: Insufficient funds"):
            requestor = Requestor(ClientFactory.getInstance())
            requestor.withdrawFunds(requestor.getFunds() + 1)
    
    def test_encode_input(self):
        requestor = Requestor(ClientFactory.getInstance())
        function = 1
        data = [10]
        encoded_tuple = requestor._encodeInput(function, data)
        assert encoded_tuple[0] == function
        assert tuple(data) == decode(requestor._getFunctionTypes(function), encoded_tuple[1])
    
    def test_encode_input_non_existing_function(self):
        with pytest.raises(ValueOutOfBounds):
            requestor = Requestor(ClientFactory.getInstance())
            requestor._encodeInput(4, [10])

    def test_create_request_with_funds(self):
        requestor = Requestor(ClientFactory.getInstance())
        functionToRun = 1
        dataArray = [10]
        payment = 1e+16
        postProcessingGas = 2e13
        requestedInsurance = 1e+18
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
    
    def test_create_request_without_funds(self):
        pass

    def test_create_request_without_funds(self):
        pass

    def test_cancel_request(self):
        pass