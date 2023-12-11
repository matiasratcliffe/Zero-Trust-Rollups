// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./BaseClient.sol";


contract DummyClient is BaseClient {

    constructor(address brokerAddress) BaseClient(brokerAddress) {}

    function clientLogic(ClientInput calldata input) external override pure returns (bytes memory) {
        return abi.encode(0);
    }

    function getInputStructure(uint functionID) external override pure returns (string memory) {
        return "{uint256 number;}";
    }
}