from scripts.classes.utils.contractProvider import ClientFactory
from scripts.classes.utils.logger import Logger
import time


@Logger.LogClassMethods()
class Executor:
    def __init__(self, account, broker, populateBuffers):
        self._listenForEvents = True
        self._minPayment = 1
        self._maxInsurance = 1e+18
        self._maxDelay = 60 * 60 * 24
        self.account = account
        self.broker = broker #BrokerFactory.at(address=broker) TODO check this!!!
        self.unacceptedRequests = []
        self.unsolidifiedSubmissions = []
        if (populateBuffers):
            self._populateBuffers()
        def addUnacceptedRequest(event):
            Logger.log(f"{self} detected -> Event[{event.event}]: {dict(event.args)}", logIndentation=0)
            request = self.broker.requests(event.args.requestID)
            payment = request[2] - request[3]
            challengeInsurance = request[4]
            claimDelay = request[5]
            if self._listenForEvents and event.args.requestID not in self.unacceptedRequests:
                if payment >= self._minPayment and challengeInsurance <= self._maxInsurance and claimDelay <= self._maxDelay:
                    self.unacceptedRequests.append(event.args.requestID)
        def addUnsolidifiedSubmission(event):
            Logger.log(f"{self} detected -> Event[{event.event}]: {dict(event.args)}", logIndentation=0)
            if self._listenForEvents and event.args.submitter != self.account and event.args.requestID not in self.unsolidifiedSubmissions:  # TODO pedir al broker el request en base al reqID y mirar si vale la pena el gas/insurance
                self.unsolidifiedSubmissions.append(event.args.requestID)
        def removeUnacceptedRequest(event):
            Logger.log(f"{self} detected -> Event[{event.event}]: {dict(event.args)}", logIndentation=0)
            if event.args.requestID in self.unacceptedRequests:
                self.unacceptedRequests.remove(event.args.requestID)
        def removeUnsolidifiedSubmission(event):
            Logger.log(f"{self} detected -> Event[{event.event}]: {dict(event.args)}", logIndentation=0)
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
    
    def __str__(self):
        return f"Executor ({str(self.account)[:6]}..{str(self.account)[-3:]})"

    def _acceptRequest(self, requestID):
        request = self.broker.requests(requestID).dict()
        transaction = self.broker.acceptRequest(requestID, {'from': self.account, 'value': request['challengeInsurance']})
        transaction.wait(1)
        if requestID in self.unacceptedRequests:
            self.unacceptedRequests.pop(self.unacceptedRequests.index(requestID))
        return transaction

    def _cancelAcceptance(self, requestID):
        transaction = self.broker.cancelAcceptance(requestID, {'from': self.account})
        transaction.wait(1)
        return transaction

    def _computeResult(self, requestID):
        client = ClientFactory.at(address=self.broker.requests(requestID).dict()['client'])
        return client.clientLogic(self.broker.requests(requestID).dict()['input'])

    def _submitResult(self, requestID, result):
        transaction = self.broker.submitResult(requestID, result, {'from': self.account})
        transaction.wait(1)
        return transaction
    
    def _challengeSubmission(self, requestID):
        client = ClientFactory.at(address=self.broker.requests(requestID).dict()['client'])
        transaction = client.challengeSubmission(requestID, {'from': self.account})
        transaction.wait(1)
        if requestID in self.unsolidifiedSubmissions:
            self.unsolidifiedSubmissions.pop(self.unsolidifiedSubmissions.index(requestID))
        return transaction

    def _claimPayment(self, requestID):
        client = ClientFactory.at(address=self.broker.requests(requestID).dict()['client'])
        return client.claimPayment(requestID, {'from': self.account})

    def solverLoopRound(self):
        if len(self.unacceptedRequests) > 0:
            requestID = self.unacceptedRequests.pop(0)
            self._acceptRequest(requestID)  # TODO what if anything here fails? TEST THAT TOO
            time.sleep(2) # TODO loop here?
            if str(self.broker.requests(requestID).dict()['acceptance'][0]) == self.account.address:
                result = self._computeResult(requestID)
                self._submitResult(requestID, result)
        else:
            Logger.log("Unaccepted requests buffer empty")

    def challengerLoopRound(self): #TODO que se pueda convalidar ejecucion, y que los primeros N (a determinar por el cliente) en convalidar se lleven una pequeña paga. Pero para convalidar tenes que dejar una prima que se va a devolver junto con la paga cuando se solidifique la request
        if len(self.unsolidifiedSubmissions) > 0:
            requestID = self.unsolidifiedSubmissions.pop(0)
            request = self.broker.requests(requestID)
            result = self._computeResult(requestID)
            if result != request[8][2]:
                self._challengeSubmission(requestID)
            else:
                Logger.log("Result matches!")
        else:
            Logger.log("Unsolidified submissions buffer empty")
