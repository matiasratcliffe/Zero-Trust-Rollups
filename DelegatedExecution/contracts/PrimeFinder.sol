// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./BaseClient.sol";


contract PrimeFinder is BaseClient {

    uint[] public PRIMES;
    bool public postProcessingEnabled = false;
    uint public batchSize = 1000;

    event automaticRequestCreationFailed();

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
        if (input.functionToRun == 1) { output = getPrime(input.data); }
        else if (input.functionToRun == 2) {output = isPrime(input.data); }
        return output;
    }

    struct OneInput {uint256 startPoint; uint256 batchSize;}
    function getPrime(bytes memory data) private pure returns (bytes memory) {
        OneInput memory input = abi.decode(data, (OneInput));
        return _getPrime(input.startPoint, input.batchSize);
    }
    function _getPrime(uint256 _startPoint, uint256 _batchSize) private pure returns (bytes memory) {
        uint256 i;
        bytes memory result;
        for (i = _startPoint | 1; i < _startPoint + _batchSize; i += 2) {
            if (_isPrime(i)) {
                result = abi.encodePacked(result, i);
            }
        }
        result = abi.encodePacked(result, i);  // Always add the last one so that post processing can know where to continue if there are no other numbers
        return result;
    }

    struct TwoInput {uint256 number;}
    function isPrime(bytes memory data) private pure returns (bytes memory) {
        TwoInput memory input = abi.decode(data, (TwoInput));
        return abi.encode(_isPrime(input.number));
    }
    function _isPrime(uint256 _number) private pure returns (bool) {
        if (_number < 2 || (_number % 2 == 0 && _number > 2)) {
            return false;
        }
        for (uint i = 3; i < _number/2; i += 2) {
            if (_number % i == 0) {
                return false;
            }
        }
        return true;
    }

    function getInputStructure(uint functionID) external override pure returns (string memory) {
        if (functionID == 1) { return "{uint256 startPoint; uint256 batchSize;}"; }
        else if (functionID == 2) { return "{uint256 number;}"; }
        else { revert("Invalid function ID"); }
    }

    function processResult(bytes memory result) public override onlyClient {
        require(address(this).balance >= 10000 gwei, "Insufficient funds");
        uint256 value;
        uint length = result.length / 32;
        for (uint i = 0; i < length; i++) {
            assembly {
                value := mload(add(result, add(32, mul(i, 32))))
            }
            if (i < length - 1 || _isPrime(value)) {
                PRIMES.push(value);
            }
        }
        if (postProcessingEnabled) {
            ClientInput memory input = ClientInput({
                functionToRun: 1,
                data: abi.encode(OneInput({startPoint: value + 1, batchSize: batchSize}))
            });
            _submitRequest(10000 gwei, input, 1000 gwei, 200000 gwei, 0 seconds);
        }
    }

    function togglePostProcessing() external onlyOwner returns (bool) {
        postProcessingEnabled = postProcessingEnabled ? false : true;
        return postProcessingEnabled;
    }
}