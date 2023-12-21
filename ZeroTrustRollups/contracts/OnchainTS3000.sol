// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;


contract OnchainTS3000 {

    uint8 currentIndex;
    uint8 fragmentDifficulty;
    bytes32[] targetHashes;
    uint32[] public passcodes;

    constructor(bytes32[] memory _targetHashes, uint8 _fragmentDifficulty) {
        currentIndex = 0;
        fragmentDifficulty = _fragmentDifficulty;
        for (uint8 i = 0; i < _targetHashes.length; i++) {
            targetHashes.push(_targetHashes[i]);
        }
    }

    function resolveOnChain() public {
        bytes32 targetHash = targetHashes[currentIndex];
        for (uint32 passcode = 0; passcode < 10**fragmentDifficulty; passcode++) {
            if (keccak256(abi.encode(passcode)) == targetHash) {
                passcodes.push(passcode);
                currentIndex++;
                return;
            }
        }
        revert("No number of the set difficulty match the target hash for this round!");
    }

}
