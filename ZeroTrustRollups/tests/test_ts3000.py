from scripts.classes.utils.contractProvider import BrokerFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.TS3000Requestor import TS3000Requestor, AESCipher
from scripts.classes.TS3000Miner import TS3000Miner
from scripts.classes.utils.logger import Logger


class TestTS3000:
    def setup(self):
        pass

    def teardown(self):
        pass

    def setup_method(self, method):
        Logger.logIndentation=0

    def teardown_method(self, method):
        pass

    def test_ts3000(self):
        fileName = "text_file"
        broker = BrokerFactory.getInstance()
        requestor = TS3000Requestor(broker, Accounts.getFromIndex(0), fileName, numberOfKeyFragments=5, difficulty=5)
        reqID = requestor.getInitialRequestID()
        miner = TS3000Miner(broker, Accounts.getFromIndex(1))

        while True:
            broker.acceptRequest(reqID, {"from": miner.account, "value": BrokerFactory.ACCEPTANCE_STAKE})
            fragment = miner.mineFragment(reqID, 5)
            tx = miner.submitFragmentResult(reqID, fragment)
            if int(requestor.client.finalKey().hex(), 16) != 0:
                break
            reqID = tx.events["requestCreated"]["requestID"]
        finalKey = bytes(requestor.client.finalKey())

        with open(f"{fileName}.decrypted", "w") as f1:
            decryptedText = AESCipher(finalKey).decryptFile("text_file.encrypted")
            f1.write(decryptedText)
            with open(fileName, "r") as f2:
                originalText = f2.read()
                assert originalText == decryptedText