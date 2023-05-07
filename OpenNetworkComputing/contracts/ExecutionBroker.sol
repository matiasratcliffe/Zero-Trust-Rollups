// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./Transferable.sol";


struct Executor {
    address executorAddress;
    uint assignedRequestID;
    uint lockedWei;
    uint accurateSolvings;
    uint inaccurateSolvings;
    uint timesPunished;
}

struct ExecutorsCollection {
    Executor[] activeExecutors;  // Not in a mapping because I need to be able to index them by uint
    mapping (address => uint) activeIndexOf;
    mapping (address => Executor) inactiveExecutors;
    mapping (address => Executor) busyExecutors;
    uint amountOfActiveExecutors;
}

struct Request {
    uint id;
    address clientAddress; // TODO ver si lo hago con address o con BaseClient para incluir postprocessing
    string inputStateReference;  // Tambien aca esta el point of insertion
    string codeReference;  // Tambien aca esta la data sobre la version y compilador y otras specs que pueden afectar el resultado
    uint payment; // In Wei; deberia tener en cuenta el computo y el gas de las operaciones de submit; y se divide entre los executors
    // TODO ver tema entorno de ejecucion restringido y capaz hacer payment fijo???
    //uint postProcessingGas;  TODO no hay post processing gas, ya que es el cliente quien deberia colectar los resultados y resolver los escrows
    bool closed;
}

struct TaskAssignment {
    address executorAddress;
    uint timestamp;
    bytes result;
    bool submitted;
}


contract ExecutionBroker is Transferable {

    uint public EXECUTION_TIME_FRAME_SECONDS;// = 3600;
    uint public BASE_STAKE_AMOUNT;// = 1e7;  // El cliente no tiene fondos lockeados salvo los que lockea en escrow por cada request. El executor, si tiene fondos lockeados, tanto para el escrow como para el punishment TODO ver que sea significativamente mayor a lo que pueda llegar a salir la rotacion con muchos executors y un gas particularmente alto. para eso tambien limitar el maximo de executors
    uint public MAXIMUM_EXECUTION_POWER;
    uint public MAXIMUM_EXECUTORS_PER_REQUEST;

    Request[] public requests;
    mapping (uint => TaskAssignment[]) public taskAssignmentsMap;
    ExecutorsCollection public executorsCollection;
    
    event resultSubmitted(uint requestID, bytes result, address submitter);
    event requestSolidified(uint requestID);

    event executorLocked(address executorAddress);
    event executorUnlocked(address executorAddress);
    event executorPunished(address executorAddress); // TODO que masss???
    

    // Restricted interaction functions

    constructor(uint executionTimeFrame, uint baseStakeAmount, uint maximumPower, uint maximumExecutors) {
        EXECUTION_TIME_FRAME_SECONDS = executionTimeFrame;
        BASE_STAKE_AMOUNT = baseStakeAmount;
        MAXIMUM_EXECUTION_POWER = maximumPower;
        MAXIMUM_EXECUTORS_PER_REQUEST = maximumExecutors;
        Executor memory executor = Executor({
            executorAddress: address(0x0),
            assignedRequestID: 0,
            lockedWei: 0,
            accurateSolvings: 0,
            inaccurateSolvings: 0,
            timesPunished: 0
        });
        Request memory request = Request({
            id: 0,
            clientAddress: address(0x0),
            inputStateReference: '',
            codeReference: '',
            payment: 0,
            closed: true
        });
        executorsCollection.activeExecutors.push(executor);  // This is to reserve the index 0, because when you delete an entry in the address => uint map, it gets set to 0
        requests.push(request);
    }

    // Public views

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

    function getExecutorStateByAddress(address executorAddress) public view returns (string memory executorState) {
        if (executorsCollection.activeIndexOf[executorAddress] != 0) {
            return "active";
        } else if (executorsCollection.inactiveExecutors[executorAddress].executorAddress == executorAddress) {
            return "inactive";
        } else if (executorsCollection.busyExecutors[executorAddress].executorAddress == executorAddress) {
            return "locked";
        } else {
            revert("This address does not belong to a registered executor");
        }
    } 

    function getExecutorByAddress(address executorAddress) public view returns (Executor memory executor) {  
        if (executorsCollection.activeIndexOf[executorAddress] != 0) {
            return executorsCollection.activeExecutors[executorsCollection.activeIndexOf[executorAddress]];
        } else if (executorsCollection.inactiveExecutors[executorAddress].executorAddress == executorAddress) {
            return executorsCollection.inactiveExecutors[executorAddress];
        } else if (executorsCollection.busyExecutors[executorAddress].executorAddress == executorAddress) {
            return executorsCollection.busyExecutors[executorAddress];
        } else {
            revert("This address does not belong to a registered executor");
        }
    }

    function getActiveExecutorByPosition(uint position) public view returns (Executor memory executor) {  // Position starts from zero and is not equal to index
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

    function registerExecutor() public payable {  // TODO podria buscar el primer cero? indexOf? ir subiendo hasta que valga cero o sea igual a size
        require(msg.value >= BASE_STAKE_AMOUNT, "To register an executor you must provide at least the minimum escrow stake amount");
        require(executorsCollection.inactiveExecutors[msg.sender].executorAddress == address(0x0), "The executor is already present, but inactive");
        require(executorsCollection.busyExecutors[msg.sender].executorAddress == address(0x0), "The executor is already present, but busy");
        _activateExecutor(Executor({
            executorAddress: msg.sender,
            assignedRequestID: 0,
            lockedWei: msg.value,
            accurateSolvings: 0,
            inaccurateSolvings: 0,
            timesPunished: 0
        }));
    }

    function pauseExecutor(bool withrawLockedFunds) public returns (bool) {
        require(executorsCollection.activeIndexOf[msg.sender] != 0, "This address does not belong to an active executor");
        bool transferSuccess = true;
        uint executorIndex = executorsCollection.activeIndexOf[msg.sender];
        Executor memory executor = executorsCollection.activeExecutors[executorIndex];
        if (withrawLockedFunds) {
            transferSuccess = _internalTransferFunds(executor.lockedWei, msg.sender);
            executor.lockedWei = 0;
        }
        executorsCollection.inactiveExecutors[msg.sender] = executor;
        delete executorsCollection.activeExecutors[executorIndex];
        delete executorsCollection.activeIndexOf[msg.sender];
        executorsCollection.amountOfActiveExecutors--;
        return transferSuccess;
    }

    function activateExecutor() public payable {
        require(executorsCollection.inactiveExecutors[msg.sender].executorAddress == msg.sender, "This address does not belong to a paused executor");
        require(executorsCollection.inactiveExecutors[msg.sender].lockedWei + msg.value >= BASE_STAKE_AMOUNT, "You must provide some Wei to reach the minimum escrow stake amount");
        executorsCollection.inactiveExecutors[msg.sender].lockedWei += msg.value;
        _activateExecutor(executorsCollection.inactiveExecutors[msg.sender]);
        delete executorsCollection.inactiveExecutors[msg.sender];
    }

    function getRandomNumber(uint floor, uint ceiling, uint blockOffset) public view returns (uint) {
        require(floor < ceiling, "The floor must be smaller than the ceiling");
        uint range = ceiling - floor;
        uint seed = (uint(blockhash(block.number - 1 - blockOffset)) / block.timestamp) + (block.timestamp ** 3);  // TODO too expensive?
        uint number = (seed % range) + floor;
        return number;
    }

    function submitRequest(string calldata inputStateReference, string calldata codeReference, uint amountOfExecutors, uint executionPowerPaidFor) public payable returns (uint) {
        // TODO podria implementar que el cliente elija un threshold de estadisticas de punisheado o innacurate
        require(executionPowerPaidFor <= MAXIMUM_EXECUTION_POWER, "You exceeded the maximum allowed exeution power per request");
        require(amountOfExecutors <= MAXIMUM_EXECUTORS_PER_REQUEST, "You exceeded the maximum number of allowed executors per request");
        require(amountOfExecutors <= executorsCollection.amountOfActiveExecutors, "You exceeded the number of available executors");
        require(amountOfExecutors % 2 == 1, "You must choose an odd amount of executors");
        require(msg.value == BASE_STAKE_AMOUNT + (executionPowerPaidFor * amountOfExecutors), "The value sent in the request must be the ESCROW_STAKE_AMOUNT plus the execution power you intend to pay for evrey executor");
        Request memory request = Request({
            id: requests.length,
            clientAddress: msg.sender,
            inputStateReference: inputStateReference,
            codeReference: codeReference,
            payment: executionPowerPaidFor,
            closed: false
        });
        requests.push(request);
        TaskAssignment[] storage taskAssignments = taskAssignmentsMap[request.id];
        for (uint i = 0; i < amountOfExecutors; i++) {
            address executorAddress = getActiveExecutorByPosition(getRandomNumber(0, executorsCollection.amountOfActiveExecutors, i)).executorAddress;
            taskAssignments.push(TaskAssignment({
                executorAddress: executorAddress,
                timestamp: block.timestamp,
                result: abi.encode(0),
                submitted: false
            }));
            _lockExecutor(executorAddress, request.id);
        }
        return request.id;
    }

    function rotateExecutors(uint requestID) public returns (bool) {
        require(requests[requestID].clientAddress == msg.sender, "You cant rotate a request that was not made by you");
        uint initialGas = gasleft();
        uint amountOfPunishedExecutors = 0;
        uint[] memory punishedExecutorsTaskIDs = new uint[](taskAssignmentsMap[requestID].length);  // Me van a quedar algunos en cero capaz, no importa
        for (uint i = 0; i < taskAssignmentsMap[requestID].length; i++) {
            if (!taskAssignmentsMap[requestID][i].submitted && block.timestamp >= (taskAssignmentsMap[requestID][i].timestamp + EXECUTION_TIME_FRAME_SECONDS)) {
                punishedExecutorsTaskIDs[amountOfPunishedExecutors++] = i;
            }
        }
        address[] memory punishedExecutorsAddresses = new address[](amountOfPunishedExecutors);
        for (uint i = 0; i < amountOfPunishedExecutors; i++) {
            if (executorsCollection.amountOfActiveExecutors > 0) {
                uint taskIndex = punishedExecutorsTaskIDs[i];
                punishedExecutorsAddresses[i] = taskAssignmentsMap[requestID][taskIndex].executorAddress;
                address newExecutorAddress = getActiveExecutorByPosition(getRandomNumber(0, executorsCollection.amountOfActiveExecutors, i)).executorAddress;
                taskAssignmentsMap[requestID][taskIndex].executorAddress = newExecutorAddress;
                taskAssignmentsMap[requestID][taskIndex].timestamp = block.timestamp;
                _lockExecutor(newExecutorAddress, requestID);
            }
        }

        uint punishGas = 12345;
        uint constantGasOverHead = 12345;
        uint effectiveAmountOfPunishedExecutors = amountOfPunishedExecutors < executorsCollection.amountOfActiveExecutors ? amountOfPunishedExecutors : executorsCollection.amountOfActiveExecutors;
        uint estimatedGasSpent = ((initialGas - gasleft()) + (punishGas * effectiveAmountOfPunishedExecutors) + constantGasOverHead) * tx.gasprice;  // This is just an aproximation, make it generous to favor the client
        uint punishAmount = estimatedGasSpent / effectiveAmountOfPunishedExecutors;
        for (uint i = 0; i < effectiveAmountOfPunishedExecutors; i++) {
            _punishExecutor(punishedExecutorsAddresses[i], punishAmount);
        }            
        bool transferSuccess = _internalTransferFunds(punishAmount * effectiveAmountOfPunishedExecutors, msg.sender);
        return transferSuccess;
    }

/*
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
        bool transferSuccess = _internalTransferFunds(payAmount, payee);
        
        bytes memory data = abi.encodeWithSelector(requests[requestID].client.processResult.selector, requests[requestID].submission.result);
        (bool callSuccess, ) = address(requests[requestID].client).call{gas: requests[requestID].postProcessingGas}(data);  // el delegate para que me aparezca el sender como el broker. cuidado si esto no me hace una vulnerabilidad, puedo vaciar fondos desde client? no deberia pasar nada, ni el broker ni el client puede extraer fondos
        emit resultPostProcessed(requestID, callSuccess);

        return transferSuccess;
    }
*/
    function _punishExecutor(address executorAddress, uint punishAmount) private {
        require(executorsCollection.busyExecutors[executorAddress].executorAddress == executorAddress, "You can only punish a locked executor");
        Executor memory executor = executorsCollection.busyExecutors[executorAddress];
        executor.lockedWei -= punishAmount;
        executor.timesPunished += 1;
        executorsCollection.inactiveExecutors[msg.sender] = executor;
        delete executorsCollection.busyExecutors[executorAddress];
    }

    function _lockExecutor(address executorAddress, uint requestID) private {
        require(executorsCollection.activeIndexOf[executorAddress] != 0, "This address does not belong to an active executor");
        uint executorIndex = executorsCollection.activeIndexOf[executorAddress];
        Executor memory executor = executorsCollection.activeExecutors[executorIndex];
        executor.assignedRequestID = requestID;
        executorsCollection.busyExecutors[executorAddress] = executor;
        delete executorsCollection.activeExecutors[executorIndex];
        delete executorsCollection.activeIndexOf[executorAddress];
        executorsCollection.amountOfActiveExecutors--;
        emit executorLocked(executorAddress);
    }

    function _unlockExecutor(address executorAddress) private {
        require(executorsCollection.busyExecutors[executorAddress].executorAddress == executorAddress, "This address does not belong to a locked executor");
        executorsCollection.busyExecutors[executorAddress].assignedRequestID = 0;
        _activateExecutor(executorsCollection.busyExecutors[executorAddress]);
        delete executorsCollection.busyExecutors[executorAddress];
    }

    function _activateExecutor(Executor memory executor) private { // TODO podria buscar el primer cero? indexOf? ir subiendo hasta que valga cero o sea igual a size
        require(executorsCollection.activeIndexOf[msg.sender] == 0, "This address is already registered as an active executor");
        executorsCollection.activeExecutors.push(executor);
        uint executorIndex = executorsCollection.activeExecutors.length - 1;
        executorsCollection.activeIndexOf[msg.sender] = executorIndex;
        executorsCollection.amountOfActiveExecutors++;
    }

}