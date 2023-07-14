// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./ExecutionBroker.sol";
import "./Ownable.sol";


abstract contract BaseClient is Ownable {

    ExecutionBroker public brokerContract;
    mapping(uint => bool) activeRequestIDs;

    event requestSubmitted(uint requestID);
    event resultPostProcessed(uint requestID, bool success);

    modifier onlyClient() {
        require(msg.sender == address(this), "Function accessible only by the contract itself");
        _;
    }

    constructor(address brokerAddress) Ownable() {
        brokerContract = ExecutionBroker(brokerAddress);
    }

    function checkResult(bytes calldata inputData, bytes calldata resultData) external virtual view returns (bool);
    function getInputDataStructure() external virtual pure returns (string memory);
    function getResultDataStructure() external virtual returns (string memory);
    function processResult(bytes calldata resultData) public virtual onlyClient {}

    function submitRequest(uint payment, bytes memory input, uint postProcessingGas) public onlyOwner payable returns (uint) {
        return _submitRequest(payment, input, postProcessingGas);
    }

    function _submitRequest(uint payment, bytes memory input, uint postProcessingGas) internal returns (uint) {
        require(payment <= address(this).balance, "Insufficient funds");
        uint requestID = brokerContract.submitRequest{value: payment}(input, postProcessingGas);
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

    function submitResult(uint requestID, bytes calldata result) external returns (bool) {
        require(activeRequestIDs[requestID] == true, "This ID does not belong to an active request within this client");
        Request memory request = brokerContract.getRequest(requestID);
        require(request.executor != address(0x0), "You need to accept the request first");
        require(request.closed == false, "The request is already closed");
        require(request.executor == msg.sender, "Someone else has accepted the Request");
        
        bool success = brokerContract.submitResult(requestID, result);
        if (success) {
            activeRequestIDs[requestID] = false;
            bytes memory data = abi.encodeWithSelector(request.client.processResult.selector, result);
            (bool callSuccess, ) = address(this).call{gas: request.postProcessingGas}(data);  // la hago low level porque quiero que la funcion siga aunque falle esto. podria usar un try catch pero paja
            emit resultPostProcessed(requestID, callSuccess);
        }
        return success;
    }

}