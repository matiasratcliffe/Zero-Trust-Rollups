// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

contract Tests {

    uint public val=1;
    event issuer(address);
    function deposit() public payable {
        val = address(this).balance;
        emit issuer(msg.sender);  // ver si este tipo de llamados es delegate o no, para saber tema collector de clientes onchain
    }

    function withdraw(uint amount) public returns (bool) {
        address payable payee = payable(msg.sender);
        (bool success, ) = payee.call{value: amount}("Hola Mundo!");
        return success;
    }

    struct ClientInput {
        uint functionToRun;
        uint dos;
    }

    event print(uint);
    function printbytes() public view returns (uint) {
        //ClientInput memory data = ClientInput({functionToRun:1,dos:2});
        //emit print(block.timestamp);
        return block.timestamp;
    }
  
}