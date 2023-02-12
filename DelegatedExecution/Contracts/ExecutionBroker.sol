// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./Transferable.sol";
import "./BaseClient.sol";


struct Request {
    BaseClient.ClientInput input;
    uint payment; // In Wei; deberia tener en cuenta el computo y el gas de las operaciones de submit y claim
    uint postProcessingGas;  // In Wei; for the post processing, if any
    uint challengeInsurance;  // amount of gas for challenges, deberia ser mayor al gas estimado, just in case
    uint claimDelay;  // the minimum amount of time that needs to pass between a submission and a payment claim, to allow for possible challengers, in secconds
    BaseClient client;
    RequestAcceptance acceptance;
    Submission submission;
    bool cancelled;
}

struct RequestAcceptance {
    address acceptor;
    uint timestamp;  // TODO ver tema vencimiento o el castigo es la retencion de fondos?
}

struct Submission {
    address issuer;
    uint timestamp;
    bytes result;
    bool solidified;
}


contract ExecutionBroker is Transferable {

    Request[] public requests;

    event requestCreated(uint requestID, uint payment, uint challengeInsurance, uint claimDelay);
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
        BaseClient clientImplementation = BaseClient(msg.sender);
        RequestAcceptance memory acceptance = RequestAcceptance({
            acceptor: address(0x0),
            timestamp: 0
        });
        Submission memory submission = Submission({
            issuer: address(0x0),
            timestamp: 0,
            result: "0x00",
            solidified: false
        });
        Request memory request = Request({
            input: input,
            payment: msg.value,
            postProcessingGas: postProcessingGas,
            challengeInsurance: requestedInsurance,
            claimDelay: claimDelay,
            client: clientImplementation,
            acceptance: acceptance,
            submission: submission,
            cancelled: false
        });
        requests.push(request);
        emit requestCreated(requests.length-1, msg.value, requestedInsurance, claimDelay);
        return requests.length - 1;
    }

    function cancelRequest(uint requestID) public {
        require(!requests[requestID].cancelled, "The request was already cancelled");
        require(msg.sender == address(requests[requestID].client), "You cant cancel a request that was not made by you");
        require(requests[requestID].acceptance.acceptor == address(0x0), "You cant cancel an accepted request");
        //delete requests[requestID], no puedo hacer esto, this fucks up the ids
        requests[requestID].cancelled = true;
        address payable payee = payable(address(requests[requestID].client));
        bool transferSuccess = internalTransferFunds(requests[requestID].payment, payee);
        emit requestCancelled(requestID, transferSuccess);
    }

    // Open interaction functions

    function publicizeRequest(uint requestID) public {  // This is to re emit the event In case the request gets forgotten
        require(requests[requestID].acceptance.acceptor == address(0x00), "You cant publicize a taken request");
        emit requestCreated(requestID, requests[requestID].payment, requests[requestID].challengeInsurance, requests[requestID].claimDelay);
    }

    function acceptRequest(uint requestID) public payable {
        // what if Request does not exist? what happens to the funds? IF YOU TRY TO ACCESS AN INVALID INDEX IN AN ARRAY, THE FUNCTION GETS REVERTED AND FUNDS RETURNED TOGETHER WITH SPARE GAS (BUT NOT ALREADY CONSUMED GAS)
        // what happens to the funds if one of the requires fail? THEY GET RETURNED
        require(!requests[requestID].cancelled, "The request was cancelled");
        require(requests[requestID].acceptance.acceptor == address(0x0) , "Someone already accepted the request");
        require(msg.value == requests[requestID].challengeInsurance, "Incorrect amount of insurance provided");
        RequestAcceptance memory acceptance = RequestAcceptance({
            acceptor: msg.sender,
            timestamp: block.timestamp
        });
        requests[requestID].acceptance = acceptance;
        emit requestAccepted(requestID, msg.sender);
    }

    function cancelAcceptance(uint requestID) public {
        // check request unsubmitted (at this point it cant be cancelled because the acceptance blocks it
        require(requests[requestID].acceptance.acceptor != address(0x0), "There is no acceptance in place for the provided requestID");
        require(requests[requestID].submission.issuer == address(0x0), "The results for this request have already beem submitted");
        require(requests[requestID].acceptance.acceptor == msg.sender, "You cant cancel an acceptance that does not belong to you");
        address payable payee = payable(requests[requestID].acceptance.acceptor);
        requests[requestID].acceptance.acceptor = address(0x0);
        bool transferSuccess = internalTransferFunds(requests[requestID].challengeInsurance, payee);
        emit acceptanceCancelled(requestID, payee, transferSuccess);
    }

    function submitResult(uint requestID, bytes calldata result) public {
        // para evitar que le roben el resultado, puede subirlo encriptado y posteriormente subir la clave de decrypt, NAAAA, no es eficiente
        // pero aca caigo en el mismo dilema, tengo que esperar que pase la clave decrypt y tengo que poner un timer para que no ponga cualquier cosa y se vaya, aunque supongo que no lo quiere hacer porque quiere recuperar la insurance. Entonces capaz saco el tiempo de acceptance time window, y confiar que el tipo va a cumplir porque quiere cobrar, aunque capaz se cuelga y no lo puede resolver, entonces capaz es mejor que se haga con encriptacion? no pero eso no me sirve porque desencriptar es costoso. Mejor le pongo una opcion al tipo para cancelar la aceptacion, y se come el gas pero recupera la prima
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

    function challengeSubmission(uint requestID) public returns (bool) {  // no hace falta el nuevo resultado ya que se va a recalcular regardless
        require(requests[requestID].submission.issuer != address(0x0), "There are no submissions for the challenged request");
        require(!requests[requestID].submission.solidified, "The challenged submission has already solidified");

		bytes memory submittedResult = requests[requestID].submission.result;
        BaseClient.ClientInput memory requestInput = requests[requestID].input;
        bytes memory trueFinalResult = requests[requestID].client.clientLogic(requestInput);
        emit challengeProcessed(requestID, trueFinalResult);

        if (keccak256(submittedResult) != keccak256(trueFinalResult)) { // corregir el resultado
            Submission memory submission = Submission({
                issuer: msg.sender,
                timestamp: block.timestamp,
                result: trueFinalResult,
                solidified: false
            });
            requests[requestID].submission = submission;  // notar que en las requests que se resolvieron por challenge el acceptor es diferente al issuer (a menos que alguien se autochallengee)
            bool transferSuccess = solidify(requestID);
            // No revierto si no es success porque una corrida on chain es muy valiosa como para arriesgar el revert
            emit challengePayment(requestID, transferSuccess);
            return true;  // result was corrected
        } // else, el original lo hizo bien, dejo que pase el tiempo y cobre
        return false;  // original was correct
    }

    function claimPayment(uint requestID) public returns (bool) {
        require(requests[requestID].submission.issuer == msg.sender, "This payment does not belong to you");
        require(!requests[requestID].submission.solidified, "The provided request has already solidified");
        require(requests[requestID].submission.timestamp + requests[requestID].claimDelay < block.timestamp, "The claim delay hasn't passed yet");
        bool transferSuccess = solidify(requestID);
        return transferSuccess;
    }

    // Public views

    function isRequestOpen(uint requestID) public view returns (bool) {  // solo a modo de ayuda
        return (!requests[requestID].cancelled && requests[requestID].acceptance.acceptor == address(0x0));
    }

    // Private functions

    function solidify(uint requestID) private returns (bool) {
        // first solidify, then pay, for reentrancy issues
        requests[requestID].submission.solidified = true;
        emit requestSolidified(requestID);
        address payee = requests[requestID].submission.issuer;
        uint payAmount = requests[requestID].payment + requests[requestID].challengeInsurance;
        bool transferSuccess = internalTransferFunds(payAmount, payee);
        
        // capaz la logica de encadenamiento es mejor definirla en python, o un mix
        bytes memory data = abi.encodeWithSelector(requests[requestID].client.processResult.selector, requests[requestID].submission.result);
        (bool callSuccess, ) = address(requests[requestID].client).call{gas: requests[requestID].postProcessingGas}(data);  // el delegate para que me aparezca el sender como el broker. cuidado si esto no me hace una vulnerabilidad, puedo vaciar fondos desde client? no deberia pasar nada, ni el broker ni el client puede extraer fondos
        emit resultPostProcessed(requestID, callSuccess);

        return transferSuccess;
    }
}