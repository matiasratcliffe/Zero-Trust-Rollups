// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./APIProvider.sol";
import "./BaseClient.sol";


struct Input {
    string apiIdentifier;
}

struct APIResponse {
    bytes message;
    bytes signature;
}

contract APIConsumer is BaseClient {
    
    APIProvider public provider;
    
    //web3.personal.sign(hash, web3.eth.defaultAccount, console.log)
    constructor(address brokerAddress, address apiProviderAddress) BaseClient(brokerAddress) {
        provider = APIProvider(apiProviderAddress);
    }

    function checkResult(bytes calldata inputData, bytes calldata resultData) external override view returns (bool) {
        Input memory input = abi.decode(inputData, (Input));
        APIResponse memory apiResponse = abi.decode(resultData, (APIResponse));
        return _verifySignature(apiResponse, provider.getAddress(input.apiIdentifier));
    }
    
    function getInputDataStructure() external override pure returns (string memory) {
        return "{string apiIdentifier;}";
    }

    function _verifySignature(APIResponse memory apiResponse, address signer) private pure returns (bool) {
        bytes32 prefixedHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", keccak256(apiResponse.message)));
        (bytes32 r, bytes32 s, uint8 v) = _splitSignature(apiResponse.signature);
        return (ecrecover(prefixedHash, v, r, s) == signer);
    }

    function _splitSignature(bytes memory signature) private pure returns (bytes32 r, bytes32 s, uint8 v) {
        require(signature.length == 65, "invalid signature length");
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
    }

}