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
    
    modifier onlyClient() {
        require(msg.sender == address(this), "Function accessible only by the contract itself");
        _;
    }

    constructor(address brokerAddress) Ownable() {
        // aca linkear con Broker hardcoded
        brokerContract = ExecutionBroker(brokerAddress);
    }

    function clientLogic(ClientInput calldata input) external virtual pure returns (bytes memory);
    function processResult(bytes calldata result) public virtual onlyClient {}
    function getInputStructure(uint functionID) external virtual pure returns (string memory);

    function submitRequest(uint payment, ClientInput calldata input, uint postProcessingGas, uint requestedInsurance, uint claimDelay) external payable onlyOwner returns (uint) {
        return _submitRequest(payment, input, postProcessingGas, requestedInsurance, claimDelay);
    }

    function _submitRequest(uint payment, ClientInput memory input, uint postProcessingGas, uint requestedInsurance, uint claimDelay) internal returns (uint) {
        require(payment <= address(this).balance, "Insufficient funds");
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

    function challengeSubmission(uint requestID) external returns (bool) {
        Request memory request = brokerContract.getRequest(requestID);
        bool success = brokerContract.challengeSubmission(requestID);
        
        /* TODO esto lo ejecuto regardless
        bytes memory data = abi.encodeWithSelector(requests[requestID].client.processResult.selector, requests[requestID].submission.result);
        (bool callSuccess, ) = address(requests[requestID].client).call{gas: requests[requestID].postProcessingGas}(data);
        emit resultPostProcessed(requestID, callSuccess);*/
        
        return success;
    }

    function claimPayment(uint requestID) external returns (bool) {
        Request memory request = brokerContract.getRequest(requestID);
        //bool success = brokerContract.claimPayment() //TODO aca podria usar un delegate call, porque el cliente si confia en el broker pero no viceversa. O podria mandar el msg sender original como otro parametro
    }

}