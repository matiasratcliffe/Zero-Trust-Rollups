// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./BaseClient.sol";


contract ClientImplementation is BaseClient {

    constructor(address brokerAddress) BaseClient(brokerAddress) {}

    function clientLogic(bytes calldata inputData) external override pure returns (bytes memory) {
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
        return abi.encode(input.counter + 7);
    }

    struct ThreeInput {uint counter;}
    function functionThree(bytes memory data) private pure returns (bytes memory) {
        ThreeInput memory input = abi.decode(data, (ThreeInput));
        return abi.encode(input.counter + 4);
    }

    function processResult(bytes calldata result) external onlyBroker override {
        require(address(this).balance >= 1000 gwei, "Insufficient funds");
        uint functionToRun;
        uint counter = abi.decode(result, (uint));
        if (counter < 100) {
            if (counter % 10 == 0) {
                if ((counter/10) % 2 == 0) {
                    functionToRun = 2;
                } else {
                    functionToRun = 3;
                }
            } else {
                functionToRun = 1;
            }
        }
        ClientInput memory data = ClientInput({
            functionToRun: functionToRun,
            data: abi.encode(counter)
        });
        uint requestID = brokerContract.submitRequest{value: 1000 gwei}(abi.encode(data), 200000 wei, 1000 gwei, 1 minutes);
        emit requestSubmitted(requestID);
    }
}