// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./ExecutionBroker.sol";
import "./Ownable.sol";


abstract contract BaseClient is Ownable {

    ExecutionBroker public brokerContract;

    event requestSubmitted(uint requestID);

    modifier onlyBroker() {
        require(msg.sender == address(brokerContract), "Can only be called by the registered broker contract");
        _;
    }

    constructor(address brokerAddress) Ownable() {
        brokerContract = ExecutionBroker(brokerAddress);
    }

    function checkResult(bytes calldata inputData, bytes calldata resultData) external virtual view returns (bool);
    function getInputDataStructure() external virtual pure returns (string memory);
    function processResult(bytes calldata resultData) external virtual onlyBroker {}

    function submitRequest(uint payment, bytes memory input, uint postProcessingGas) public onlyOwner payable returns (uint) {
        require(payment <= msg.value + address(this).balance, "Insufficient funds");
        uint requestID = brokerContract.submitRequest{value: payment}(input, postProcessingGas);
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