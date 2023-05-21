from eth_utils import keccak
from eth_abi import encode


class ExecutionState:

    def __init__(self, data, address):
        self.signingAddress = address
        self.data = str(data)
    
    def toTuple(self):
        return (self.data, self.signingAddress)
    
    def getHash(self):
        return keccak(encode(['(string,address)'], [self.toTuple()]))

    def __eq__(self, other) -> bool:
        return self.__class__ == other.__class__ and self.data == other.data