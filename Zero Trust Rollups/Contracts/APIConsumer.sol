// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./APIProvider.sol";

contract APIConsumer {
    // TODO esto es un ejemplo de ZT rollup, o ZT Oracle
    APIProvider public provider;

    constructor(address apiProviderAddress) {
        provider = APIProvider(apiProviderAddress);
    }

}