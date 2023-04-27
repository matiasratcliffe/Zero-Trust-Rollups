// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./Transferable.sol";


struct Executor {
    address executorAddress;
    // Locked eth?
    // Reputation?
}

struct ExecutorsCollection {
    Executor[] activeExecutors;  // Not in a mapping because I need to be able to index them by uint
    mapping (address => Executor) inactiveExecutors;
    mapping (address => Executor) busyExecutors;
    mapping (address => uint) indexOf;
    uint amountOfActiveExecutors;
}

struct Request {
    uint id;
    address clientAddress; // TODO ver si lo hago con address o con BaseClient para incluir postprocessing
    string inputReference;
    string codeReference;
    uint payment; // In Wei; deberia tener en cuenta el computo y el gas de las operaciones de submit; y se divide entre los executors
    // TODO ver tema entorno de ejecucion restringido y capaz hacer payment fijo???
    //uint postProcessingGas;
    bool cancelled; // TODO o closed?
}

struct TaskAssignment {
    address executorAddress;
    uint timestamp;
    bytes result;
    bool submitted;
}


contract ExecutionBroker is Transferable {

    // TODO hacer mapping para paused executors
    uint public constant EXECUTION_TIME_FRAME_SECONDS = 3600;

    Request[] public requests;
    mapping (uint => TaskAssignment[]) public taskAssignmentsMap;
    ExecutorsCollection public executorsCollection;

    event requestCreated(uint requestID, uint payment, uint postProcessingGas, uint challengeInsurance, uint claimDelay);
    event requestCancelled(uint requestID, bool refundSuccess);

    event requestAccepted(uint requestID, address acceptor);
    event acceptanceCancelled(uint requestID, address acceptor, bool refundSuccess);
    
    event resultSubmitted(uint requestID, bytes result, address submitter);
    event resultPostProcessed(uint requestID, bool success);
    event requestSolidified(uint requestID);
    
    event challengeProcessed(uint requestID, bytes result);
    event challengePayment(uint requestID, bool success);

    event executorPaused(address executorAddress);
    event executorLocked(address executorAddress);
    event executorUnlocked(address executorAddress);
    event executorPunished(address executorAddress); // TODO que masss???
    

    // Restricted interaction functions

    constructor() {
        blockhash(9);
        Executor memory executor = Executor({
            executorAddress: address(0x0)
        });
        executorsCollection.activeExecutors.push(executor);  // This is to reserve the index 0, because when you delete an entry in the address => uint map, it gets set to 0
    }

    // Public views

    /*function isRequestOpen(uint requestID) public view returns (bool) {  // solo a modo de ayuda
        return (!requests[requestID].cancelled && requests[requestID].acceptor == address(0x0));
    }*/

    function requestCount() public view returns (uint) {
        return requests.length;
    }

    function getActiveExecutorsList() public view returns (address[] memory) {
        address[] memory addresses = new address[](executorsCollection.amountOfActiveExecutors);
        uint j = 0;
        for (uint i = 0; i < executorsCollection.activeExecutors.length; i++) {
            if (executorsCollection.activeExecutors[i].executorAddress != address(0x0)) {
                addresses[j] = executorsCollection.activeExecutors[i].executorAddress;
                j++;
            }
        }
        return addresses;
    }

    function getAmountOfActiveExecutors() public view returns (uint) {
        return executorsCollection.amountOfActiveExecutors;
    }

    function getExecutor(uint position) public view returns (Executor memory) {
        require(position < executorsCollection.amountOfActiveExecutors, "You are selecting a position outside the existing executors");
        uint j = 0;
        for (uint i = 0; i < executorsCollection.activeExecutors.length; i++) {
            if (executorsCollection.activeExecutors[i].executorAddress == address(0x0)) {
                continue;
            }
            if (j == position) {
                return executorsCollection.activeExecutors[i];
            }
            j++;
        }
    }

    // Open interaction functions

    function registerExecutor() public returns (uint) {  // TODO podria buscar el primer cero? indexOf? ir subiendo hasta que valga cero o sea igual a size
        // TODO ver tema de requerir fondos lockeados
        require(executorsCollection.inactiveExecutors[msg.sender].executorAddress == address(0x0), "The executor is already present, but inactive");
        return _registerExecutor(Executor({
            executorAddress: msg.sender
        }));
    }

    function pauseExecutor() public {
        _pauseExecutor(msg.sender);
    }

    function unpauseExecutor() public returns (uint) {
        require(executorsCollection.inactiveExecutors[msg.sender].executorAddress == msg.sender, "This address does not belong to a paused executor");
        uint executorIndex = _registerExecutor(executorsCollection.inactiveExecutors[msg.sender]);
        delete executorsCollection.inactiveExecutors[msg.sender];
        return executorIndex;
    }

    function getRandomNumber(uint floor, uint ceiling, uint blockOffset) public view returns (uint) {
        require(floor <= ceiling, "The floor cant be bigger than the ceiling");
        uint range = ceiling - floor;
        uint seed = (uint(blockhash(block.number - 1 - blockOffset)) / block.timestamp) + (block.timestamp ** 3);
        uint number = (seed % (range | 1)) + floor;
        return number;
    }

    function submitRequest(string calldata inputReference, string calldata codeReference, uint amountOfExecutors) public payable returns (uint) {
        //require(msg.value - postProcessingGas > 0, "The post processing gas cannot takeup all of the supplied ether");  // en el bot de python, ver que efectivamente el net payment, valga la pena
        require(amountOfExecutors <= executorsCollection.amountOfActiveExecutors, "You exceeded the number of available executors");
        require(amountOfExecutors % 2 == 1, "You must choose an odd amount of executors");
        // TODO ver tema pago, porque no hay incentivo, medio que te mandan a ejecutar por obligacion y capaz paga miseria. Capaz que haya pago cero, solo un lock en un escrow, y que los ejecutores incluyan en su respuesta encriptada el virtual-gas que les tomo ejecutar localmente
        Request memory request = Request({
            id: requests.length,
            clientAddress: msg.sender,
            inputReference: inputReference,
            codeReference: codeReference,
            payment: msg.value,  // aca esta incluido el post processing gas, para evitar tener que devolver aparte
            //postProcessingGas: postProcessingGas,
            //client: BaseClient(msg.sender),
            cancelled: false
        });
        requests.push(request);
        //emit requestCreated(request.id, msg.value, postProcessingGas, requestedInsurance, claimDelay); TODO
        TaskAssignment[] storage taskAssignments = taskAssignmentsMap[request.id];
        for (uint i = 0; i < amountOfExecutors; i++) {
            address executorAddress = getExecutor(getRandomNumber(1, executorsCollection.amountOfActiveExecutors, i)).executorAddress;
            taskAssignments.push(TaskAssignment({
                executorAddress: executorAddress,
                timestamp: block.timestamp,
                result: abi.encode(0),
                submitted: false
            }));
            _lockExecutor(executorAddress);
        }
        return request.id;
    }

    function rotateExecutors(uint requestID) public {
        require(requests[requestID].clientAddress == msg.sender, "You cant rotate a request that was not made by you");
        for (uint i = 0; i < taskAssignmentsMap[requestID].length; i++) {
            if (block.timestamp >= (taskAssignmentsMap[requestID][i].timestamp + EXECUTION_TIME_FRAME_SECONDS)) {
                //if (executorsCollection.amountOfActiveExecutors)
                // TODO maybe que el gas de ejecutar esto sea devuelto de el los fondos lockeados del ejecutor, aparentemente se puede saber tx.gas es gas price
                // TODO chequear que el que reemplaza no sea el mismo? o simplemente lo deshabilito hasta que el ejecutor manualmente se rehabilite?
            }
        }
    }

/*
    function cancelRequest(uint requestID) public { TODO que se pueda cancelar o rotare executores, alternativamente (bah, cancelar solo si ninguno ejecuto)
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
*/
    function _punishExecutor(address executorAddress) private {
        // TODO ver si bajo rep, elimino de executors, o slasheo
    }

    function _pauseExecutor(address executorAddress) private {
        require(executorsCollection.indexOf[executorAddress] != 0, "This address does not belong to an active executor");
        uint executorIndex = executorsCollection.indexOf[executorAddress];
        Executor memory executor = executorsCollection.activeExecutors[executorIndex];
        executorsCollection.inactiveExecutors[executorAddress] = executor;
        delete executorsCollection.activeExecutors[executorIndex];
        delete executorsCollection.indexOf[executorAddress];
        executorsCollection.amountOfActiveExecutors--;
        emit executorPaused(executorAddress);
    }

    function _lockExecutor(address executorAddress) private {
        require(executorsCollection.indexOf[executorAddress] != 0, "This address does not belong to an active executor");
        uint executorIndex = executorsCollection.indexOf[executorAddress];
        Executor memory executor = executorsCollection.activeExecutors[executorIndex];
        executorsCollection.busyExecutors[executorAddress] = executor;
        delete executorsCollection.activeExecutors[executorIndex];
        delete executorsCollection.indexOf[executorAddress];
        executorsCollection.amountOfActiveExecutors--;
        emit executorLocked(executorAddress);
    }

    function _unlockExecutor(address executorAddress) private returns (uint) {
        require(executorsCollection.busyExecutors[executorAddress].executorAddress == executorAddress, "This address does not belong to a locked executor");
        uint executorIndex = _registerExecutor(executorsCollection.busyExecutors[executorAddress]);
        delete executorsCollection.busyExecutors[executorAddress];
        return executorIndex;
    }

    function _registerExecutor(Executor memory executor) private returns (uint) {
        require(executorsCollection.indexOf[msg.sender] == 0, "This address is already registered as an active executor");
        executorsCollection.activeExecutors.push(executor);
        uint executorIndex = executorsCollection.activeExecutors.length - 1;
        executorsCollection.indexOf[msg.sender] = executorIndex;
        executorsCollection.amountOfActiveExecutors++;
        return executorIndex;
    }

}