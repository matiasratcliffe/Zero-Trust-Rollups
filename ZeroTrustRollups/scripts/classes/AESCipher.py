import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES
from eth_utils import keccak
from eth_abi import encode
from random import randint


class AESCipher(object):

    def __init__(self, passcode: int):
        self.bs = AES.block_size
        self.key = hashlib.sha256(keccak(encode(['uint'], [passcode])).hex().encode()).digest()

    def encryptFile(self, fileName):
        with open(fileName, "r") as f:
            fileContents = f.read()
            return self.encrypt(fileContents)

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw.encode()))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

class Requestor:

    def generateKeyFragments(self, size: int = 50, difficulty: int = 10):
        globalHashes = []
        localHashes = [keccak(encode(['uint'], [randint(int('9' * (difficulty - 2)), int('9' * difficulty))]))]
        for i in range(size):
            passcode = randint(int('9' * (difficulty - 2)), int('9' * difficulty))
            globalHashes.append(keccak(encode(['uint', 'bytes32'], [passcode, localHashes[i]])))
            if i < size - 1:
                localHashes.append(keccak(encode(['uint'], [passcode])))
        return localHashes[0], globalHashes