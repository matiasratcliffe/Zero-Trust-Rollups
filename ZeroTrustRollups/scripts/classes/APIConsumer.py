from brownie.convert.datatypes import HexString
from eth_abi import encode
import re


class APIConsumer:

    def _getFunctionTypes(self, function):
        memberRegex = r"([A-Za-z][A-Za-z0-9]*)\s+[_A-Za-z][_A-Za-z0-9]*;"
        dataStruct = self.client.getInputStructure(function)
        return ["("+",".join(re.findall(memberRegex, dataStruct))+")"]

    def _encodeInput(self, functionToRun, data):
        return (functionToRun, HexString(encode(self._getFunctionTypes(functionToRun), [tuple(data)]), "bytes"))