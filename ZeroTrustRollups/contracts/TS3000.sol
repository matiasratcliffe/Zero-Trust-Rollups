// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./BaseClient.sol";


contract TS3000 is BaseClient {

    struct KeyFragment {
        bytes32 globalHash;
        bytes32 localHash;
        uint passcode;
    }

    struct Input {
        uint fragmentIndex;
        bytes32 globalHash;
        bytes32 localHash;
    }

    struct Result {
        uint fragmentIndex;
        uint passcode;
    }

    event keyFullyMined();

    string public encryptedDataRefference;
    KeyFragment[] public keyFragments;
    bytes32 public finalKey;
    
    uint public rewardPerFragment;
    uint public postProcessingGas;
    bool public postProcessingEnabled;
    
    constructor(address brokerAddress, string memory _encryptedDataRefference, bytes32 firstLocalHash, bytes32[] memory globalHashes) BaseClient(brokerAddress) payable {
        postProcessingGas = 10;  //TODO calculate postprocgas
        postProcessingEnabled = true;
        rewardPerFragment = msg.value / globalHashes.length; //TODO aca tener en cuenta el postprocgas
        encryptedDataRefference = _encryptedDataRefference;
        for (uint i = 0; i < globalHashes.length; i++) {
            KeyFragment memory fragment; 
            fragment.globalHash = globalHashes[i];
            if (i == 0) {
                fragment.localHash = firstLocalHash;
            }
            keyFragments.push(fragment);
        }
        Input memory input = Input({
            fragmentIndex: 0,
            globalHash: globalHashes[0],
            localHash: firstLocalHash
        });
        submitRequest(rewardPerFragment, abi.encode(input), postProcessingGas);
    }

    function checkResult(bytes calldata inputData, bytes calldata resultData) external override pure returns (bool) {
        Input memory input = abi.decode(inputData, (Input));
        Result memory result = abi.decode(resultData, (Result));
        return (input.fragmentIndex == result.fragmentIndex) && (keccak256(abi.encode(result.passcode, input.localHash)) == input.globalHash);
    }

    function processResult(bytes calldata resultData) external override onlyBroker {
        Result memory result = abi.decode(resultData, (Result));
        keyFragments[result.fragmentIndex].passcode = result.passcode;
        if (result.fragmentIndex == keyFragments.length - 1) {
            finalKey = keccak256(abi.encode(result.passcode));
            emit keyFullyMined();
        } else {
            keyFragments[result.fragmentIndex + 1].localHash = keccak256(abi.encode(result.passcode));
            if (postProcessingEnabled) {
                Input memory input = Input({
                    fragmentIndex: result.fragmentIndex + 1,
                    globalHash: keyFragments[result.fragmentIndex + 1].globalHash,
                    localHash: keyFragments[result.fragmentIndex + 1].localHash
                });
                submitRequest(rewardPerFragment, abi.encode(input), postProcessingGas);
            }
        }
    }

    function togglePostProcessing() external onlyOwner {
        postProcessingEnabled = postProcessingEnabled ? false : true;
    }

    function getInputDataStructure() external override pure returns (string memory) {
        return "{uint fragmentIndex; bytes32 globalHash; bytes32 localHash;}";
    }
}