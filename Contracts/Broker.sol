// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "Transferable.sol";
import "BaseClient.sol";


struct RequestChain {  // esto es para jugar con la posibilidad de que al solidificar una sumission se cree una nueva oferta
    bool chained;
    bytes chainData;
    //CAPAZ HAYA QUE BORRAR ESTO POR EL TEMA DEL PAYMENT, A MENOS QUE HAYA UN SISTEMA MAS COMPLEJO DE PAGO
}

struct Request {
    bytes input;
    uint payment; // In Wei; deberia tener en cuenta el computo y el gas de las operaciones de submit y claim
    uint challengeInsurance;  // amount of gas for challenges, TODO REVISAAAAR, deberia ser mayor al gas estimado, just in case
    uint claimDelay;  // the minimum amount of time that needs to pass between a submission and a payment claim, to allow for possible challengers
    BaseClient client;
    RequestAcceptance acceptance;
    Submission submission;
    
    //RequestChain chain; TODO
}

struct RequestAcceptance {
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

    uint public constant ACCEPTANCE_TIME_WINDOW = 3600;  // In ethereum, there is a tolerance of around 900 seconds for block.timestamp

    Request[] public requests;

    event requestCreated(uint requestID, uint payment, uint challengeInsurance, uint claimDelay);
    event challengePayment(uint requestID, bool success);
    event challengeProcessed(uint requestID, bytes result);
    event requestAccepted(uint requestID, address acceptor);
    event resultSubmitted(uint requestID, bytes result);
    event paymentClaimed(uint requestID, bool success);

    // TODO poner que el cliente pueda poner un time limit, tipo, unas semanas, para el cual, si nadie submiteo nada ni comiteo, puede retirar el pago y cancelar la request
    function submitRequest(bytes calldata inputData, address clientContractAddress, uint requestedInsurance, uint claimDelay) public payable returns (uint) {
        // check clientContractAddress is an actual client - creo que no se puede, me parece que lo voy a tener que dejar asi, creo que no es una vulnerabilidad, onda, si no es del tipo, va a fallar eventualmente, y problema del boludo que lo registro mal
        BaseClient clientImplementation = BaseClient(clientContractAddress);
        RequestAcceptance memory acceptance = RequestAcceptance({
            acceptor: address(0x0),
            timestamp: 0
        });
        Submission memory submission = Submission({
            issuer: address(0x0),
            timestamp: 0,
            result: "",
            solidified: false
        });
        Request memory request = Request({
            input: inputData,
            payment: msg.value,
            challengeInsurance: requestedInsurance,
            claimDelay: claimDelay,
            client: clientImplementation,
            acceptance: acceptance,
            submission: submission
        });
        requests.push(request);
        emit requestCreated(requests.length-1, msg.value, requestedInsurance, claimDelay);
        return requests.length - 1;
    }

    function acceptRequest(uint requestID) public payable {  // DO I MAKE THE INSURANCE HERE OR IN SUBMIT RESULT? TODO
        // what if Request does not exist? what happens to the funds? IF YOU TRY TO ACCESS AN INVALID INDEX IN AN ARRAY, THE FUNCTION GETS REVERTED AND FUNDS RETURNED TOGETHER WITH SPARE GAS (BUT NOT ALREADY CONSUMED GAS)
        // what happens to the funds if one of the requires fail? THEY GET RETURNED
        require(requests[requestID].submission.issuer == address(0x0), "The request has already been completed");
        require(requests[requestID].acceptance.acceptor == address(0x0) || (requests[requestID].acceptance.timestamp + ACCEPTANCE_TIME_WINDOW < block.timestamp), "Someone already accepted the request");
        require(msg.value == requests[requestID].challengeInsurance, "Incorrect amount of insurance provided");
        RequestAcceptance memory acceptance = RequestAcceptance({
            acceptor: msg.sender,
            timestamp: block.timestamp
        });
        requests[requestID].acceptance = acceptance;
        emit requestAccepted(requestID, msg.sender);
    }

    function submitResult(uint requestID, bytes calldata result) public {  // y si la gente maliciosa no quiere procesar esta transaccion? para hacerle perder la seña al pibe, o para que se le venza y robarle el resultado TODO
        require(requests[requestID].submission.issuer == address(0x0), "The request has already been completed");
        require(requests[requestID].acceptance.acceptor == msg.sender, "Someone else has accepted the Request");  // no chequeo el timestamp porque el timestamp es solo para ofertar, si se vencio, pero nadie mas contra oferto, vale
        Submission memory submission = Submission({
            issuer: msg.sender,
            timestamp: block.timestamp,
            result: result,
            solidified: false
        });
        requests[requestID].submission = submission;
        emit resultSubmitted(requestID, result);
    }

    function submitChallenge(uint requestID) public {  // no hace falta el nuevo resultado ya que se va a recalcular regardless
        require(requests[requestID].submission.issuer != address(0x0), "There are no submissions for the challenged request");
        require(!requests[requestID].submission.solidified, "The challenged submission has already solidified");

		bytes memory submittedResult = requests[requestID].submission.result;
        bytes memory requestInput = requests[requestID].input;
        bytes memory trueFinalResult = requests[requestID].client.clientLogic(requestInput);
        emit challengeProcessed(requestID, trueFinalResult);

        if (keccak256(submittedResult) != keccak256(trueFinalResult)) { // corregir el resultado
            Submission memory submission = Submission({
                issuer: msg.sender,
                timestamp: block.timestamp,
                result: trueFinalResult,
                solidified: false
            });
            requests[requestID].submission = submission;
            bool transferSuccess = solidify(requestID);
            // No revierto si no es success porque una corrida on chain es muy valiosa como para arriesgar el revert
            emit challengePayment(requestID, transferSuccess);
        } // else, el original lo hizo bien, dejo que pase el tiempo y cobre
    }

    function claimPayment(uint requestID) public {
        require(requests[requestID].submission.issuer == msg.sender, "This payment does not belong to you");
        require(!requests[requestID].submission.solidified, "The provided request has already solidified");
        require(requests[requestID].submission.timestamp + requests[requestID].claimDelay < block.timestamp, "The claim delay hasn't passed yet");
        bool transferSuccess = solidify(requestID);
        emit paymentClaimed(requestID, transferSuccess);
    }

    function isRequestOpen(uint requestID) public view returns (bool) {  // solo a modo de ayuda
        return requests[requestID].acceptance.acceptor == address(0x0);
    }

    function solidify(uint requestID) private returns (bool) {
        // first solidify, then pay, for reentrancy issues
        requests[requestID].submission.solidified = true;
        address payee = requests[requestID].submission.issuer;
        uint payAmount = requests[requestID].payment + requests[requestID].challengeInsurance;
        bool transferSuccess = internalTransferFunds(payAmount, payee);
        return transferSuccess;
    }
}