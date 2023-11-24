// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;


contract OnChainPrimeFinder {

    uint[] public PRIMES;

    constructor() {
        PRIMES.push(2);
    }

    function getPrimes() public view returns (uint[] memory) {
        return PRIMES;
    }

    function getPrimesLength() public view returns (uint) {
        return PRIMES.length;
    }

    function findPrimes(uint256 limit) public returns (uint[] memory) {
        uint i;
        for (i = PRIMES[PRIMES.length - 1] | 1; i < limit; i += 2) {
            if (_isPrime(i)) {
                PRIMES.push(i);
            }
        }
        return PRIMES;
    }

    function _isPrime(uint256 number) private pure returns (bool) {
        if (number < 2 || (number % 2 == 0 && number > 2)) {
            return false;
        }
        for (uint i = 3; i < number/2; i += 2) {
            if (number % i == 0) {
                return false;
            }
        }
        return true;
    }
}