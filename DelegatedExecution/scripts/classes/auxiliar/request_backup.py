from scripts.classes.auxiliar.accountsManager import AccountsManager
#from scripts.classes.contracts import ClientFactory
from eth_abi import decode_abi


class Acceptance:
    def __init__(self, _acceptor):
        self.acceptor = _acceptor
        #self.timestamp = ?

    def __str__(self):
        return f"(<{self.acceptor.address}>)"

class Submission:
    def __init__(self, _issuer, _timestamp, _result, _solidified):
        self.issuer = _issuer
        self.timestamp = _timestamp
        self.result = _result
        self.solidified = _solidified
    
    def __str__(self):
        return f"(<{self.issuer.address}>, 0x{self.result.hex(), self.solidified})"

class Request:
    def __init__(self, requestID, chainRequest):
        self.id = requestID
        self.input = (int(chainRequest[0][0]), bytes(chainRequest[0][1]))
        self.payment = int(chainRequest[1])
        self.postProcessingGas = int(chainRequest[2])
        self.challengeInsurance = int(chainRequest[3])
        self.claimDelay = int(chainRequest[4])
        self.client = ClientFactory.fromAddress(str(chainRequest[5]))
        self.acceptance = None
        self.submission = None
        if (int(chainRequest[6][0], 16) != 0):
            self.acceptance = Acceptance(
                AccountsManager.getFromKey(str(chainRequest[6][0]))
            )
        if (int(chainRequest[7][0], 16) != 0):
            self.submission = Submission(
                AccountsManager.getFromKey(str(chainRequest[7][0])),
                int(chainRequest[7][1]),
                bytes(chainRequest[7][2]),
                chainRequest[7][3]
            )
        self.cancelled = chainRequest[8]
    
    def __str__(self):
        return f"{{id: {self.id}, input: ({self.input[0]}, 0x{self.input[1].hex()}), payment: {self.payment/1e+18} Eth, postProcessingGas: {self.postProcessingGas/1e+9} Gwei, challengeInsurance: {self.challengeInsurance/1e+18} Eth, claimDelay: {self.claimDelay/3600} Hours, client: {self.client}, cancelled: {self.cancelled}, acceptance: {self.acceptance}, submission: {self.submission}}}"
    
    def __repr__(self):
        return str(self)