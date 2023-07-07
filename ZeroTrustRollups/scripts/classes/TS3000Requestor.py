import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES
from eth_utils import keccak
from eth_abi import encode
from random import randint
from brownie import TS3000
from scripts.classes.utils.contractProvider import BrokerFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger


@Logger.LogClassMethods()
class AESCipher(object):

    def __init__(self, passcode: int):
        self.bs = AES.block_size
        self.key = hashlib.sha256(keccak(encode(['uint'], [passcode])).hex().encode()).digest()

    def encryptFile(self, fileName):
        with open(fileName, "r") as f:
            fileContents = f.read()
            return self.encrypt(fileContents)

    def encrypt(self, raw):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(self._pad(raw.encode())))

    def decryptFile(self, fileName):
        with open(fileName, "r") as f:
            fileContents = f.read()
            return self.decrypt(fileContents)

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * bytes(0x01)

    def _unpad(self, s):
        for i in range(1, len(s) - 1):
            if s[-i] != 0:
                break
        i -= 1
        return s[:-i] if i > 0 else s

@Logger.LogClassMethods()
class TS3000Requestor:

    def __init__(self, broker, account, paymentPerFragment, textFileToEncrypt, numberOfKeyFragments: int = 50, difficulty: int = 10):
        self.broker = broker
        self.owner = account
        firstLocalHash, globalHashes, passcode = self._generateKeyFragments(numberOfKeyFragments, difficulty)
        self.cipher = AESCipher(passcode)
        with open(textFileToEncrypt + ".encrypted", "w") as f:
            f.write(str(self.cipher.encryptFile(textFileToEncrypt))[2:-1])
        self.client = TS3000.deploy(broker.address, textFileToEncrypt + ".encrypted", firstLocalHash, globalHashes, {'from': account, 'value': paymentPerFragment})

    def _generateKeyFragments(self, size: int, difficulty: int):
        globalHashes = []
        localHashes = [keccak(encode(['uint'], [randint(int('9' * (difficulty - 2)), int('9' * difficulty))]))]
        for i in range(size):
            passcode = randint(int('9' * (difficulty - 2)), int('9' * difficulty))
            globalHashes.append(keccak(encode(['uint', 'bytes32'], [passcode, localHashes[i]])))
            if i < size - 1:
                localHashes.append(keccak(encode(['uint'], [passcode])))
        return localHashes[0], globalHashes, passcode

def main():
    broker = BrokerFactory.getInstance()
    requestor = TS3000Requestor(broker, Accounts.getAccount(), 1e14, "text_file")