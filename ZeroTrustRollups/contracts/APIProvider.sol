// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;


contract APIProvider {
    
    mapping(address => bytes) public RegisteredAPIs;

    function registerAPI() public {
        require(RegisteredAPIs[msg.sender]);
    }

}