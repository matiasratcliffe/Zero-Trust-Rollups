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
            Logger.log(f"Event[{event.event}]: {dict(event.args)}", logIndentation=0)
            request = self.broker.requests(event.args.requestID)
            payment = request[2] - request[3]
            challengeInsurance = request[4]
            claimDelay = request[5]
            if self._listenForEvents:
                if payment >= self._minPayment and challengeInsurance <= self._maxInsurance and claimDelay <= self._maxDelay:
                    self.unacceptedRequests.append(event.args.requestID)
        def addUnsolidifiedSubmission(event):
            Logger.log(f"Event[{event.event}]: {dict(event.args)}", logIndentation=0)
            if self._listenForEvents and event.args.submitter != self.account:  # TODO pedir al broker el request en base al reqID y mirar si vale la pena el gas/insurance
                self.unsolidifiedSubmissions.append(event.args.requestID)
        def removeUnacceptedRequest(event):
            Logger.log(f"Event[{event.event}]: {dict(event.args)}", logIndentation=0)
            if event.args.requestID in self.unacceptedRequests:
                self.unacceptedRequests.remove(event.args.requestID)
        def removeUnsolidifiedSubmission(event):
            Logger.log(f"Event[{event.event}]: {dict(event.args)}", logIndentation=0)
            if event.args.requestID in self.unsolidifiedSubmissions:
                self.unsolidifiedSubmissions.remove(event.args.requestID)
        # TODO ver tema matar threads
        self.broker.events.subscribe("requestCreated", addUnacceptedRequest)
        self.broker.events.subscribe("acceptanceCancelled", addUnacceptedRequest)
        self.broker.events.subscribe("requestCancelled", removeUnacceptedRequest)
        self.broker.events.subscribe("requestAccepted", removeUnacceptedRequest)
        self.broker.events.subscribe("resultSubmitted", addUnsolidifiedSubmission)
        self.broker.events.subscribe("requestSolidified", removeUnsolidifiedSubmission)

    def _populateBuffers(self):
        self.unacceptedRequests = []
        self.unsolidifiedSubmissions = []
        requests = [self.broker.requests(reqID) for reqID in range(self.broker.requestCount())]
        #Logger.log(f"requests: {requests}", color=Logger.colors.RED, raw=True)
        for index, req in enumerate(requests):
            if not req.dict()['cancelled']:
                if int(req.dict()['acceptance'][0], 16) == 0:
                    Logger.log(f"Added request {index} to unaccepted requests")
                    self.unacceptedRequests.append(index)
                elif int(req.dict()['submission'][0], 16) != 0 and not req.dict()['submission'][3]:
                    Logger.log(f"Added request {index} to unsolidified submissions")
                    self.unsolidifiedSubmissions.append(index)
    
    def _acceptRequest(self, requestID):
        request = self.broker.requests(requestID)
        transaction = self.broker.acceptRequest(requestID, {'from': self.account, 'value': request.dict()['challengeInsurance']})
        transaction.wait(1)
        self.unacceptedRequests.pop(self.unacceptedRequests.index(requestID))
        return transaction

    def _cancelAcceptance(self, requestID):
        transaction = self.broker.cancelAcceptance(requestID, {'from': self.account})
        transaction.wait(1)
        return transaction

    def _acceptNextOpenRequest(self):
        reqID = self.unacceptedRequests[0]
        self._acceptRequest(reqID)

    def _computeResult(self, requestID):
        if str(self.broker.requests(requestID).dict()['acceptance'][0]) == self.account.address:
            client = ClientFactory.at(address=self.broker.requests(requestID).dict()['client'])
            return client.clientLogic(self.broker.requests(requestID).dict()['input'])

    def _submitResult(self, requestID, result):
        transaction = self.broker.submitResult(requestID, result, {'from': self.account})
        transaction.wait(1)
        return transaction
    
    def _challengeSubmission(self, requestID):
        transaction = self.broker.challengeSubmission(requestID, {'from': self.account})
        transaction.wait(1)
        self.unsolidifiedSubmissions.pop(self.unsolidifiedSubmissions.index(requestID))
        return transaction

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
