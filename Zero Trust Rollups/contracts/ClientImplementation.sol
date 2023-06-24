// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./BaseClient.sol";


contract ClientImplementation is BaseClient {

    constructor(address brokerAddress) BaseClient(brokerAddress) {}

    function checkResult(bytes calldata input, bytes calldata result) external override pure returns (bool) {
        return true;
    }
}