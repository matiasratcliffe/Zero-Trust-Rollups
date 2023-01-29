// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./BaseClient.sol";

contract ClientImplementation is BaseClient {

    constructor(address brokerAddress) BaseClient(brokerAddress) {}

    function clientLogic(bytes calldata inputData) public override pure returns (bytes memory) {
        bytes memory output = "";
        ClientInput memory input = abi.decode(inputData, (ClientInput));
        if (input.functionToRun == 1) { output = functionOne(input.data); }
        else if (input.functionToRun == 2) { output = functionTwo(input.data); }
        else if (input.functionToRun == 3) { output = functionThree(input.data); }
        return output;
    }

    struct OneInput {uint counter;}
    function functionOne(bytes memory data) private pure returns (bytes memory) {
        OneInput memory input = abi.decode(data, (OneInput));
        return abi.encode(input.counter * 10);
    }

    struct TwoInput {uint counter;}
    function functionTwo(bytes memory data) private pure returns (bytes memory) {
        TwoInput memory input = abi.decode(data, (TwoInput));
        return abi.encode(input.counter / 10);
    }

    struct ThreeInput {uint counter;}
    function functionThree(bytes memory data) private pure returns (bytes memory) {
        ThreeInput memory input = abi.decode(data, (ThreeInput));
        return abi.encode(input.counter + 10);
    }

    function processResult(bytes calldata result) external onlyBroker override {
        //TODO hacer llamado a api, y logica interna simple para armar otro request
    }

}