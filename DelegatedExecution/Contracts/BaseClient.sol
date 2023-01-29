// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./ExecutionBroker.sol";
import "./Ownable.sol";


abstract contract BaseClient is Ownable {

    struct ClientInput {
        uint functionToRun;
        bytes data;
    }

    ExecutionBroker public brokerContract;

    event requestSubmitted(uint requestID);

    constructor(address brokerAddress) {
        // aca linkear con Broker hardcoded
        brokerContract = ExecutionBroker(brokerAddress); //esto me hace un circulo de referencias?? TODO check
    }

    modifier onlyBroker() {
        require(msg.sender == address(brokerContract), "Can only be called by the registered broker contract");
        _;
    }

    function clientLogic(bytes calldata input) public virtual pure returns (bytes memory);
    function processResult(bytes calldata result) external onlyBroker {}  // no es virtual porque no es necesaria, la pueden dejar asi

    function submitRequest(uint payment, bytes calldata inputData, uint postProcessingGas, uint requestedInsurance, uint claimDelay) external onlyOwner payable returns (uint) {
        require(payment <= msg.value + address(this).balance, "Insufficient funds");
        uint requestID = brokerContract.submitRequest{value: payment}(inputData, postProcessingGas, requestedInsurance, claimDelay);
        emit requestSubmitted(requestID);
        return requestID;
    }

    // TODO ver tema cancel request y todas las posibles interacciones
    function cancelRequest(uint requestID) external onlyOwner {
        brokerContract.cancelRequest(requestID);
    }

    function sendFunds() public payable {}
    
    function withdrawFunds(uint value) public onlyOwner returns (bool) {
        require(address(this).balance >= value, "Insufficient funds");
        address payable payee = payable(msg.sender);
        (bool success, ) = payee.call{value: value}("");
        return success;
    }

}