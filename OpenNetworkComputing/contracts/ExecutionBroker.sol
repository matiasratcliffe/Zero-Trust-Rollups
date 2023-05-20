// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./Transferable.sol";


struct Executor {
    address executorAddress;
    uint assignedRequestID;
    uint taskAssignmentIndex;
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
    string inputState;  // Tambien aca esta el point of insertion
    string codeReference;  // Tambien aca esta la data sobre la version y compilador y otras specs que pueden afectar el resultado
    uint executionPowerPaidFor; // In Wei; deberia tener en cuenta el computo y el gas de las operaciones de submit; y se divide entre los executors
    // TODO ver tema entorno de ejecucion restringido y capaz hacer payment fijo???
    //uint postProcessingGas;  TODO no hay post processing gas, ya que es el cliente quien deberia colectar los resultados y resolver los escrows
    Result result; // start empty, gets populated after escrow
    bool submissionsLocked;
    bool closed;
}

struct TaskAssignment {
    address executorAddress;
    uint timestamp;
    bytes32 signedResultHash;
    bytes32 unsignedResultHash;
    Result result;
    bool submitted;
    bool liberated;
}

struct Result {
    string data;
    address issuer;
}


contract ExecutionBroker is Transferable {

    uint public EXECUTION_TIME_FRAME_SECONDS;// = 3600;
    uint public BASE_STAKE_AMOUNT;// = 1e7;  // El cliente no tiene fondos lockeados salvo los que lockea en escrow por cada request. El executor, si tiene fondos lockeados, tanto para el escrow como para el punishment TODO ver que sea significativamente mayor a lo que pueda llegar a salir la rotacion con muchos executors y un gas particularmente alto. para eso tambien limitar el maximo de executors
    uint public MAXIMUM_EXECUTION_POWER;
    uint public MAXIMUM_EXECUTORS_PER_REQUEST;

    Request[] public requests;
    mapping (uint => TaskAssignment[]) public taskAssignmentsMap;
    ExecutorsCollection public executorsCollection;
    
    event resultSubmitted(uint requestID, address submitter);
    event requestSubmissionsLocked(uint requestID);
    event requestClosed(uint requestID, uint coincidences);

    event executorLocked(address executorAddress);
    event executorUnlocked(address executorAddress);
    event executorPunished(address executorAddress);
    

    // Restricted interaction functions

    constructor(uint executionTimeFrame, uint baseStakeAmount, uint maximumPower, uint maximumExecutors) {
        EXECUTION_TIME_FRAME_SECONDS = executionTimeFrame;
        BASE_STAKE_AMOUNT = baseStakeAmount;
        MAXIMUM_EXECUTION_POWER = maximumPower;
        MAXIMUM_EXECUTORS_PER_REQUEST = maximumExecutors;
        Executor memory executor = Executor({
            executorAddress: address(0x0),
            assignedRequestID: 0,
            taskAssignmentIndex: 0,
            lockedWei: 0,
            accurateSolvings: 0,
            inaccurateSolvings: 0,
            timesPunished: 0
        });
        Request memory request = Request({
            id: 0,
            clientAddress: address(0x0),
            inputState: '',
            codeReference: '',
            executionPowerPaidFor: 0,
            result: Result({
                data: '',
                issuer: address(0x0)
            }),
            submissionsLocked: false,
            closed: true
        });
        executorsCollection.activeExecutors.push(executor);  // This is to reserve the index 0, because when you delete an entry in the address => uint map, it gets set to 0
        requests.push(request);
    }

    // Public pures

    function getResultHash(Result memory result) public pure returns (bytes32) {
        return keccak256(abi.encode(result));
    }

    // Public views

    function requestCount() public view returns (uint) {
        return requests.length - 1;  // The request number 0 is blank
    }

    function getActiveExecutorsList() public view returns (address[] memory) {
        address[] memory addresses = new address[](executorsCollection.amountOfActiveExecutors);
        uint32 j = 0;
        for (uint32 i = 0; i < executorsCollection.activeExecutors.length; i++) {
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

    function getInactiveExecutorByAddress(address executorAddress) public view returns (Executor memory) {
        return executorsCollection.inactiveExecutors[executorAddress];
    }

    function getBusyExecutorByAddress(address executorAddress) public view returns (Executor memory) {
        return executorsCollection.busyExecutors[executorAddress];
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
        uint32 j = 0;
        for (uint32 i = 0; i < executorsCollection.activeExecutors.length; i++) {
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
            taskAssignmentIndex: 0,
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

    function submitRequest(string calldata inputState, string calldata codeReference, uint amountOfExecutors, uint executionPowerPaidFor) public payable returns (uint) {
        // TODO podria implementar que el cliente elija un threshold de estadisticas de punisheado o innacurate
        require(amountOfExecutors % 2 == 1, "You must choose an odd amount of executors");
        require(amountOfExecutors <= MAXIMUM_EXECUTORS_PER_REQUEST, "You exceeded the maximum number of allowed executors per request");
        require(executionPowerPaidFor <= MAXIMUM_EXECUTION_POWER, "You exceeded the maximum allowed execution power per request");
        require(amountOfExecutors <= executorsCollection.amountOfActiveExecutors, "You exceeded the number of available executors");
        require(msg.value == BASE_STAKE_AMOUNT + (executionPowerPaidFor * amountOfExecutors), "The value sent in the request must be the ESCROW_STAKE_AMOUNT plus the execution power you intend to pay for evrey executor");
        Request memory request = Request({
            id: requests.length,
            clientAddress: msg.sender,
            inputState: inputState,
            codeReference: codeReference,
            executionPowerPaidFor: executionPowerPaidFor,
            result: Result({
                data: '',
                issuer: address(0x0)
            }),
            submissionsLocked: false,
            closed: false
        });
        requests.push(request);
        TaskAssignment[] storage taskAssignments = taskAssignmentsMap[request.id];
        for (uint32 i = 0; i < amountOfExecutors; i++) {
            address executorAddress = getActiveExecutorByPosition(getRandomNumber(0, executorsCollection.amountOfActiveExecutors, i)).executorAddress;
            taskAssignments.push(TaskAssignment({
                executorAddress: executorAddress,
                timestamp: block.timestamp,
                signedResultHash: bytes32(abi.encode(0)),
                unsignedResultHash: bytes32(abi.encode(0)),
                result: Result({
                    data: '',
                    issuer: address(0x0)
                }),
                submitted: false,
                liberated: false
            }));
            _lockExecutor(executorAddress, request.id, i);
        }
        return request.id;
    }

    function rotateExecutors(uint requestID) public returns (bool) {
        require(requests[requestID].clientAddress == msg.sender, "You cant rotate a request that was not made by you");
        require(requests[requestID].submissionsLocked == false, "All executors for this request have already delivered");
        uint initialGas = gasleft();
        uint amountOfPunishedExecutors = 0;
        uint[] memory punishedExecutorsTaskIDs = new uint[](taskAssignmentsMap[requestID].length);  // Me van a quedar algunos en cero capaz, no importa
        for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
            if (!taskAssignmentsMap[requestID][i].submitted && block.timestamp >= (taskAssignmentsMap[requestID][i].timestamp + EXECUTION_TIME_FRAME_SECONDS)) {
                punishedExecutorsTaskIDs[amountOfPunishedExecutors++] = i;
            }
        }
        if (amountOfPunishedExecutors == 0) {
            return false;
        }
        address[] memory punishedExecutorsAddresses = new address[](amountOfPunishedExecutors);
        uint effectiveAmountOfPunishedExecutors = 0;
        for (uint8 i = 0; i < amountOfPunishedExecutors; i++) {
            if (executorsCollection.amountOfActiveExecutors > 0) {
                uint taskIndex = punishedExecutorsTaskIDs[i];
                punishedExecutorsAddresses[i] = taskAssignmentsMap[requestID][taskIndex].executorAddress;
                address newExecutorAddress = getActiveExecutorByPosition(getRandomNumber(0, executorsCollection.amountOfActiveExecutors, i)).executorAddress;
                taskAssignmentsMap[requestID][taskIndex].executorAddress = newExecutorAddress;
                taskAssignmentsMap[requestID][taskIndex].timestamp = block.timestamp;
                _lockExecutor(newExecutorAddress, requestID, i);
                effectiveAmountOfPunishedExecutors++;
            }
        }
        if (effectiveAmountOfPunishedExecutors == 0) {
            return false;
        }

        uint punishGas = 12345; //TODO
        uint constantGasOverHead = 12345; //TODO
        uint estimatedGasSpent = ((initialGas - gasleft()) + (punishGas * effectiveAmountOfPunishedExecutors) + constantGasOverHead) * tx.gasprice;  // This is just an aproximation, make it generous to favor the client
        uint punishAmount = estimatedGasSpent / effectiveAmountOfPunishedExecutors;
        for (uint8 i = 0; i < effectiveAmountOfPunishedExecutors; i++) {
            _punishExecutor(punishedExecutorsAddresses[i], punishAmount);
        }            
        bool transferSuccess = _internalTransferFunds(punishAmount * effectiveAmountOfPunishedExecutors, msg.sender);
        return transferSuccess;
    }

    function truncateExecutors(uint requestID) public {
        //TODO tiene que haber pasado el tiempo, y es como rotate pero no los rota, solo los elimina y castiga. por ende, tiene que haber al menos un numero impar de submit
    }

    function submitSignedResultHash(uint requestID, bytes32 signedResultHash) public {
        Executor memory executor = getExecutorByAddress(msg.sender);
        require(executor.assignedRequestID == requestID, "You must be assigned to the provided request to submit a result hash");
        require(taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].executorAddress == msg.sender, "There is an address missmatch in the assignment");  // This should never happen
        require(taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].submitted == false, "The result for this request, for this executor, has already been submitted");

        taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].signedResultHash = signedResultHash;
        taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].submitted = true;
        emit resultSubmitted(requestID, msg.sender);

        // if last one, mark request as submitted? do something else like start the escrow? SI ES EL ULTIMO SOLO MARCO COMO SUBMITED, REQUISITO PARA LIBERATE RESULT. POR LO QUE IMPLICITAMENTE ARRANCA EL ESCROW, Y AHI VAN POSTULANDO LOS RESULTADOS. Y EN EL LIBERATE RESULTS, SI ES EL ULTIMO, SE GENERA LA PAGA Y LIBERAN LOS STAKES CLIENT&EXECUTOR, O SI PASA CIERTO TIEMPO, EL CLIENTE PUEDE TRUNCAR LA LIBERACION PARA RETIRAR SU STAKE, Y LOS QUE NO HAYAN LIBERADO LA COMEN
        bool lastOne = true;
        for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
            if (!taskAssignmentsMap[requestID][i].submitted) {
                lastOne = false;
            }
        }
        if (lastOne) {
            requests[requestID].submissionsLocked = true;
            emit requestSubmissionsLocked(requestID);
        }

    }

    function liberateResult(uint requestID, Result memory result) public {
        Executor memory executor = getExecutorByAddress(msg.sender);
        require(executor.assignedRequestID == requestID, "You must be assigned to the provided request to liberate the result");
        require(taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].submitted == true, "You must first submit a signed result hash before you can liberate it");
        require(requests[requestID].submissionsLocked == true, "You must wait until all submissions for this request have been locked");
        require(taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].liberated == false, "The result for this request, for this executor, has already been liberated");
        
        // TODO test in python
        require(result.issuer == msg.sender, "The issuer of the sent result does not match the transaction sender");
        require(getResultHash(result) == taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].signedResultHash, "Your result does not match your submitted hash");
        
        result.issuer = address(this);
        
        taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].unsignedResultHash = keccak256(abi.encode(result));
        taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].result = result;
        taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].liberated = true;

        bool lastOne = true;
        for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
            if (!taskAssignmentsMap[requestID][i].liberated) {
                lastOne = false;
            }
        }
        if (lastOne) {
            bytes32[] memory hashes = new bytes32[](taskAssignmentsMap[requestID].length);
            uint8[] memory indexes = new uint8[](taskAssignmentsMap[requestID].length);
            uint8[] memory appearences = new uint8[](taskAssignmentsMap[requestID].length);
            for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
                for (uint8 j = 0; j <= i; j++) {
                    if (hashes[j] == bytes32(0x0)) {
                        hashes[j] = taskAssignmentsMap[requestID][i].unsignedResultHash;
                        indexes[j] = i;
                        appearences[j] = 1;
                        break;
                    } else if (hashes[j] == taskAssignmentsMap[requestID][i].unsignedResultHash) {
                        appearences[j]++;
                        break;
                    }
                }
            }
            uint8 assignmentIndexOfMaximum = 0;
            uint8 appearenceIndexOfMaximum = 0;
            for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
                if (appearences[i] > appearences[appearenceIndexOfMaximum]) {  // Si hay empate, que gane el primero
                    appearenceIndexOfMaximum = i;
                    assignmentIndexOfMaximum = indexes[i];
                }
            }
            
            // Result posting
            // TODO emit amount of appearences for result in event
            requests[requestID].result = taskAssignmentsMap[requestID][assignmentIndexOfMaximum].result;
            requests[requestID].closed = true;
            emit requestClosed(requestID, appearences[appearenceIndexOfMaximum]);

            // Punishments and payments
            address[] memory executorsToBeRewarded = new address[](appearences[appearenceIndexOfMaximum]);
            uint8 rewardedIndex = 0;
            address[] memory executorsToBePunished = new address[](taskAssignmentsMap[requestID].length - appearences[appearenceIndexOfMaximum]);
            uint8 punishedIndex = 0;
            for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
                if (taskAssignmentsMap[requestID][i].unsignedResultHash == hashes[appearenceIndexOfMaximum]) {
                    executorsToBeRewarded[rewardedIndex++] = taskAssignmentsMap[requestID][i].executorAddress;
                } else {
                    executorsToBePunished[punishedIndex++] = taskAssignmentsMap[requestID][i].executorAddress;
                }
            }
            for (uint8 i = 0; i < rewardedIndex; i++) {

            }
            for (uint8 i = 0; i < punishedIndex; i++) {
                
            }
        }
        // TODO preguntarme si es necesario un escrow, y que el cliente tenga fondos lockeados? capaz el cliente tiene la paga y los unicos con fondos lockeados son los ejecutores
    }

    function truncateResultLiberation(uint requestID) public {

    }

    // Private Functions

    function _punishExecutor(address executorAddress, uint punishAmount) private {
        require(executorsCollection.busyExecutors[executorAddress].executorAddress == executorAddress, "You can only punish a locked executor");
        Executor memory executor = executorsCollection.busyExecutors[executorAddress];
        executor.lockedWei -= punishAmount;
        executor.timesPunished += 1;
        executor.assignedRequestID = 0;
        executorsCollection.inactiveExecutors[executorAddress] = executor;
        delete executorsCollection.busyExecutors[executorAddress];
    }

    function _lockExecutor(address executorAddress, uint requestID, uint taskAssignmentIndex) private {
        require(executorsCollection.activeIndexOf[executorAddress] != 0, "This address does not belong to an active executor");
        uint executorIndex = executorsCollection.activeIndexOf[executorAddress];
        Executor memory executor = executorsCollection.activeExecutors[executorIndex];
        executor.assignedRequestID = requestID;
        executor.taskAssignmentIndex = taskAssignmentIndex;
        executorsCollection.busyExecutors[executorAddress] = executor;
        delete executorsCollection.activeExecutors[executorIndex];
        delete executorsCollection.activeIndexOf[executorAddress];
        executorsCollection.amountOfActiveExecutors--;
        emit executorLocked(executorAddress);
    }

    function _unlockExecutor(address executorAddress) private { // TODO cuando usaria esto?? solo cuando se termina bien la ejecucion? o en algun caso triste?
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