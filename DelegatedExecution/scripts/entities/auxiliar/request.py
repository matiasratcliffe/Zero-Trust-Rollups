class Acceptance:
    def __init__(self, _acceptor):
        self.acceptor = _acceptor
        #self.timestamp = ?

class Submission:
    def __init__(self, _issuer, _timestamp, _result):
        self.issuer = _issuer
        self.timestamp = _timestamp
        self.result = _result
        self.solidified = False

class Request:
    def __init__(self, _input, _payment, _postProcessingGas, _challengeInsurance, _claimDelay, _client):
        self.input = _input
        self.payment = _payment
        self.postProcessingGas = _postProcessingGas
        self.challengeInsurance = _challengeInsurance
        self.claimDelay = _claimDelay
        self.client = _client
        self.cancelled = False
        self.acceptance = None
        self.submission = None