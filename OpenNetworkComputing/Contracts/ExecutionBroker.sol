// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./Transferable.sol";
import "./BaseClient.sol";


struct Executors {
    address[] addresses;
    mapping (address => uint) index;
    uint size;
}

struct Request {
    uint id;  // Index, for unicity when raw comparing
    BaseClient.ClientInput input;
    uint payment; // In Wei; deberia tener en cuenta el computo y el gas de las operaciones de submit y claim
    uint postProcessingGas;  // In Wei; for the post processing, if any
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
    Executors public executors;

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

    constructor() {
        executors.addresses.push(address(0x0));  // This is to reserve the index 0
    }

    function registerExecutor() public returns (uint) {
        require(executors.index[msg.sender] == 0, "This address is already registered as an executor");
        executors.addresses.push(msg.sender);
        uint index = executors.addresses.length - 1;
        executors.index[msg.sender] = index;
        executors.size++;
        return(index);
    }

    function unregisterExecutor() public returns (bool) {
        require(executors.index[msg.sender] != 0, "This address is not registered as an executor");
        uint index = executors.index[msg.sender];
        delete executors.addresses[index];
        delete executors.index[msg.sender];
        executors.size--;
        return true;
    }

    function submitRequest(BaseClient.ClientInput calldata input, uint postProcessingGas) public payable returns (uint) {
        require(msg.value - postProcessingGas > 0, "The post processing gas cannot takeup all of the supplied ether");  // en el bot de python, ver que efectivamente el net payment, valga la pena
        BaseClient clientImplementation = BaseClient(msg.sender);
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
            client: clientImplementation,
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
        bool transferSuccess = internalTransferFunds(requests[requestID].payment, payee);
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
        bool transferSuccess = internalTransferFunds(requests[requestID].challengeInsurance, payee);
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

    function claimPayment(uint requestID) public returns (bool) {
        require(requests[requestID].submission.issuer != address(0x0), "There are no submissions for the provided request");
        require(requests[requestID].submission.issuer == msg.sender, "This payment does not belong to you");
        require(!requests[requestID].submission.solidified, "The provided request has already solidified");
        require(requests[requestID].submission.timestamp + requests[requestID].claimDelay < block.timestamp, "The claim delay hasn't passed yet");
        bool transferSuccess = solidify(requestID);
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
    function solidify(uint requestID) private returns (bool) {
        // first solidify, then pay, for reentrancy issues
        requests[requestID].submission.solidified = true;
        emit requestSolidified(requestID);
        address payable payee = payable(requests[requestID].submission.issuer);
        uint payAmount = requests[requestID].payment + requests[requestID].challengeInsurance;
        bool transferSuccess = internalTransferFunds(payAmount, payee);
        
        bytes memory data = abi.encodeWithSelector(requests[requestID].client.processResult.selector, requests[requestID].submission.result);
        (bool callSuccess, ) = address(requests[requestID].client).call{gas: requests[requestID].postProcessingGas}(data);  // el delegate para que me aparezca el sender como el broker. cuidado si esto no me hace una vulnerabilidad, puedo vaciar fondos desde client? no deberia pasar nada, ni el broker ni el client puede extraer fondos
        emit resultPostProcessed(requestID, callSuccess);

        return transferSuccess;
    }

}