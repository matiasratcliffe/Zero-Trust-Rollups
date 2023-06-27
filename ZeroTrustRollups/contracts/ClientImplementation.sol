// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./BaseClient.sol";

//TODO BORRAR ESTE ARCHIVOOOO
contract ClientImplementation is BaseClient {

    constructor(address brokerAddress) BaseClient(brokerAddress) {}

    struct Input {
        uint dummy;
    }

    struct Result {
        uint dummy;
    }

    function getInputDataStructure() external override pure returns (string memory) {

    }

    function getResultDataStructure() external override pure returns (string memory) {

    }

    function checkResult(bytes calldata inputData, bytes calldata resultData) external override pure returns (bool) {
        Input memory input = abi.decode(inputData, (Input));
        Result memory result = abi.decode(resultData, (Result));
        return true;
    }

    function processResult(bytes calldata result) external override onlyBroker {

    }

}