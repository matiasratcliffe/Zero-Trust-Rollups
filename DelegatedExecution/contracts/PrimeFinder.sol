// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./BaseClient.sol";


contract PrimeFinder is BaseClient {

    uint[] public PRIMES;

    constructor(address brokerAddress) BaseClient(brokerAddress) {
        PRIMES.push(2);
    }

    function getPrimes() public view returns (uint[] memory) {
        return PRIMES;
    }

    function getPrimesLength() public view returns (uint) {
        return PRIMES.length;
    }

    function clientLogic(ClientInput calldata input) external override pure returns (bytes memory) {
        bytes memory output = "";
        if (input.functionToRun == 1) { output = _getPrime(input.data); }
        else if (input.functionToRun == 2) {output = _isPrime(input.data); }
        return output;
    }

    struct OneInput {uint startPoint;}
    function _getPrime(bytes memory data) private pure returns (bytes memory) {
        uint i;
        uint batchSize = 10;
        OneInput memory input = abi.decode(data, (OneInput));
        for (i = input.startPoint | 1; i < input.startPoint + batchSize; i += 2) {
            if (abi.decode(_isPrime(abi.encode(TwoInput({number: i}))), (bool))) {
                return abi.encode(i);
            }
        }
        return abi.encode(i);
    }

    struct TwoInput {uint number;}
    function _isPrime(bytes memory data) private pure returns (bytes memory) {
        TwoInput memory input = abi.decode(data, (TwoInput));
        if (input.number < 2 || (input.number % 2 == 0 && input.number > 2)) {
            return abi.encode(false);
        }
        for (uint i = 3; i < input.number/2; i += 2) {
            if (input.number % i == 0) {
                return abi.encode(false);
            }
        }
        return abi.encode(true);
    }

    function getInputStructure(uint functionID) external override pure returns (string memory) {
        if (functionID == 1) { return "{uint startPoint;}"; }
        else if (functionID == 2) { return "{uint number;}"; }
        else { revert("Invalid function ID"); }
    }

    function processResult(bytes calldata result) external override onlyBroker {
        require(address(this).balance >= 10000 gwei, "Insufficient funds");
        uint number = abi.decode(result, (uint));
        ClientInput memory input = ClientInput({
            functionToRun: 1,
            data: abi.encode(OneInput({startPoint: number + 1}))
        });
        uint requestID = brokerContract.submitRequest{value: 10000 gwei}(input, 1000 gwei, 200000 gwei, 0 seconds);
        emit requestSubmitted(requestID);
        if (abi.decode(_isPrime(abi.encode(TwoInput({number: number}))), (bool))) {
            PRIMES.push(number);
        }
        return; //TODO ??????
        for (uint8 i = 0; i < PRIMES.length; i++) {
            if (number % PRIMES[i] == 0) {
                return;
            }
        }
        PRIMES.push(number);
    }
}