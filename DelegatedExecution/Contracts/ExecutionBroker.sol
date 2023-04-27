// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./Transferable.sol";
import "./BaseClient.sol";


struct Request {
    uint id;  // Index, for unicity when raw comparing
    BaseClient.ClientInput input;
    uint payment; // In Wei; deberia tener en cuenta el computo y el gas de las operaciones de submit y claim
    uint postProcessingGas;  // In Wei; for the post processing, if any
    uint challengeInsurance;  // amount of gas for challenges, deberia ser mayor al gas estimado, just in case
    uint claimDelay;  // the minimum amount of time that needs to pass between a submission and a payment claim, to allow for possible challengers, in secconds
    BaseClient client;
    address acceptor;
    Submission submission;
    bool cancelled;
}

struct Submission {
    address issuer;
    uint timestamp;
    bytes result;
    bool solidified;
}


contract ExecutionBroker is Transferable {

    Request[] public requests;

    event requestCreated(uint requestID, uint payment, uint postProcessingGas, uint challengeInsurance, uint claimDelay);
    event requestCancelled(uint requestID, bool refundSuccess);

    event requestAccepted(uint requestID, address acceptor);
    event acceptanceCancelled(uint requestID, address acceptor, bool refundSuccess);
    
    event resultSubmitted(uint requestID, bytes result, address submitter);
    event resultPostProcessed(uint requestID, bool success);
    event requestSolidified(uint requestID);
    
    event challengeProcessed(uint requestID, bytes result);
    event challengePayment(uint requestID, bool success);
    

    // Restricted interaction functions

    function submitRequest(BaseClient.ClientInput calldata input, uint postProcessingGas, uint requestedInsurance, uint claimDelay) public payable returns (uint) {
        // check msg.sender is an actual client - creo que no se puede, me parece que lo voy a tener que dejar asi, creo que no es una vulnerabilidad, onda, si no es del tipo, va a fallar eventualmente, y problema del boludo que lo registro mal
        require(msg.value - postProcessingGas > 0, "The post processing gas cannot takeup all of the supplied ether");  // en el bot de python, ver que efectivamente el net payment, valga la pena
        Submission memory submission = Submission({
            issuer: address(0x0),
            timestamp: 0,
            result: abi.encode(0),
            solidified: false
        });
        Request memory request = Request({
            id: requests.length,
            input: input,
            payment: msg.value,  // aca esta incluido el post processing gas, para evitar tener que devolver aparte
            postProcessingGas: postProcessingGas,
            challengeInsurance: requestedInsurance,
            claimDelay: claimDelay,
            client: BaseClient(msg.sender),
            acceptor: address(0x0),
            submission: submission,
            cancelled: false
        });
        emit requestCreated(request.id, msg.value, postProcessingGas, requestedInsurance, claimDelay);
        requests.push(request);
        return request.id;
    }

    function cancelRequest(uint requestID) public {
        require(requestID < requests.length, "Index out of range");
        require(!requests[requestID].cancelled, "The request was already cancelled");
        require(msg.sender == address(requests[requestID].client), "You cant cancel a request that was not made by you");
        require(requests[requestID].acceptor == address(0x0), "You cant cancel an accepted request");
        //delete requests[requestID], no puedo hacer esto, this fucks up the ids
        requests[requestID].cancelled = true;
        address payable payee = payable(address(requests[requestID].client));
        bool transferSuccess = _internalTransferFunds(requests[requestID].payment, payee);
        emit requestCancelled(requestID, transferSuccess);
    }

    // Open interaction functions

    function publicizeRequest(uint requestID) public {  // This is to re emit the event In case the request gets forgotten
        require(requests[requestID].acceptor == address(0x00), "You cant publicize a taken request");
        emit requestCreated(requestID, requests[requestID].payment, requests[requestID].postProcessingGas, requests[requestID].challengeInsurance, requests[requestID].claimDelay);
    }

    function acceptRequest(uint requestID) public payable {
        // what if Request does not exist? what happens to the funds? IF YOU TRY TO ACCESS AN INVALID INDEX IN AN ARRAY, THE FUNCTION GETS REVERTED AND FUNDS RETURNED TOGETHER WITH SPARE GAS (BUT NOT ALREADY CONSUMED GAS)
        // what happens to the funds if one of the requires fail? THEY GET RETURNED
        require(!requests[requestID].cancelled, "The request was cancelled");
        require(requests[requestID].acceptor == address(0x0) , "Someone already accepted the request");
        require(msg.value == requests[requestID].challengeInsurance, "Incorrect amount of insurance provided");
        requests[requestID].acceptor = msg.sender;
        emit requestAccepted(requestID, msg.sender);
    }

    function cancelAcceptance(uint requestID) public {
        require(requests[requestID].acceptor != address(0x0), "There is no acceptor for the provided requestID");
        require(requests[requestID].submission.issuer == address(0x0), "This request already has a submission");
        require(requests[requestID].acceptor == msg.sender, "You cant cancel an acceptance that does not belong to you");
        address payable payee = payable(requests[requestID].acceptor);
        requests[requestID].acceptor = address(0x0);
        bool transferSuccess = _internalTransferFunds(requests[requestID].challengeInsurance, payee);
        emit acceptanceCancelled(requestID, payee, transferSuccess);
    }

    function submitResult(uint requestID, bytes calldata result) public {
        require(requests[requestID].acceptor != address(0x0), "You need to accept the request first");
        require(requests[requestID].submission.issuer == address(0x0), "There is already a submission for this request");
        require(requests[requestID].acceptor == msg.sender, "Someone else has accepted the Request");
        Submission memory submission = Submission({
            issuer: msg.sender,
            timestamp: block.timestamp,
            result: result,
            solidified: false
        });
        requests[requestID].submission = submission;
        emit resultSubmitted(requestID, result, msg.sender);
    }

    function challengeSubmission(uint requestID) public returns (bool) {
        require(requests[requestID].submission.issuer != address(0x0), "There are no submissions for the challenged request");
        require(!requests[requestID].submission.solidified, "The challenged submission has already solidified");

		bytes memory submittedResult = requests[requestID].submission.result;
        BaseClient.ClientInput memory requestInput = requests[requestID].input;
        bytes memory trueFinalResult = requests[requestID].client.clientLogic(requestInput);
        emit challengeProcessed(requestID, trueFinalResult);

        if (keccak256(submittedResult) != keccak256(trueFinalResult)) {
            Submission memory submission = Submission({
                issuer: msg.sender,
                timestamp: block.timestamp,
                result: trueFinalResult,
                solidified: false
            });
            requests[requestID].submission = submission;  // notar que en las requests que se resolvieron por challenge el acceptor es diferente al issuer (a menos que alguien se autochallengee)
            bool transferSuccess = _solidify(requestID);
            emit challengePayment(requestID, transferSuccess);
            return true;  // result was corrected
        } else {  // el original lo hizo bien, dejo que pase el tiempo y cobre TODO decidir si quiero pagar un challenge a una sub correcta
            return false;  // original was correct
        }
    }

    function claimPayment(uint requestID) public returns (bool) {
        require(requests[requestID].submission.issuer != address(0x0), "There are no submissions for the provided request");
        require(requests[requestID].submission.issuer == msg.sender, "This payment does not belong to you");
        require(!requests[requestID].submission.solidified, "The provided request has already solidified");
        require(requests[requestID].submission.timestamp + requests[requestID].claimDelay < block.timestamp, "The claim delay hasn't passed yet");
        bool transferSuccess = _solidify(requestID);
        return transferSuccess;
    }

    // Public views

    function isRequestOpen(uint requestID) public view returns (bool) {  // solo a modo de ayuda
        return (!requests[requestID].cancelled && requests[requestID].acceptor == address(0x0));
    }

    function requestCount() public view returns (uint) {
        return requests.length;
    }

    // Private functions
    function _solidify(uint requestID) private returns (bool) {
        // first solidify, then pay, for reentrancy issues
        requests[requestID].submission.solidified = true;
        emit requestSolidified(requestID);
        address payable payee = payable(requests[requestID].submission.issuer);
        uint payAmount = requests[requestID].payment + requests[requestID].challengeInsurance;
        bool transferSuccess = _internalTransferFunds(payAmount, payee);
        
        bytes memory data = abi.encodeWithSelector(requests[requestID].client.processResult.selector, requests[requestID].submission.result);
        (bool callSuccess, ) = address(requests[requestID].client).call{gas: requests[requestID].postProcessingGas}(data);  // el delegate para que me aparezca el sender como el broker. cuidado si esto no me hace una vulnerabilidad, puedo vaciar fondos desde client? no deberia pasar nada, ni el broker ni el client puede extraer fondos
        emit resultPostProcessed(requestID, callSuccess);

        return transferSuccess;
    }

}