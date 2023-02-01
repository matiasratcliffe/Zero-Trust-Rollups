// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./Transferable.sol";
import "./BaseClient.sol";


struct Request {
    bytes input;
    uint payment; // In Wei; deberia tener en cuenta el computo y el gas de las operaciones de submit y claim
    uint postProcessingGas;  // In Wei; for the post processing, if any
    BaseClient client;
    // TODO code source???
    RequestAcceptance acceptance;
    Submission submission;
    bool closed;
}

struct RequestAcceptance {
    address acceptor;
    uint timestamp;  // TODO ver tema vencimiento o el castigo es la retencion de fondos?
}

struct Submission {
    address issuer;
    uint timestamp;
    bytes result;
}


contract ExecutionBroker is Transferable {

    Request[] public requests;

    event requestCreated(uint requestID, uint payment, uint challengeInsurance, uint claimDelay);
    event requestCancelled(uint requestID, bool refundSuccess);

    event requestAccepted(uint requestID, address acceptor);
    event acceptanceCancelled(uint requestID, address acceptor, bool refundSuccess);
    
    event resultSubmitted(uint requestID, bytes result);
    event resultPostProcessed(uint requestID, bool success);
    
    event paymentClaimed(uint requestID, bool success);
    
    event challengeProcessed(uint requestID, bytes result); mbape
    event challengePayment(uint requestID, bool success);
    

    function submitRequest(bytes calldata inputData, uint postProcessingGas, uint requestedInsurance, uint claimDelay) public payable returns (uint) {
        // check msg.sender is an actual client - creo que no se puede, me parece que lo voy a tener que dejar asi, creo que no es una vulnerabilidad, onda, si no es del tipo, va a fallar eventualmente, y problema del boludo que lo registro mal
        require(msg.value - postProcessingGas > 0, "The post processing gas cannot takeup all of the supplied ether");  // TODO en el bot de python, ver que efectivamente el net payment, valga la pena
        BaseClient clientImplementation = BaseClient(msg.sender);
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
            postProcessingGas: postProcessingGas,
            challengeInsurance: requestedInsurance,
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
        if (requests[requestID].client.checkResult(requests[requestID].input, result)) {
            Submission memory submission = Submission({
                issuer: msg.sender,
                timestamp: block.timestamp,
                result: result,
                solidified: false
            });
            requests[requestID].submission = submission;
            emit resultSubmitted(requestID, result);  // TODO revisar esto
        } else {
            // TODO remove acceptance, and emit event
        }
        
    }

    function claimPayment(uint requestID) public {
        require(requests[requestID].submission.issuer == msg.sender, "This payment does not belong to you");
        require(!requests[requestID].submission.solidified, "The provided request has already been completed");
        require(requests[requestID].submission.timestamp + requests[requestID].claimDelay < block.timestamp, "The claim delay hasn't passed yet");
        requests[requestID].closed = true;
        address payee = requests[requestID].submission.issuer;
        uint payAmount = requests[requestID].payment;
        bool transferSuccess = internalTransferFunds(payAmount, payee);
        
        // capaz la logica de encadenamiento es mejor definirla en python, o un mix
        bytes memory data = abi.encodeWithSelector(requests[requestID].client.processResult.selector, requests[requestID].submission.result);
        (bool callSuccess, ) = address(requests[requestID].client).call{gas: requests[requestID].postProcessingGas}(data);  // el delegate para que me aparezca el sender como el broker. cuidado si esto no me hace una vulnerabilidad, puedo vaciar fondos desde client? no deberia pasar nada, ni el broker ni el client puede extraer fondos
        emit resultPostProcessed(requestID, callSuccess);
        emit paymentClaimed(requestID, transferSuccess);
    }

    function isRequestOpen(uint requestID) public view returns (bool) {  // solo a modo de ayuda
        return (!requests[requestID].cancelled && requests[requestID].acceptance.acceptor == address(0x0));
    }
}