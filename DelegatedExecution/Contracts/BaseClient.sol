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
        brokerContract = ExecutionBroker(brokerAddress);
    }

    modifier onlyBroker() {
        require(msg.sender == address(brokerContract), "Can only be called by the registered broker contract");
        _;
    }

    function clientLogic(ClientInput calldata input) external virtual pure returns (bytes memory);
    function processResult(bytes calldata result) external virtual onlyBroker {}
    function getInputStructure(uint functionID) external virtual pure returns (string memory);

    function submitRequest(uint payment, ClientInput calldata input, uint postProcessingGas, uint requestedInsurance, uint claimDelay) external onlyOwner payable returns (uint) {
        require(payment <= msg.value + address(this).balance, "Insufficient funds");
        uint requestID = brokerContract.submitRequest{value: payment}(input, postProcessingGas, requestedInsurance, claimDelay);
        emit requestSubmitted(requestID);
        return requestID;
    }

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