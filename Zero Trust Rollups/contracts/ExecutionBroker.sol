// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./Transferable.sol";
import "./BaseClient.sol";
import "./Ownable.sol";


struct Request {
    uint id;  // Index, for unicity when raw comparing
    bytes input; //TODO ver tema inputs y logic reference?
    uint payment; // In Wei; deberia tener en cuenta el computo y el gas de las operaciones de submit y claim
    BaseClient client;
    address executor;
    bytes result;
    bool closed;
    //TODO quizas para TS3000 hay que hacer un post processing logic
}


contract ExecutionBroker is Transferable, Ownable {

    uint public ACCEPTANCE_STAKE;

    Request[] public requests;

    event requestCreated(uint requestID, uint payment);
    event requestCancelled(uint requestID);

    event requestAccepted(uint requestID, address acceptor);
    event acceptanceCancelled(uint requestID, address acceptor, bool refundSuccess);

    event requestCompleted(uint requestID, bool transferSuccess);
    event requestReOpened(uint requestID, bool transferSuccess);

    constructor(uint acceptanceStake) Ownable() {
        ACCEPTANCE_STAKE = acceptanceStake;
    }

    // Restricted interaction functions

    function submitRequest(bytes calldata input) public payable returns (uint) {
        Request memory request = Request({
            id: requests.length,
            input: input,
            payment: msg.value,  // aca esta incluido el post processing gas, para evitar tener que devolver aparte
            client: BaseClient(msg.sender),
            executor: address(0x0),
            result: abi.encode(0),
            closed: false
        });
        emit requestCreated(request.id, msg.value);
        requests.push(request);
        return request.id;
    }

    function cancelRequest(uint requestID) public returns (bool) {
        require(!requests[requestID].closed, "The request is closed");
        require(msg.sender == address(requests[requestID].client), "You cant cancel a request that was not made by you");
        require(requests[requestID].executor == address(0x0), "You cant cancel an accepted request");
        requests[requestID].closed = true;
        address payable payee = payable(address(requests[requestID].client));
        emit requestCancelled(requestID);
        bool transferSuccess = _internalTransferFunds(requests[requestID].payment, payee);
        return transferSuccess;
    }

    // Open interaction functions

    function publicizeRequest(uint requestID) public {  // This is to re emit the event In case the request gets forgotten
        require(requests[requestID].executor == address(0x00), "You cant publicize a taken request");
        emit requestCreated(requestID, requests[requestID].payment);
    }

    function acceptRequest(uint requestID) public payable {
        // what if Request does not exist? what happens to the funds? IF YOU TRY TO ACCESS AN INVALID INDEX IN AN ARRAY, THE FUNCTION GETS REVERTED AND FUNDS RETURNED TOGETHER WITH SPARE GAS (BUT NOT ALREADY CONSUMED GAS)
        // what happens to the funds if one of the requires fail? THEY GET RETURNED
        require(!requests[requestID].closed, "The request is closed");
        require(requests[requestID].executor == address(0x0), "There already is an acceptance for this request");
        require(msg.value == ACCEPTANCE_STAKE, "Incorrect amount of stake provided");
        requests[requestID].executor = msg.sender;
        emit requestAccepted(requestID, msg.sender);
        // TODO Aca no hay acceptance override ya que no hay necesidad de que haya competencia de calculo
    }

    function cancelAcceptance(uint requestID) public {
        require(requests[requestID].executor != address(0x0), "There is no acceptor for the provided requestID");
        require(requests[requestID].closed == false, "This request is closed");
        require(requests[requestID].executor == msg.sender, "You cant cancel an acceptance that does not belong to you");
        requests[requestID].executor = address(0x0);
        bool transferSuccess = _internalTransferFunds((ACCEPTANCE_STAKE*95)/100, msg.sender);  // Devolver un 95% del stake
        emit acceptanceCancelled(requestID, requests[requestID].executor, transferSuccess);
        _internalTransferFunds((ACCEPTANCE_STAKE*5)/100, owner());
    }

    function submitResult(uint requestID, bytes calldata result) public returns (bool) {
        // para evitar que le roben el resultado, puede subirlo encriptado y posteriormente subir la clave de decrypt, NAAAA, no es eficiente
        // pero aca caigo en el mismo dilema, tengo que esperar que pase la clave decrypt y tengo que poner un timer para que no ponga cualquier cosa y se vaya, aunque supongo que no lo quiere hacer porque quiere recuperar la insurance. Entonces capaz saco el tiempo de acceptance time window, y confiar que el tipo va a cumplir porque quiere cobrar, aunque capaz se cuelga y no lo puede resolver, entonces capaz es mejor que se haga con encriptacion? no pero eso no me sirve porque desencriptar es costoso. Mejor le pongo una opcion al tipo para cancelar la aceptacion, y se come el gas pero recupera la prima
        require(requests[requestID].executor != address(0x0), "You need to accept the request first");
        require(requests[requestID].closed == false, "The request is already closed");
        require(requests[requestID].executor == msg.sender, "Someone else has accepted the Request");
        if (requests[requestID].client.checkResult(requests[requestID].input, result)) {
            requests[requestID].result = result;
            requests[requestID].closed = true;
            uint payAmount = requests[requestID].payment + ACCEPTANCE_STAKE;
            bool transferSuccess = _internalTransferFunds(payAmount, msg.sender);
            emit requestCompleted(requestID, transferSuccess);
            return true;
        } else {
            requests[requestID].executor = address(0x0);
            bool transferSuccess = _internalTransferFunds((ACCEPTANCE_STAKE*95)/100, msg.sender);
            emit requestReOpened(requestID, transferSuccess);
            _internalTransferFunds((ACCEPTANCE_STAKE*5)/100, owner());
            return false;
        }
    }
}