// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./Ownable.sol";


contract APIProvider is Ownable {

    mapping(string => address) public RegisteredAPIs;

    constructor () Ownable() {}

    function setAPIAddress(string calldata apiIdentifier, address apiAddress) public onlyOwner {
        RegisteredAPIs[apiIdentifier] = apiAddress;
    }

    function getAddress(string calldata apiIdentifier) public view returns (address) {
        require(RegisteredAPIs[apiIdentifier] != address(0x0), "This identifier has not been registered");
        return RegisteredAPIs[apiIdentifier];
    }

}