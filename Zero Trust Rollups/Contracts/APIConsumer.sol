// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./APIProvider.sol";

contract APIConsumer {
    // TODO esto es un ejemplo de ZT rollup, o ZT Oracle
    APIProvider public provider;
    //web3.personal.sign(hash, web3.eth.defaultAccount, console.log)
    constructor(address apiProviderAddress) {
        provider = APIProvider(apiProviderAddress);
    }

    function verifySignature(
        bytes32 signedHash, bytes calldata signature, address signer
    ) public pure returns (bool) {
        (bytes32 r, bytes32 s, uint8 v) = splitSignature(signature);
        return (ecrecover(signedHash, v, r, s) == signer);
    }

    function splitSignature(
        bytes memory signature
    ) public pure returns (bytes32 r, bytes32 s, uint8 v) {
        require(signature.length == 65, "invalid signature length");
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
    }

}