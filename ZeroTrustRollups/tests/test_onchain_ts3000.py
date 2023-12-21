from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger
from brownie import OnchainTS3000
from eth_utils import keccak
from eth_abi import encode
from random import randint


class TestOnchainTS3000:
    def setup(self):
        pass

    def teardown(self):
        pass

    def setup_method(self, method):
        Logger.logIndentation=0

    def teardown_method(self, method):
        pass

    def test_trivial_client_costs(self):
        pass

    def get_test_data(self, amount, difficulty):
        hashes = []
        passcodes = []
        for _ in range(amount):
            passcode = randint(0, int('9' * difficulty))
            hash = keccak(encode(['uint32'], [passcode]))
            passcodes.append(passcode)
            hashes.append(hash)
        return passcodes, hashes 

    def test_onchain_ts3000(self):
        amount = 30
        difficulty = 4
        passcodes, hashes = self.get_test_data(amount, difficulty)
        requestorAccount = Accounts.getFromIndex(0)
        initialRequestorBalance = requestorAccount.balance()
        contract = OnchainTS3000.deploy(hashes, difficulty, {"from": requestorAccount, "gas_price": 1})
        requestDeploymentCost = initialRequestorBalance - requestorAccount.balance()
        
        transactions = []
        calculatedPasscodes = []
        for i in range(amount):
            transactions.append(contract.resolveOnChain({"from": requestorAccount}))
            calculatedPasscodes.append(contract.passcodes(i))

        print(f"Request deployment cost: {requestDeploymentCost:,}")
        print("---------------------------------------------------------------------------------------")
        totalMiningCost = 0
        for i, tx in enumerate(transactions):
            print(f"Fragment {i} mining cost: {tx.gas_used:,}")
            totalMiningCost += tx.gas_used
        print("---------------------------------------------------------------------------------------")
        print(f"totalMiningCost: {totalMiningCost:,}")
        print("---------------------------------------------------------------------------------------")
        print(f"Original Passcodes: {passcodes}")
        print(f"Calculated Passcodes: {calculatedPasscodes}")

        raise "Interactive Console"