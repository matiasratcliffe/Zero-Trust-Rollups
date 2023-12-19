// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./BaseClient.sol";


contract TS3000 is BaseClient {
    struct Input {
        uint number;
    }

    struct Result {
        uint number;
    }

    constructor(address brokerAddress) BaseClient(brokerAddress) payable {
        Input memory input = Input({
            number: 0
        });
        _submitRequest(0, abi.encode(input), 100000);
    }

    function checkResult(bytes calldata inputData, bytes calldata resultData) external override view returns (bool) {
        Input memory input = abi.decode(inputData, (Input));
        Result memory result = abi.decode(resultData, (Result));
        return true;
    }

    function getInputDataStructure() external override pure returns (string memory) {
        return "{uint number;}";
    }
    
    function getResultDataStructure() external override pure returns (string memory) {
        return "{uint number;}";
    }
}
