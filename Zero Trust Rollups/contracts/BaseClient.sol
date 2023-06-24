// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./ExecutionBroker.sol";
import "./Ownable.sol";


abstract contract BaseClient is Ownable {

    ExecutionBroker public brokerContract;

    event requestSubmitted(uint requestID);

    constructor(address brokerAddress) {
        // aca linkear con Broker hardcoded
        brokerContract = ExecutionBroker(brokerAddress);
    }

    function checkResult(bytes calldata input, bytes calldata result) external virtual pure returns (bool);
    
    function submitRequest(uint payment, bytes calldata input) external onlyOwner payable returns (uint) {
        require(payment <= msg.value + address(this).balance, "Insufficient funds");
        uint requestID = brokerContract.submitRequest{value: payment}(input);
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