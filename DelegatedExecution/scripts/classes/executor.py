from scripts.logger import Logger

@Logger.LogClassMethods
class Executor:
    def __init__(self, account, broker, populateBuffers=False):
        self._listenForEvents = True
        self._minPayment = 1
        self._maxInsurance = 1e+18
        self._maxDelay = 60 * 60 * 24
        self.account = account
        self.broker = broker
        self.unacceptedRequests = []
        self.unsolidifiedSubmissions = []
        if (populateBuffers):
            self._populateBuffers
        def addUnacceptedRequest(event):
            Logger.log(f"Event[{event.event}]: {dict(event.args)}")
            if self._listenForEvents:
                if event.args.payment >= self._minPayment and event.args.challengeInsurance <= self._maxInsurance and event.args.claimDelay <= self._maxDelay:
                    self.unacceptedRequests.append(event.args.requestID)
        def addUnsolidifiedSubmission(event):
            Logger.log(f"Event[{event.event}]: {dict(event.args)}")
            if self._listenForEvents:
                self.unsolidifiedSubmissions.append(event.args.requestID)
        self.broker.instance.events.subscribe("requestCreated", lambda event : addUnacceptedRequest(event))
        self.broker.instance.events.subscribe("acceptanceCancelled", lambda event : addUnacceptedRequest(event))
        self.broker.instance.events.subscribe("requestCancelled", lambda event : self.unacceptedRequests.remove(event.args.requestID) if event.args.requestID in self.unacceptedRequests else None)
        self.broker.instance.events.subscribe("requestAccepted", lambda event : self.unacceptedRequests.remove(event.args.requestID) if event.args.requestID in self.unacceptedRequests else None)
        self.broker.instance.events.subscribe("resultSubmitted", lambda event : addUnsolidifiedSubmission(event))
        self.broker.instance.events.subscribe("requestSolidified", lambda event : self.unsolidifiedSubmissions.remove(event.args.requestID) if event.args.requestID in self.unsolidifiedSubmissions else None)

    def _populateBuffers(self):
        self.unacceptedRequests = []
        self.unsolidifiedSubmissions = []
        for req in self.broker.getRequests():
            if not req.cancelled:
                if req.acceptance == None:
                    Logger.log(f"Added request {req.id} to unaccepted requests")
                    self.unacceptedRequests.append(req.id)
                elif req.submission != None and req.submission.solidified:
                    Logger.log(f"Added request {req.id} to unsolidified submissions")
                    self.unsolidifiedSubmissions.append(req.id)
    
    def _acceptNextOpenRequest(self):
        request = self.broker.getRequest(self.unacceptedRequests.pop(0))
        self.broker.acceptRequest(request.id, self.account)
        return request.id

    def _computeResult(self, requestID):
        if self.broker.getRequest(requestID).acceptance.acceptor == self.account:
            dataInput = self.broker.getRequest(requestID).input
            result = self.broker.getRequest(requestID).client.instance.clientLogic(dataInput)
            Logger.log(f"Result computed: {requestID} => {result}")
            return result

    def _submitResult(self, requestID, result):
        self.broker.submitResult(requestID, result)
    
    def _challengeSubmission(self, requestID):
        self.broker.challengeSubmission(requestID, self.account)

    def solverLoopRound(self):
        if len(self.unacceptedRequests) > 0:
            requestID = self._acceptNextOpenRequest()
            result = self._computeResult(requestID)
            self._submitResult(requestID, result)
        else:
            Logger.log("Unaccepted requests buffer empty")

    def challengerLoopRound(self):
        if len(self.unsolidifiedSubmissions) > 0:
            request = self.broker.getRequest(self.unsolidifiedSubmissions.pop(0))
            result = self.computeResult(request.id)
            if result != request.submission.result:
                self.challengeSubmission(request.id)
            else:
                Logger.log("Result matches!")
        else:
            Logger.log("Unsolidified submissions buffer empty")
