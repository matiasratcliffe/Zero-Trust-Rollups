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
        uint minTimestamp;
    }

    struct Result {
        uint fragmentIndex;
        uint timestampRestriction;
        uint passcode;
    }

    event keyFullyMined();

    string public encryptedDataRefference;
    KeyFragment[] public keyFragments;
    bytes32 public finalKey;

    uint public rewardPerFragment;
    uint public postProcessingGas;
    uint public minTimeFramePerFragment;
    bool public postProcessingEnabled;
    
    constructor(address brokerAddress, string memory _encryptedDataRefference, bytes32 firstLocalHash, bytes32[] memory globalHashes, uint _minTimeFramePerFragment) BaseClient(brokerAddress) payable {
        postProcessingGas = 400000;  // calculate postprocgas //// con 300000 funciona, con 200000 no
        postProcessingEnabled = true;
        rewardPerFragment = msg.value / globalHashes.length; //aca tener en cuenta el postprocgas
        encryptedDataRefference = _encryptedDataRefference;
        minTimeFramePerFragment = _minTimeFramePerFragment;
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
            localHash: firstLocalHash,
            minTimestamp: block.timestamp
        });
        _submitRequest(rewardPerFragment, abi.encode(input), postProcessingGas);
    }

    function checkResult(bytes calldata inputData, bytes calldata resultData) external override view returns (bool) {
        Input memory input = abi.decode(inputData, (Input));
        Result memory result = abi.decode(resultData, (Result));
        return (input.minTimestamp == result.timestampRestriction) && (block.timestamp >= result.timestampRestriction) && (input.fragmentIndex == result.fragmentIndex) && (keccak256(abi.encode(result.passcode, input.localHash)) == input.globalHash);
    }

    function processResult(bytes calldata resultData) public override onlyClient { // decidir si quiero mantener el parametro de post processing gas, o si lo dejo limitless a criterio del ejecutor. LO MANTENGO POR QUE ESTA SETEADO EL LIMITE DESDE BASE CLIENT FUERA DEL CONTROL DE CLIENTES MALICIOSOS
        //La hago public y only client en vez de internal porque necesito el cambio de msg.sender y necesito limitar el gas
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
                    localHash: keyFragments[result.fragmentIndex + 1].localHash,
                    minTimestamp: result.timestampRestriction + minTimeFramePerFragment
                });
                _submitRequest(rewardPerFragment, abi.encode(input), postProcessingGas);
            }
        }
    }

    function togglePostProcessing() external onlyOwner returns (bool) {
        postProcessingEnabled = postProcessingEnabled ? false : true;
        return postProcessingEnabled;
    }

    function getInputDataStructure() external override pure returns (string memory) {
        return "{uint fragmentIndex; bytes32 globalHash; bytes32 localHash; uint minTimestamp;}";
    }
    
    function getResultDataStructure() external override pure returns (string memory) {
        return "{uint fragmentIndex; uint timestampRestriction; uint passcode;}";
    }

}