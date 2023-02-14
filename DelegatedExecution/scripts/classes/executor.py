from scripts.classes.utils.logger import Logger
from brownie.exceptions import VirtualMachineError
from scripts.classes.utils.contractProvider import ClientFactory, BrokerFactory


@Logger.LogClassMethods()
class Executor:
    def __init__(self, account, broker, populateBuffers=False):
        self._listenForEvents = True
        self._minPayment = 1
        self._maxInsurance = 1e+18
        self._maxDelay = 60 * 60 * 24
        self.account = account
        self.broker = BrokerFactory.at(address=broker)
        self.unacceptedRequests = []
        self.unsolidifiedSubmissions = []
        if (populateBuffers):
            self._populateBuffers()
        def addUnacceptedRequest(event):
            Logger.log(f"Event[{event.event}]: {dict(event.args)}")
            if self._listenForEvents:
                if event.args.payment >= self._minPayment and event.args.challengeInsurance <= self._maxInsurance and event.args.claimDelay <= self._maxDelay:
                    self.unacceptedRequests.append(event.args.requestID)
        def addUnsolidifiedSubmission(event):
            Logger.log(f"Event[{event.event}]: {dict(event.args)}")
            if self._listenForEvents and event.args.submitter != self.account:
                self.unsolidifiedSubmissions.append(event.args.requestID)
        self.broker.events.subscribe("requestCreated", addUnacceptedRequest)
        self.broker.events.subscribe("acceptanceCancelled", addUnacceptedRequest)
        self.broker.events.subscribe("requestCancelled", lambda event : self.unacceptedRequests.remove(event.args.requestID) if event.args.requestID in self.unacceptedRequests else None)
        self.broker.events.subscribe("requestAccepted", lambda event : self.unacceptedRequests.remove(event.args.requestID) if event.args.requestID in self.unacceptedRequests else None)
        self.broker.events.subscribe("resultSubmitted", addUnsolidifiedSubmission)
        self.broker.events.subscribe("requestSolidified", lambda event : self.unsolidifiedSubmissions.remove(event.args.requestID) if event.args.requestID in self.unsolidifiedSubmissions else None)

    def _populateBuffers(self):
        self.unacceptedRequests = []
        self.unsolidifiedSubmissions = []
        reqID = 0
        requests = []
        try:
            while True:
                requests.append(self.broker.requests(reqID))
                reqID += 1
        except VirtualMachineError:
            pass
        for req in requests:
            if not req.dict()['cancelled']:
                if int(req.dict()['acceptance'][0], 16) == 0:
                    Logger.log(f"Added request {requests.index(req)} to unaccepted requests")
                    self.unacceptedRequests.append(requests.index(req))
                elif int(req.dict()['submission'][0], 16) != 0 and not req.dict()['submission'][3]:
                    Logger.log(f"Added request {requests.index(req)} to unsolidified submissions")
                    self.unsolidifiedSubmissions.append(requests.index(req))
    
    def _acceptRequest(self, requestID):
        request = self.broker.requests(requestID)
        self.broker.acceptRequest(requestID, {'from': self.account, 'value': request.dict()['challengeInsurance']})
        self.unacceptedRequests.pop(self.unacceptedRequests.index(requestID))

    def _cancelAcceptance(self, requestID):
        self.broker.cancelAcceptance(requestID, {'from': self.account})

    def _acceptNextOpenRequest(self):
        reqID = self.unacceptedRequests[0]
        self._acceptRequest(reqID)

    def _computeResult(self, requestID):
        if str(self.broker.requests(requestID).dict()['acceptance'][0]) == self.account.address:
            client = ClientFactory.at(address=self.broker.requests(requestID).dict()['client'])
            return client.clientLogic(self.broker.requests(requestID).dict()['input'])

    def _submitResult(self, requestID, result):
        self.broker.submitResult(requestID, result, {'from': self.account})
    
    def _challengeSubmission(self, requestID):
        self.broker.challengeSubmission(requestID, {'from': self.account})
        self.unsolidifiedSubmissions.pop(self.unsolidifiedSubmissions.index(requestID))

    def solverLoopRound(self):
        if len(self.unacceptedRequests) > 0:
            requestID = self._acceptNextOpenRequest()
            result = self._computeResult(requestID)
            self._submitResult(requestID, result)
        else:
            Logger.log("Unaccepted requests buffer empty")

    def challengerLoopRound(self):
        if len(self.unsolidifiedSubmissions) > 0:
            request = self.broker.getRequest(self.unsolidifiedSubmissions[0])
            result = self.computeResult(request.id)
            if result != request.submission.result:
                self.challengeSubmission(request.id)
            else:
                Logger.log("Result matches!")
        else:
            Logger.log("Unsolidified submissions buffer empty")
