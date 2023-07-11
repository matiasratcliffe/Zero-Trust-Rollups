from scripts.classes.utils.contractProvider import BrokerFactory
from eth_abi import encode, decode
from eth_utils import keccak
from brownie import TS3000
import re


class TS3000Miner:
    def __init__(self, broker, account):
        self.broker = BrokerFactory.at(address=broker.address)
        self.account = account
    
    def mineFragment(self, requestID, difficulty):
        assert difficulty < 10, "The difficulty is to high to run on this device"
        request = self.broker.requests(requestID).dict()
        TS3000Contract = TS3000.at(self.broker.requests(requestID).dict()["client"])
        memberRegex = r"([A-Za-z][A-Za-z0-9]*)\s+[_A-Za-z][_A-Za-z0-9]*;"
        (fragmentIndex, globalHash, localHash) = decode(["("+",".join(re.findall(memberRegex, TS3000Contract.getInputDataStructure()))+")"], request["input"])[0]
        for passcode in range(10**difficulty):
            if keccak(encode(["uint", "bytes32"], [passcode, localHash])) == globalHash:
                break
        return encode(["("+",".join(re.findall(memberRegex, TS3000Contract.getResultDataStructure()))+")"], [(fragmentIndex, passcode)])

    def submitFragmentResult(self, requestID, result):
        return self.broker.submitResult(requestID, result, {"from": self.account})