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
    mapping(uint => bool) activeRequestIDs;

    event requestSubmitted(uint requestID);
    event resultPostProcessed(uint requestID, bool success);

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
        activeRequestIDs[requestID] = true;
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
        require(activeRequestIDs[requestID] == true, "This ID does not belong to an active request within this client");
        Request memory request = brokerContract.getRequest(requestID);
        require(request.submission.issuer != address(0x0), "There are no submissions for the challenged request");
        require(!request.submission.solidified, "The challenged submission has already solidified");
        
        bool success = brokerContract.challengeSubmission(requestID, msg.sender);
        
        bytes memory data = abi.encodeWithSelector(request.client.processResult.selector, request.submission.result);
        (bool callSuccess, ) = address(request.client).call{gas: request.postProcessingGas}(data);
        emit resultPostProcessed(requestID, callSuccess);
        
        return success;
    }

    function claimPayment(uint requestID) external returns (bool) {
        require(activeRequestIDs[requestID] == true, "This ID does not belong to an active request within this client");
        Request memory request = brokerContract.getRequest(requestID);
        require(request.submission.issuer != address(0x0), "There are no submissions for the provided request");
        require(request.submission.issuer == msg.sender, "This payment does not belong to you");
        require(!request.submission.solidified, "The provided request has already solidified");

        bool success = brokerContract.claimPayment(requestID);
        activeRequestIDs[requestID] = false;
        
        bytes memory data = abi.encodeWithSelector(request.client.processResult.selector, request.submission.result);
        (bool callSuccess, ) = address(request.client).call{gas: request.postProcessingGas}(data);
        emit resultPostProcessed(requestID, callSuccess);

        return success;
    }

}
//TODO poner en la tesis que esta correccion de vulnerabilidad es por si un cliente hace un delegate call al postproc de otro cliente con la identidad del broker