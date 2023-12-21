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

    def test_ts3000_ztr(self):
        fileName = "text_file"
        broker = BrokerFactory.getInstance()
        requestorAccount = Accounts.getFromIndex(0)
        initialRequestorBalance = requestorAccount.balance()
        requestor = TS3000Requestor(broker, requestorAccount, fileName, numberOfKeyFragments=30, difficulty=4, paymentPerFragment=0, gas_price=1)
        requestDeploymentCost = initialRequestorBalance - requestorAccount.balance()
        reqID = requestor.getInitialRequestID()
        miner = TS3000Miner(broker, Accounts.getFromIndex(1))
        #executorAccount = Accounts.getFromIndex(4)
        #initialExecutorBalance = executorAccount.balance()
        #tx = broker.resolveRequestOnChain(0, {"from": executorAccount, "gas_price": 1})

        accTXs = []
        submitTXs = []
        while True:
            accTXs.append(broker.acceptRequest(reqID, {"from": miner.account, "value": BrokerFactory.ACCEPTANCE_STAKE}))
            fragment = miner.mineFragment(reqID, 5)
            tx = miner.submitFragmentResult(reqID, fragment)
            submitTXs.append(tx)
            if int(requestor.client.finalKey().hex(), 16) != 0:
                break
            reqID = tx.events["requestCreated"]["requestID"]
        finalKey = bytes(requestor.client.finalKey())

        print(f"Request deployment cost: {requestDeploymentCost:,}")
        print("---------------------------------------------------------------------------------------")
        totalMiningCost = 0
        for i in range(len(accTXs)):
            fragment = requestor.client.keyFragments(i).dict()
            miningCost = accTXs[i].gas_used + submitTXs[i].gas_used
            totalMiningCost += miningCost
            print(f"Fragment {i} Acceptance Gas: {accTXs[i].gas_used:,} Submission Gas: {submitTXs[i].gas_used:,}")
            #print(f"\tglobalHash: {fragment['globalHash']}")
            #print(f"\tlocalHash: {fragment['localHash']}")
            #print(f"\tpasscode: {fragment['passcode']}")
        print("---------------------------------------------------------------------------------------")
        print(f"totalMiningCost: {totalMiningCost:,}")
        print(f"finalKey: {requestor.client.finalKey()}")
        print("============================== short test summary info ================================")

        raise "Interactive Console"

        with open(f"{fileName}.decrypted", "w") as f1:
            decryptedText = AESCipher(finalKey).decryptFile("text_file.encrypted")
            f1.write(decryptedText)
            with open(fileName, "r") as f2:
                originalText = f2.read()
                assert originalText == decryptedText