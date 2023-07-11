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
    // TODO FLOOOOOOOOOOOOOOOOOORRRRRR DE VULNERABILIDADDDD, CUALQUIER POST PROCESS PUEDE LLAMAR A CUALQUIER ONLYBROKER DE CUALQUIER OOOTRO CONTRATO, Y AHORA TAMBIEN A LOS SUBMITS, QUIZAS SE SOLUCIONA HACIENDO TODAS LAS INTERACCIONES A TRAVES DE EL CONTRATO CLIENTE? Otro limite es el postprocess? pero no, porque el post process lo pone el atacante en este caso. Hay alguna manera de contar la cantidad de internal calls?
    modifier onlyOwnerOrBroker() {
        require(msg.sender == address(brokerContract) || isOwner(), "Function accessible only by the owner or broker");
        _;
    }

    constructor(address brokerAddress) Ownable() {
        brokerContract = ExecutionBroker(brokerAddress);
    }

    function checkResult(bytes calldata inputData, bytes calldata resultData) external virtual view returns (bool);
    function getInputDataStructure() external virtual pure returns (string memory);
    function getResultDataStructure() external virtual returns (string memory);
    function processResult(bytes calldata resultData) external virtual onlyBroker {}

    function submitRequest(uint payment, bytes memory input, uint postProcessingGas) public onlyOwnerOrBroker payable returns (uint) {
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