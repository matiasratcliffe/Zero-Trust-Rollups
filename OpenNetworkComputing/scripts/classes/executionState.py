from eth_utils import keccak
from eth_abi import encode_abi


class ExecutionState:

    def __init__(self, data):
        self.signingAddress = ""
        self.data = data

    def getSignedHash(self, signingAddress):
        self.signingAddress = signingAddress
        return keccak(encode_abi(['string'], [str(self)])).hex()

    def __str__(self) -> str:
        return f'{{"data":"{str(self.data)}","signingAddress":"{str(self.signingAddress)}"}}'

    def __eq__(self, other) -> bool:
        return self.__class__ == other.__class__ and self.data == other.data