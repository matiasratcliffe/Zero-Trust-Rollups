class Acceptance:
    def __init__(self, _acceptor):
        self.acceptor = _acceptor
        #self.timestamp = ?

class Submission:
    def __init__(self, _issuer, _timestamp, _result, _solidified):
        self.issuer = _issuer
        self.timestamp = _timestamp
        self.result = _result
        self.solidified = _solidified

class Request:
    def __init__(self, _id, _client, _input, _payment, _postProcessingGas, _challengeInsurance, _claimDelay):
        self.id = _id
        self.input = _input
        self.payment = _payment
        self.postProcessingGas = _postProcessingGas
        self.challengeInsurance = _challengeInsurance
        self.claimDelay = _claimDelay
        self.client = _client
        self.cancelled = False
        self.acceptance = None
        self.submission = None
    
    def __str__(self):
        return "{{id: {self.id}, input: {self.input}, payment: {self.payment},\
            postProcessingGas: {self.postProcessingGas}, challengeInsurance: {self.challengeInsurance}, claimDelay: {self.claimDelay}, client: {self.client}, cancelled:  {self.cancelled}, acceptance: {self.acceptance}, submission: {self.submission}}}"