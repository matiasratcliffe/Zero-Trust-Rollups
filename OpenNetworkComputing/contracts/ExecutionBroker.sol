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

enum CategoryIdentifiers {
    HIGHEST,
    STANDARD,
    LOWEST
}

struct ExecutorCategory {
    Executor[] activeExecutors;
    mapping (address => uint) activeIndexOf;
    uint24 amountOfActiveExecutors;
}

struct ExecutorsCollection {
    ExecutorCategory[3] executorCategories;
    mapping (address => Executor) inactiveExecutors;
    mapping (address => Executor) busyExecutors;
    uint24 amountOfActiveExecutors;
}

struct Request {
    uint id;
    address clientAddress;
    uint executionPowerPrice;
    uint executionPowerPaidFor;
    string inputState;  // Tambien aca esta el point of insertion
    string codeReference;  // Tambien aca esta la data sobre la version y compilador y otras specs que pueden afectar el resultado
    // TODO ver tema entorno de ejecucion restringido
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

enum ExecutorState {
    ACTIVE,
    INACTIVE,
    LOCKED
}

enum PunishmentCase {
    REGULAR,
    TRUNCATED,
    INACCURATE_SOLVING
}

contract ExecutionBroker is Transferable {

    uint public PUNISH_GAS = 12345; //TODO

    uint public EXECUTION_TIME_FRAME_SECONDS;// = 3600;
    uint public BASE_STAKE_AMOUNT;// = 1e7;  // El cliente no tiene fondos lockeados. El executor, si tiene fondos lockeados para el punishment. ver que sea significativamente mayor a lo que pueda llegar a salir la rotacion con muchos executors y un gas particularmente alto. para eso tambien limitar el maximo de executors
    uint public MAXIMUM_EXECUTION_POWER;
    uint public MAXIMUM_EXECUTORS_PER_REQUEST;

    Request[] public requests;
    mapping (uint => TaskAssignment[]) public taskAssignmentsMap;
    ExecutorsCollection public executorsCollection;
    uint referenceExecutionPowerPriceCache;
    
    event requestCreated(uint requestID, address clientAddress);
    event resultSubmitted(uint requestID, address submitter);
    event requestSubmissionsLocked(uint requestID);
    event requestClosed(uint requestID, uint coincidences);
    event requestRecycled(uint requestID);

    event executorLocked(address executorAddress);
    event executorUnlocked(address executorAddress);
    event executorPunished(address executorAddress);

    constructor(uint executionTimeFrame, uint baseStakeAmount, uint maximumPower, uint maximumExecutors) {
        referenceExecutionPowerPriceCache = 1; //TODO
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
            executionPowerPrice: 0,
            executionPowerPaidFor: 0,
            inputState: '',
            codeReference: '',
            result: Result({
                data: '',
                issuer: address(0x0)
            }),
            submissionsLocked: false,
            closed: true
        });
        executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].activeExecutors.push(executor);  // This is to reserve the index 0, because when you delete an entry in the address => uint map, it gets set to 0
        executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].activeExecutors.push(executor);
        executorsCollection.executorCategories[uint8(CategoryIdentifiers.LOWEST)].activeExecutors.push(executor);
        requests.push(request);  // This is because executors have an assignedRequestID that when set to 0 is meant to be interpreted as null
    }

    // Pure functions

    function getExecutorCategory(Executor memory executor) public pure returns (CategoryIdentifiers) {
        uint divider = (executor.timesPunished + executor.inaccurateSolvings) * 50; // * 100 / 2
        divider = divider == 0 ? 1 : divider;
        uint score = (executor.accurateSolvings * 10000) / divider;
        if (score <= 50) {
            return CategoryIdentifiers.LOWEST;
        } else if (score >= 200) {
            return CategoryIdentifiers.HIGHEST;
        } else {
            return CategoryIdentifiers.STANDARD;
        }
    }

    // Public views

    function requestCount() public view returns (uint) {
        return requests.length - 1;  // The request number 0 is blank
    }

    function getRequests() public view returns (Request[] memory) {
        return requests;
    }

    function getActiveExecutorsList() public view returns (address[][] memory) {
        address[][] memory addresses = new address[][](3);
        uint24 j = 0;
        for (uint8 category = 0; category < 3; category++) {
            addresses[category] = new address[](executorsCollection.executorCategories[uint8(category)].amountOfActiveExecutors);
            for (uint24 i = 0; i < executorsCollection.executorCategories[uint8(category)].activeExecutors.length; i++) {  // La categoria arranca con un executor nulo, y puede o no tener huecos por ejecutores blockeados o removidos, por eso uso length para recorrer, y no amount que es el numero de efectivos
                if (executorsCollection.executorCategories[uint8(category)].activeExecutors[i].executorAddress != address(0x0)) {
                    addresses[uint8(category)][j] = executorsCollection.executorCategories[uint8(category)].activeExecutors[i].executorAddress;
                    j++;
                }
            }
        }
        return addresses;
    }

    function getAmountOfActiveExecutors() public view returns (uint) {
        return executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].amountOfActiveExecutors +
            executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].amountOfActiveExecutors +
            executorsCollection.executorCategories[uint8(CategoryIdentifiers.LOWEST)].amountOfActiveExecutors;
    }

    function getAmountOfActiveExecutorsWithCriteria(CategoryIdentifiers minimumCategory) public view returns (uint24) {
        uint24 amountOfFittingExecutors = executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].amountOfActiveExecutors;
        if (minimumCategory == CategoryIdentifiers.STANDARD) {
            amountOfFittingExecutors += executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].amountOfActiveExecutors;
        } else if (minimumCategory == CategoryIdentifiers.LOWEST) {
            amountOfFittingExecutors += executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].amountOfActiveExecutors + executorsCollection.executorCategories[uint8(CategoryIdentifiers.LOWEST)].amountOfActiveExecutors;
        }
        return amountOfFittingExecutors;
    }

    function getInactiveExecutorByAddress(address executorAddress) public view returns (Executor memory) {
        return executorsCollection.inactiveExecutors[executorAddress];
    }

    function getBusyExecutorByAddress(address executorAddress) public view returns (Executor memory) {
        return executorsCollection.busyExecutors[executorAddress];
    }

    function getIndexAndCategoryOfActiveExecutorByAddress(address executorAddress) public view returns (uint, CategoryIdentifiers) {
        if (executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].activeIndexOf[executorAddress] != 0) {
            return (executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].activeIndexOf[executorAddress], CategoryIdentifiers.HIGHEST);
        } else if (executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].activeIndexOf[executorAddress] != 0) {
            return (executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].activeIndexOf[executorAddress], CategoryIdentifiers.STANDARD);
        } else if (executorsCollection.executorCategories[uint8(CategoryIdentifiers.LOWEST)].activeIndexOf[executorAddress] != 0) {
            return (executorsCollection.executorCategories[uint8(CategoryIdentifiers.LOWEST)].activeIndexOf[executorAddress], CategoryIdentifiers.LOWEST);
        } else {
            revert("This address does not belong to an active executor");
        }
    }

    function getExecutorStateByAddress(address executorAddress) public view returns (ExecutorState executorState) {
        if (executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].activeIndexOf[executorAddress] != 0 || 
            executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].activeIndexOf[executorAddress] != 0 ||
            executorsCollection.executorCategories[uint8(CategoryIdentifiers.LOWEST)].activeIndexOf[executorAddress] != 0) {
            return ExecutorState.ACTIVE;
        } else if (executorsCollection.inactiveExecutors[executorAddress].executorAddress == executorAddress) {
            return ExecutorState.INACTIVE;
        } else if (executorsCollection.busyExecutors[executorAddress].executorAddress == executorAddress) {
            return ExecutorState.LOCKED;
        } else {
            revert("This address does not belong to a registered executor");
        }
    } 

    function getExecutorByAddress(address executorAddress) public view returns (Executor memory executor) {  
        if (executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].activeIndexOf[executorAddress] != 0) {
            return executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].activeExecutors[executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].activeIndexOf[executorAddress]];
        } else if (executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].activeIndexOf[executorAddress] != 0) {
            return executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].activeExecutors[executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].activeIndexOf[executorAddress]];
        } else if (executorsCollection.executorCategories[uint8(CategoryIdentifiers.LOWEST)].activeIndexOf[executorAddress] != 0) {
            return executorsCollection.executorCategories[uint8(CategoryIdentifiers.LOWEST)].activeExecutors[executorsCollection.executorCategories[uint8(CategoryIdentifiers.LOWEST)].activeIndexOf[executorAddress]];
        } else if (executorsCollection.inactiveExecutors[executorAddress].executorAddress == executorAddress) {
            return executorsCollection.inactiveExecutors[executorAddress];
        } else if (executorsCollection.busyExecutors[executorAddress].executorAddress == executorAddress) {
            return executorsCollection.busyExecutors[executorAddress];
        } else {
            revert("This address does not belong to a registered executor");
        }
    }

    function getActiveExecutorByRelativeIndex(uint index, CategoryIdentifiers category) public view returns (Executor memory executor) {
        return executorsCollection.executorCategories[uint8(category)].activeExecutors[index];
    }

    function getActiveExecutorByRelativePosition(uint position, CategoryIdentifiers category) public view returns (Executor memory executor) {
        uint24 j = 0;
        for (uint24 i = 0; i < executorsCollection.executorCategories[uint8(category)].activeExecutors.length; i++) {  // i < executorsCollection.executorCategories[uint8(category)].amountOfActiveExecutors.amountOfActiveExecutors
            if (executorsCollection.executorCategories[uint8(category)].activeExecutors[i].executorAddress == address(0x0)) {
                continue;
            }
            if (j == position) {
                return executorsCollection.executorCategories[uint8(category)].activeExecutors[i];
            } else {
                j++;
            }
        }
        revert("Position exceeded number of available executors for category");
    }

    function getActiveExecutorByAbsolutePosition(uint position) public view returns (Executor memory executor) {
        if (position < executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].amountOfActiveExecutors) {
            return getActiveExecutorByRelativePosition(position, CategoryIdentifiers.HIGHEST);
        } else if (position > executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].amountOfActiveExecutors && position < (executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].amountOfActiveExecutors + executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].amountOfActiveExecutors)) {
            return getActiveExecutorByRelativePosition(position - executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].amountOfActiveExecutors, CategoryIdentifiers.STANDARD);
        } else {
            return getActiveExecutorByRelativePosition(position - (executorsCollection.executorCategories[uint8(CategoryIdentifiers.HIGHEST)].amountOfActiveExecutors + executorsCollection.executorCategories[uint8(CategoryIdentifiers.STANDARD)].amountOfActiveExecutors), CategoryIdentifiers.LOWEST);
        }
    }

    function getReferenceExecutionPowerPrice() public view returns (uint) {
        uint16 gasProportionality = 1;
        return ((tx.gasprice / gasProportionality) | 1); //TODO quizas agregar mas cosas aca, como el gas price, y el ratio de total available executors
    }

    // Open interaction functions

    function registerExecutor() public payable {
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
        require(getExecutorStateByAddress(msg.sender) == ExecutorState.ACTIVE, "This address does not belong to an active executor");
        bool transferSuccess = true;
        (uint executorIndex, CategoryIdentifiers category) = getIndexAndCategoryOfActiveExecutorByAddress(msg.sender);
        Executor memory executor = executorsCollection.executorCategories[uint8(category)].activeExecutors[executorIndex];
        if (withrawLockedFunds) {
            transferSuccess = _internalTransferFunds(executor.lockedWei, msg.sender);
            executor.lockedWei = 0;
        }
        executorsCollection.inactiveExecutors[msg.sender] = executor;
        delete executorsCollection.executorCategories[uint8(category)].activeExecutors[executorIndex];
        delete executorsCollection.executorCategories[uint8(category)].activeIndexOf[msg.sender];
        executorsCollection.executorCategories[uint8(category)].amountOfActiveExecutors--;
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

    function submitRequest(string memory inputState, string memory codeReference, uint amountOfExecutors, uint executionPowerPaidFor, uint256 randomSeed, CategoryIdentifiers executorCategory) public payable returns (uint) {
        referenceExecutionPowerPriceCache = getReferenceExecutionPowerPrice();
        require(amountOfExecutors % 2 == 1, "You must choose an odd amount of executors");
        require(amountOfExecutors <= MAXIMUM_EXECUTORS_PER_REQUEST, "You exceeded the maximum number of allowed executors per request");
        require(executionPowerPaidFor <= MAXIMUM_EXECUTION_POWER, "You exceeded the maximum allowed execution power per request");
        require(amountOfExecutors <= getAmountOfActiveExecutorsWithCriteria(executorCategory), "You exceeded the number of available executors that fit your criteria");
        require(msg.value == referenceExecutionPowerPriceCache * executionPowerPaidFor * amountOfExecutors, "The value sent in the request must be the execution power you intend to pay for multiplied by the price and the amount of executors");
        
        return _submitRequest(msg.sender, referenceExecutionPowerPriceCache, executionPowerPaidFor, inputState, codeReference, amountOfExecutors, randomSeed, executorCategory);
    }

    /*function rotateExecutors(uint requestID, uint256 randomSeed, CategoryIdentifiers category) public returns (bool transferSuccess) {
        uint initialGas = gasleft();
        require(requests[requestID].clientAddress == msg.sender, "You cant rotate a request that was not made by you");
        require(requests[requestID].submissionsLocked == false, "All executors for this request have already delivered");
        uint8 amountOfPunishedExecutors = 0;
        uint[] memory punishedExecutorsTaskIDs = new uint[](taskAssignmentsMap[requestID].length);  // Me van a quedar algunos en cero capaz, no importa
        for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
            if (!taskAssignmentsMap[requestID][i].submitted && block.timestamp >= (taskAssignmentsMap[requestID][i].timestamp + EXECUTION_TIME_FRAME_SECONDS)) {
                punishedExecutorsTaskIDs[amountOfPunishedExecutors++] = i;
            }
        }
        if (amountOfPunishedExecutors == 0) {
            return false;
        }
        //TODO check all uint types, google if they are cheaper, include in thesis
        uint24 amountOfAvailableExecutorsFittingCriteria = getAmountOfActiveExecutorsWithCriteria(category);
        uint24 effectiveAmountOfPunishedExecutors = amountOfAvailableExecutorsFittingCriteria > amountOfPunishedExecutors ? amountOfPunishedExecutors : amountOfAvailableExecutorsFittingCriteria;
        address[] memory punishedExecutorsAddresses = new address[](effectiveAmountOfPunishedExecutors);
        uint24 ceiling = amountOfAvailableExecutorsFittingCriteria;
        for (uint8 i = 0; i < effectiveAmountOfPunishedExecutors; i++) {  // Si la cantidad efectiva es menor a la cantidad total, solo roto los primeros
            uint taskIndex = punishedExecutorsTaskIDs[i];
            punishedExecutorsAddresses[i] = taskAssignmentsMap[requestID][taskIndex].executorAddress;
            taskAssignmentsMap[requestID][taskIndex].executorAddress = _getAndReserveActiveExecutorByAbsolutePosition(randomSeed % ceiling, requestID, i);
            taskAssignmentsMap[requestID][taskIndex].timestamp = block.timestamp;
            effectiveAmountOfPunishedExecutors++;
            randomSeed /= ceiling;
            ceiling--;
        }
        if (effectiveAmountOfPunishedExecutors == 0) {
            return false;
        }
        return _punishmentRound(requestID, PunishmentCase.REGULAR, initialGas, effectiveAmountOfPunishedExecutors, punishedExecutorsAddresses, 0);  // aca no hay refund porque se rotan? a menos que no haya suficientes, pero si no hay suficientes available se espera, no se rota asique no hay refund regardless
    }

    function truncateExecutors(uint requestID) public returns (bool transferSuccess) {
        uint initialGas = gasleft();
        require(requests[requestID].clientAddress == msg.sender, "You cant truncate a request that was not made by you"); //TODO test in python
        require(requests[requestID].submissionsLocked == false, "All executors for this request have already delivered");
        uint amountOfPunishedExecutors = 0;
        address[] memory punishedExecutorsAddresses = new address[](taskAssignmentsMap[requestID].length);
        for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
            if (!taskAssignmentsMap[requestID][i].submitted) {
                if (block.timestamp >= (taskAssignmentsMap[requestID][i].timestamp + EXECUTION_TIME_FRAME_SECONDS)) {
                    punishedExecutorsAddresses[amountOfPunishedExecutors++] = taskAssignmentsMap[requestID][i].executorAddress;
                    delete taskAssignmentsMap[requestID][i];
                    taskAssignmentsMap[requestID][i].submitted = true;  // Para que no obstruya la liberacion
                    taskAssignmentsMap[requestID][i].liberated = true;  // Para que no obstruya el cierre
                } else {
                    revert("There are still some unexpired executors who have not delivered"); //TODO test in python. Esto seria si los trunca de entrada, o si primero los rota y despues los trunca rapido, testear ambos casos
                }
            }
        }
        require(taskAssignmentsMap[requestID].length > amountOfPunishedExecutors, "You can only truncate executors if there has been at least one submission");
        if (amountOfPunishedExecutors == 0) {
            return false;
        }

        requests[requestID].submissionsLocked = true; //TODO test in python
        
        uint refundAmount = requests[requestID].executionPowerPrice * requests[requestID].executionPowerPaidFor * amountOfPunishedExecutors; // porque en close request solo hago refund por los marcados pero no los truncados
        return _punishmentRound(requestID, PunishmentCase.REGULAR, initialGas, amountOfPunishedExecutors, punishedExecutorsAddresses, refundAmount);
    }*/

    //TODO fijarse que capaz un ejecutor truncado o un ejecutor marcado capaz todavia puede submitear o liberar????? mirar que onda las banderas y los index cacheados en el executor en si
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

    function liberateResult(uint requestID, Result memory result) public returns (bool) {
        uint initialGas = gasleft();
        Executor memory executor = getExecutorByAddress(msg.sender);
        require(requests[requestID].closed == false, "This request has already been closed"); //TODO test in python
        require(executor.assignedRequestID == requestID, "You must be assigned to the provided request to liberate the result");
        require(taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].submitted == true, "You must first submit a signed result hash before you can liberate it");
        require(requests[requestID].submissionsLocked == true, "You must wait until all submissions for this request have been locked");
        require(taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].liberated == false, "The result for this request, for this executor, has already been liberated");        
        // TODO test in python
        require(result.issuer == msg.sender, "The issuer of the sent result does not match the transaction sender");
        
        bool hashMatched;
        if (keccak256(abi.encode(result)) == taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].signedResultHash) {
            hashMatched = true;
            result.issuer = address(this);    
            taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].unsignedResultHash = keccak256(abi.encode(result));
            taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].result = result;
        } else {
            hashMatched = false;
            // Dejo el result.issuer en cero, forzando un castigo al ser ignorado por el majority detector en _closeRequest. Este castigo es peor que ser truncado como ejecutor
        }
        taskAssignmentsMap[executor.assignedRequestID][executor.taskAssignmentIndex].liberated = true;

        bool lastOne = true;
        for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
            if (!taskAssignmentsMap[requestID][i].liberated) {
                lastOne = false;
                break;
            }
        }
        if (lastOne) { // TODO Hacer que el cliente ponga una prima para devolverle el gas al ultimo ejecutor en liberar, que es el que paga toda esta logica extra. El resto debe estar contemplado en el pago. TAMBIEN DEVOLVER DICHA PRIMA AL FINAL DE ESTA FUNCION, SI Y SOLO SI EL ULTIMO FUE ACCURATE, naah mejor devolver la prima siempre. Hacer que la prima sea bastante grande, y se le devuelve la diferencia al cliente
            uint markedCount = 0;
            uint nonTruncatedExecutors = 0;
            address[] memory executorsMarked = new address[](taskAssignmentsMap[requestID].length);  // Para los castigos de aca y de close, uso address[] en vez de taskAssignmentIDs porque ya no me interesa el task assignment, ya que la request se va a cerrar
            for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
                if (taskAssignmentsMap[requestID][i].executorAddress != address(0x0)) {
                    nonTruncatedExecutors++;
                    if (taskAssignmentsMap[requestID][i].result.issuer == address(0x0)) {
                        executorsMarked[markedCount++] = taskAssignmentsMap[requestID][i].executorAddress;
                    }
                }
            }
            if (markedCount < nonTruncatedExecutors) {  // if there is at least one valid submission
                _closeRequest(requestID, initialGas);
            } else {  // markedCount == nonTruncatedExecutors meaning all non truncated executors submitted an invalid hash, so, no valid submissions found
                _recycleRequest(requestID, initialGas, markedCount, executorsMarked);
            }
        }
        return hashMatched;
    }

    /*function forceResultLiberation(uint requestID) public {
        uint initialGas = gasleft();
        require(requests[requestID].closed == false, "This request has already been closed"); //TODO test in python
        require(requests[requestID].clientAddress == msg.sender, "You cant force the liberation of a request that was not made by you"); //TODO test in python
        require(requests[requestID].submissionsLocked == true, "There are still executors who have not posted their results");
        //TODO check at least one liberated
        //maybe once submissionsLocked is set to true, I need a submissionsLocked timestamp to check if i can truncateliberation yet or not TODO
        
        uint amountOfValidSubmissions = 0;
        for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
            if (taskAssignmentsMap[requestID][i].result.issuer == address(0x0)) {
                taskAssignmentsMap[requestID][i].liberated = true;  // Los libero pero les dejo el resultado en cero, forzando el castigo en close request
            } else {
                amountOfValidSubmissions++;
            }
        }
        require(amountOfValidSubmissions < taskAssignmentsMap[requestID].length, "There must be at least one valid liberated result");
        _closeRequest(requestID, initialGas);
    }*/

    //TODO puedo hacer que el precio del executionpower sea inversamente proporsional a la cantidad de ejecutores activos, uso tx.gasprice? YA CONFIRME QUE SI EXISTE
    // Private Functions

    function _getAndReserveActiveExecutorByAbsolutePosition(uint position, uint requestID, uint8 taskAssignmentIndex) private returns (address) {
        address executorAddress = getActiveExecutorByAbsolutePosition(position).executorAddress;
        _lockExecutor(executorAddress, requestID, taskAssignmentIndex);
        return executorAddress;
    }

    function _recycleRequest(uint requestID, uint initialGas, uint markedCount, address[] memory executorsMarked) private {
        uint refundAmount = 0;
        requests[requestID].closed = true;
        emit requestClosed(requestID, 0);
        emit requestRecycled(requestID);
        if (getAmountOfActiveExecutorsWithCriteria(CategoryIdentifiers.LOWEST) >= taskAssignmentsMap[requestID].length) {
            _submitRequest(requests[requestID].clientAddress, requests[requestID].executionPowerPrice, requests[requestID].executionPowerPaidFor, requests[requestID].inputState, requests[requestID].codeReference, taskAssignmentsMap[requestID].length, uint256(blockhash(block.number-1)), CategoryIdentifiers.LOWEST);
        } else {
            refundAmount = requests[requestID].executionPowerPrice * requests[requestID].executionPowerPaidFor * markedCount;
        }
        _punishmentRound(requestID, PunishmentCase.INACCURATE_SOLVING, initialGas, markedCount, executorsMarked, refundAmount);
    }

    function _submitRequest(address clientAddress, uint executionPowerPrice, uint executionPowerPaidFor, string memory inputState, string memory codeReference, uint amountOfExecutors, uint256 randomSeed, CategoryIdentifiers executorCategory) private returns (uint) {
        Request memory request = Request({
            id: requests.length,
            clientAddress: clientAddress,
            executionPowerPrice: executionPowerPrice,
            executionPowerPaidFor: executionPowerPaidFor,
            inputState: inputState,
            codeReference: codeReference,
            result: Result({
                data: '',
                issuer: address(0x0)
            }),
            submissionsLocked: false,
            closed: false
        });
        requests.push(request);
        TaskAssignment[] storage taskAssignments = taskAssignmentsMap[request.id];
        uint24 ceiling = getAmountOfActiveExecutorsWithCriteria(executorCategory);
        for (uint8 i = 0; i < amountOfExecutors; i++) {
            taskAssignments.push(TaskAssignment({
                executorAddress: _getAndReserveActiveExecutorByAbsolutePosition(randomSeed % ceiling, request.id, i),
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
            randomSeed /= ceiling;
            ceiling--;
        }
        emit requestCreated(request.id, clientAddress);
        return request.id;
    }

    function _closeRequest(uint requestID, uint initialGas) private {
        bytes32[] memory hashes = new bytes32[](taskAssignmentsMap[requestID].length);
        uint8[] memory indexes = new uint8[](taskAssignmentsMap[requestID].length);
        uint8[] memory appearences = new uint8[](taskAssignmentsMap[requestID].length);
        for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
            if (taskAssignmentsMap[requestID][i].result.issuer == address(0x0)) {  // Estos son los truncados o marcados para ser castigados
                continue;
            }
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
        for (uint8 i = 0; i < appearences.length; i++) {
            if (appearences[i] > appearences[appearenceIndexOfMaximum]) {  // Si hay empate, que gane el primero
                appearenceIndexOfMaximum = i;
                assignmentIndexOfMaximum = indexes[i];
            }
        }
        // Jamas se deberia dar que haya cero appearrances de todos, por el chequeo de validSubmissionsPresent

        // Result posting
        requests[requestID].result = taskAssignmentsMap[requestID][assignmentIndexOfMaximum].result;
        requests[requestID].closed = true;
        emit requestClosed(requestID, appearences[appearenceIndexOfMaximum]);

        // Punishments and payments
        address[] memory executorsToBeRewarded = new address[](appearences[appearenceIndexOfMaximum]);
        uint8 rewardedCount = 0;
        address[] memory executorsToBePunished = new address[](taskAssignmentsMap[requestID].length - appearences[appearenceIndexOfMaximum]);
        uint8 punishedCount = 0;
        for (uint8 i = 0; i < taskAssignmentsMap[requestID].length; i++) {
            if (taskAssignmentsMap[requestID][i].unsignedResultHash == hashes[appearenceIndexOfMaximum]) {
                executorsToBeRewarded[rewardedCount++] = taskAssignmentsMap[requestID][i].executorAddress;
            } else if (taskAssignmentsMap[requestID][i].executorAddress != address(0x0)) {  // Aca gracias a esta condicion agarro a los marcados para punished pero no a los truncados
                executorsToBePunished[punishedCount++] = taskAssignmentsMap[requestID][i].executorAddress;
            }
        }

        uint individualPayAmount = requests[requestID].executionPowerPaidFor * requests[requestID].executionPowerPrice;
        for (uint8 i = 0; i < rewardedCount; i++) {
            _internalTransferFunds(individualPayAmount, executorsToBeRewarded[i]);
            executorsCollection.busyExecutors[executorsToBeRewarded[i]].accurateSolvings++;
            _unlockExecutor(executorsToBeRewarded[i]);
        }

        if (punishedCount > 0) {
            uint refundAmount = requests[requestID].executionPowerPaidFor * requests[requestID].executionPowerPrice * punishedCount;
            _punishmentRound(requestID, PunishmentCase.INACCURATE_SOLVING, initialGas, punishedCount, executorsToBePunished, refundAmount);
        }
    }

    function _punishmentRound(uint requestID, PunishmentCase punishmentCase, uint initialGas, uint punishedCount, address[] memory executorsToBePunished, uint refundAmount) private returns (bool transferSuccess) {
        uint loopGasOverhead;
        if (punishmentCase == PunishmentCase.INACCURATE_SOLVING) {
            loopGasOverhead = 1; // TODO lo puedo hacer constante regardless del caso?
        } else {  // PunishmentCase.REGULAR
            loopGasOverhead = 1; // TODO
        }
        uint constantGasOverhead = 12345; // TODO
        uint estimatedGasSpent = ((initialGas - gasleft()) + ((PUNISH_GAS + loopGasOverhead) * punishedCount) + constantGasOverhead) * tx.gasprice;  // This is just an aproximation, make it generous to favor the client
        uint punishAmount = estimatedGasSpent / punishedCount;
        for (uint8 i = 0; i < punishedCount; i++) {
            // update reputation
            if (punishmentCase == PunishmentCase.INACCURATE_SOLVING) {
                executorsCollection.busyExecutors[executorsToBePunished[i]].inaccurateSolvings++;
            }
            _punishExecutor(executorsToBePunished[i], punishAmount);
        }
        return _internalTransferFunds((punishAmount * punishedCount) + refundAmount, requests[requestID].clientAddress);
    }

    function _punishExecutor(address executorAddress, uint punishAmount) private {
        require(executorsCollection.busyExecutors[executorAddress].executorAddress == executorAddress, "You can only punish a locked executor");
        Executor memory executor = executorsCollection.busyExecutors[executorAddress];
        executor.lockedWei -= punishAmount;
        executor.timesPunished += 1;
        executor.assignedRequestID = 0;
        executor.taskAssignmentIndex = 0;
        executorsCollection.inactiveExecutors[executorAddress] = executor;
        delete executorsCollection.busyExecutors[executorAddress];
        emit executorPunished(executorAddress);
    }

    function _lockExecutor(address executorAddress, uint requestID, uint taskAssignmentIndex) private {
        require(getExecutorStateByAddress(executorAddress) == ExecutorState.ACTIVE, "This address does not belong to an active executor");
        (uint executorIndex, CategoryIdentifiers category) = getIndexAndCategoryOfActiveExecutorByAddress(executorAddress);
        Executor memory executor = executorsCollection.executorCategories[uint8(category)].activeExecutors[executorIndex];
        executor.assignedRequestID = requestID;
        executor.taskAssignmentIndex = taskAssignmentIndex;
        executorsCollection.busyExecutors[executorAddress] = executor;
        delete executorsCollection.executorCategories[uint8(category)].activeExecutors[executorIndex];
        delete executorsCollection.executorCategories[uint8(category)].activeIndexOf[executorAddress];
        executorsCollection.executorCategories[uint8(category)].amountOfActiveExecutors--;
        executorsCollection.amountOfActiveExecutors--;
        emit executorLocked(executorAddress);
    }

    function _unlockExecutor(address executorAddress) private {
        require(executorsCollection.busyExecutors[executorAddress].executorAddress == executorAddress, "This address does not belong to a locked executor");
        executorsCollection.busyExecutors[executorAddress].assignedRequestID = 0;
        executorsCollection.busyExecutors[executorAddress].taskAssignmentIndex = 0;
        _activateExecutor(executorsCollection.busyExecutors[executorAddress]);
        delete executorsCollection.busyExecutors[executorAddress];
        emit executorUnlocked(executorAddress);
    }

    function _activateExecutor(Executor memory executor) private {
        CategoryIdentifiers category = getExecutorCategory(executor);
        require(executorsCollection.executorCategories[uint8(category)].activeIndexOf[executor.executorAddress] == 0, "This address is already registered as an active executor");
        uint24 executorIndex;
        for (executorIndex = 1; executorIndex < executorsCollection.executorCategories[uint8(category)].activeExecutors.length; executorIndex++) {
            if (executorsCollection.executorCategories[uint8(category)].activeExecutors[executorIndex].executorAddress == address(0x0)) {
                break;
            }
        }
        if (executorIndex == executorsCollection.executorCategories[uint8(category)].activeExecutors.length) {
            executorsCollection.executorCategories[uint8(category)].activeExecutors.push(executor);
        } else {
            executorsCollection.executorCategories[uint8(category)].activeExecutors[executorIndex] = executor;
        }
        executorsCollection.executorCategories[uint8(category)].activeIndexOf[executor.executorAddress] = executorIndex;
        executorsCollection.executorCategories[uint8(category)].amountOfActiveExecutors++;
        executorsCollection.amountOfActiveExecutors++;
    }
}