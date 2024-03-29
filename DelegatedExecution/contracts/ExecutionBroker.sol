// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./Transferable.sol";
import "./BaseClient.sol";


struct Request {
    uint id;  // Index, for unicity when raw comparing
    BaseClient.ClientInput input;
    uint payment; // In Wei; deberia tener en cuenta el computo y el gas de las operaciones de submit y claim
    address[] confirmers;
    uint postProcessingGas;  // In Wei; for the post processing, if any
    uint challengeInsurance;  // amount of gas for challenges, deberia ser mayor al gas estimado, just in case
    uint claimDelay;  // the minimum amount of time that needs to pass between a submission and a payment claim, to allow for possible challengers, in secconds
    BaseClient client;
    Acceptance acceptance;
    Submission submission;
    bool cancelled;
}

struct Acceptance {
    address acceptor;
    uint timestamp;
}

struct Submission {
    address issuer;
    uint timestamp;
    bytes result;
    bool solidified;
}


contract ExecutionBroker is Transferable {

    uint public ACCEPTANCE_GRACE_PERIOD;  // = 300 seconds = 5 minutes 
    uint8 public CONFIRMERS_FEE_PERCENTAGE;
    uint8 public AMOUNT_OF_CONFIRMERS;

    Request[] public requests;

    event requestCreated(uint requestID, uint payment, uint postProcessingGas, uint challengeInsurance, uint claimDelay);
    event requestCancelled(uint requestID, bool refundSuccess);

    event requestAccepted(uint requestID, address acceptor);
    event acceptanceCancelled(uint requestID, address acceptor, bool refundSuccess);
    
    event resultSubmitted(uint requestID, bytes result, address submitter);
    event resultConfirmed(uint requestID);
    event requestSolidified(uint requestID);
    
    event challengeProcessed(uint requestID, bytes result);
    event challengePayment(uint requestID, address payee, bool success);
    
    constructor(uint acceptanceGracePeriod, uint8 confirmersFeePercentage, uint8 amountOfConfirmers) {
        ACCEPTANCE_GRACE_PERIOD = acceptanceGracePeriod;
        CONFIRMERS_FEE_PERCENTAGE = confirmersFeePercentage;
        AMOUNT_OF_CONFIRMERS = amountOfConfirmers;
    }

    // Restricted interaction functions

    function submitRequest(BaseClient.ClientInput calldata input, uint payment, uint postProcessingGas, uint requestedInsurance, uint claimDelay) public payable returns (uint) {
        // check msg.sender is an actual client - creo que no se puede, me parece que lo voy a tener que dejar asi, creo que no es una vulnerabilidad, onda, si no es del tipo, va a fallar eventualmente, y problema del boludo que lo registro mal
        require(msg.value == payment + (payment * AMOUNT_OF_CONFIRMERS * CONFIRMERS_FEE_PERCENTAGE) / 100, "The supplied ether must cover the payment and the confirmers fees");
        //require((payment / 4) >= postProcessingGas * tx.gasprice, "The post processing gas has to be lower than or equal to 1/4th of the payment");
        Acceptance memory acceptance = Acceptance({
            acceptor: address(0x0),
            timestamp: 0
        });
        Submission memory submission = Submission({
            issuer: address(0x0),
            timestamp: 0,
            result: abi.encode(0),
            solidified: false
        });
        Request memory request = Request({
            id: requests.length,
            input: input,
            payment: payment,  // aca esta incluido el post processing gas, para evitar tener que devolver aparte, ALSO el gasprice puede no ser el mismo entre el submit y el resolve, el payment tiene que ser generoso para el postprocessing
            confirmers: new address[](AMOUNT_OF_CONFIRMERS),
            postProcessingGas: postProcessingGas,
            challengeInsurance: requestedInsurance,
            claimDelay: claimDelay,
            client: BaseClient(payable(msg.sender)),
            acceptance: acceptance,
            submission: submission,
            cancelled: false
        });
        emit requestCreated(request.id, payment, postProcessingGas, requestedInsurance, claimDelay);
        requests.push(request);
        return request.id;
    }

    function cancelRequest(uint requestID) public {
        require(requestID < requests.length, "Index out of range");
        require(!requests[requestID].cancelled, "The request was already cancelled");
        require(msg.sender == address(requests[requestID].client), "You cant cancel a request that was not made by you");
        require(requests[requestID].acceptance.acceptor == address(0x0), "You cant cancel an accepted request");
        //delete requests[requestID], no puedo hacer esto, this fucks up the ids
        requests[requestID].cancelled = true;
        bool transferSuccess = _internalTransferFunds(requests[requestID].payment + (requests[requestID].payment * AMOUNT_OF_CONFIRMERS * CONFIRMERS_FEE_PERCENTAGE) / 100, address(requests[requestID].client));
        emit requestCancelled(requestID, transferSuccess);
    }

    // Open interaction functions

    function publicizeRequest(uint requestID) public {  // This is to re emit the event In case the request gets forgotten
        require(requests[requestID].acceptance.acceptor == address(0x00), "You cant publicize a taken request");
        emit requestCreated(requestID, requests[requestID].payment, requests[requestID].postProcessingGas, requests[requestID].challengeInsurance, requests[requestID].claimDelay);
    }

    function acceptRequest(uint requestID) public payable {
        // what if Request does not exist? what happens to the funds? IF YOU TRY TO ACCESS AN INVALID INDEX IN AN ARRAY, THE FUNCTION GETS REVERTED AND FUNDS RETURNED TOGETHER WITH SPARE GAS (BUT NOT ALREADY CONSUMED GAS)
        // what happens to the funds if one of the requires fail? THEY GET RETURNED
        require(!requests[requestID].cancelled, "The request was cancelled");
        require(requests[requestID].submission.issuer == address(0x0), "There is already a submission for this request");
        require(requests[requestID].acceptance.acceptor == address(0x0) || (requests[requestID].acceptance.timestamp + ACCEPTANCE_GRACE_PERIOD) < block.timestamp, "There already is an unexpired acceptance for this request");
        require(msg.value == requests[requestID].challengeInsurance, "Incorrect amount of insurance provided");
        if (requests[requestID].acceptance.acceptor != address(0x0)) {
            _internalTransferFunds(requests[requestID].challengeInsurance, requests[requestID].acceptance.acceptor);
        }
        requests[requestID].acceptance.acceptor = msg.sender;
        requests[requestID].acceptance.timestamp = block.timestamp;
        emit requestAccepted(requestID, msg.sender);
    }

    function cancelAcceptance(uint requestID) public {
        require(requests[requestID].acceptance.acceptor != address(0x0), "There is no acceptor for the provided requestID");
        require(requests[requestID].submission.issuer == address(0x0), "This request already has a submission");
        require(requests[requestID].acceptance.acceptor == msg.sender, "You cant cancel an acceptance that does not belong to you");
        requests[requestID].acceptance.acceptor = address(0x0);
        requests[requestID].acceptance.timestamp = 0;
        bool transferSuccess = _internalTransferFunds(requests[requestID].challengeInsurance, requests[requestID].acceptance.acceptor);
        emit acceptanceCancelled(requestID, requests[requestID].acceptance.acceptor, transferSuccess);
    }

    function submitResult(uint requestID, bytes calldata result) public {
        require(requests[requestID].acceptance.acceptor != address(0x0), "You need to accept the request first");
        require(requests[requestID].submission.issuer == address(0x0), "There is already a submission for this request");
        require(requests[requestID].acceptance.acceptor == msg.sender, "Someone else has accepted the Request");  // no chequeo el timestamp porque el timestamp es solo para ofertar, si se vencio, pero nadie mas contra oferto, vale
        Submission memory submission = Submission({
            issuer: msg.sender,
            timestamp: block.timestamp,
            result: result,
            solidified: false
        });
        requests[requestID].submission = submission;
        emit resultSubmitted(requestID, result, msg.sender);
    }

    function confirmResult(uint requestID) public payable {
        require(requests[requestID].submission.issuer != address(0x0), "There are no submissions for this request");
        require(!requests[requestID].submission.solidified, "This request has already been solidified");
        require(requests[requestID].submission.issuer != msg.sender, "You cant confirm your own result");
        require(requests[requestID].confirmers[AMOUNT_OF_CONFIRMERS - 1] == address(0x0), "This request has reached max confirmation");
        require(msg.value == (requests[requestID].challengeInsurance * CONFIRMERS_FEE_PERCENTAGE) / 100, "You need to deposit a percentage of the insurance fee to confirm");
        for (uint8 i = 0; i < AMOUNT_OF_CONFIRMERS; i++) {
            require(requests[requestID].confirmers[i] != msg.sender, "You have already confirmed this result");
            if (requests[requestID].confirmers[i] == address(0x0)) {
                requests[requestID].confirmers[i] = msg.sender;
                emit resultConfirmed(requestID);
                break;
            }
        }
    }

    function challengeSubmission(uint requestID, address challenger) public returns (bool) {
		require(msg.sender == address(requests[requestID].client), "You can only challenge a submission through the client");
        bytes memory submittedResult = requests[requestID].submission.result;
        BaseClient.ClientInput memory requestInput = requests[requestID].input;
        bytes memory trueFinalResult = requests[requestID].client.clientLogic(requestInput);
        emit challengeProcessed(requestID, trueFinalResult);

        if (keccak256(submittedResult) != keccak256(trueFinalResult)) {
            Submission memory submission = Submission({
                issuer: challenger,
                timestamp: block.timestamp,
                result: trueFinalResult,
                solidified: false
            });
            requests[requestID].submission = submission;  // notar que en las requests que se resolvieron por challenge el acceptor es diferente al issuer (a menos que alguien se autochallengee)
            uint feePayment = 0;
            for (uint8 i = 0; i < AMOUNT_OF_CONFIRMERS; i++) {
                if (requests[requestID].confirmers[i] == address(0x0)) {
                    if (feePayment > 0) {
                        _internalTransferFunds(feePayment, challenger);
                    }
                    break;
                }
                requests[requestID].confirmers[i] = address(0x0);
                feePayment += (requests[requestID].challengeInsurance * CONFIRMERS_FEE_PERCENTAGE) / 100;  // El challenger se queda con el fee de los confirmers
            }
            bool transferSuccess = _solidify(requestID);
            emit challengePayment(requestID, challenger, transferSuccess);
            return true;  // result was corrected
        } else {  // el original lo hizo bien, solidifico y le pago
            bool transferSuccess = _solidify(requestID);
            emit challengePayment(requestID, requests[requestID].submission.issuer, transferSuccess);
            return false;  // original was correct
        }
    }

    function claimPayment(uint requestID) public returns (bool) {
        require(msg.sender == address(requests[requestID].client), "You can only claim a payment through the client");
        bool transferSuccess = _solidify(requestID);
        return transferSuccess;
    }

    // Public views

    function isRequestOpen(uint requestID) public view returns (bool) {  // solo a modo de ayuda
        return (!requests[requestID].cancelled && requests[requestID].acceptance.acceptor == address(0x0));
    }

    function requestCount() public view returns (uint) {
        return requests.length;
    }

    function getRequests() public view returns (Request[] memory) {
        return requests;
    }

    function getRequest(uint requestID) public view returns (Request memory) {
        return requests[requestID];
    }

    // Private functions
    function _solidify(uint requestID) private returns (bool) {
        // first solidify, then pay, for reentrancy issues
        requests[requestID].submission.solidified = true;
        emit requestSolidified(requestID);
        uint payAmount = requests[requestID].payment + requests[requestID].challengeInsurance;
        bool transferSuccess = _internalTransferFunds(payAmount, requests[requestID].submission.issuer);
        for (uint8 i = 0; i < AMOUNT_OF_CONFIRMERS; i++) {
            if (requests[requestID].confirmers[i] != address(0x0)) {
                payAmount = ((requests[requestID].payment + requests[requestID].challengeInsurance) * CONFIRMERS_FEE_PERCENTAGE) / 100;
                _internalTransferFunds(payAmount, requests[requestID].confirmers[i]);   
            } else {
                uint refundAmount = (AMOUNT_OF_CONFIRMERS - i) * ((requests[requestID].payment * CONFIRMERS_FEE_PERCENTAGE) / 100);
                _internalTransferFunds(refundAmount, address(requests[requestID].client));
            }
        }
        return transferSuccess;
    }

}