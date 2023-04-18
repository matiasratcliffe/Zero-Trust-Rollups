//programacion
//estructura de datos
//seguridad y criptografia
//economia de la empresa

//Titulo: Off-chain delegated code execution for on-chain code

//Objetivo: El objetivo es plantear una alternativa a la ejecucion directa de codigo en blockchains basadas en el protocolo ethereum, valiendose de oraculos y un sistema de incentivos financieros para reducir el costo de la ejecucion de dicho codigo.

// es un optimistic rollup? comparar con optimism y otras cosas existentes (es diferente porque lo mio esta pensado para alquiler de computo, no simplemente como metodo ahorrativo para dapps)

//Analizar las alternativas de ejecucion hoy en dia (local, cloud, blockchain, voluntary computing, ICP?), y exponer virtudes y defectos en cada uno, y una esperanza de en lo que este trabajo podria llegar a culminar
//Proponer un modelo de ejecucion de codigo con resultados onchain pero ejecucion offchain, reduciendo el costo de gas

//El objetivo no es crear un servicio competitivo a nivel mercado, sino mas bien explorar las posibilidades tecnicas de la tecnologia blockchain y los smart contracts

// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;


contract DelegatedExecution {

    // CUIDADO https://solidity-by-example.org/hacks/re-entrancy/

    //struct FuncInput {} // TANTO INITIAL STATE COMO PARAMS DEBERIAN SER UNA CADENA DE BYTES DONDE LOS DATOS ESTEN CODIFICADOS. DEPENDE DEL CLIENTE QUE DECIDE PONER EN CADA UNO, PUEDE EMPAQUETAR TODO EN UNO SOLO Y DEJAR TODO VACIO PERO LA IDEA ES QUE EN STATE CODIFIQUE UN STRUCT QUE ESTE GUARDADO EN SU CONTRATO, Y EN PARAMS QUE SIMPLEMENTE SEAN PARAMETROS PROPUESTOS POR EL OFERENTE (AHI PODRIA CODIFICARSE LOS IDs DE LAS SUBFUNCIONES A EJECUTARSE EN ESA CORRIDA
    
    //Que el cliente tenga una funcion para hacer oferta!!!!!!!!!!!

    //FuncState public state; // NO PUEDE HABER ESTADO YA QUE ESO VA EN CONTRA DEL DETERMINISMO DE LA FUNCION PURE

    // Fijo pero revisar si hace falta cambiar (Persistir initial state para que el check sea determinista?)
    //event funcTransacted(uint256 timestamp, uint256 offerID, address indexed issuer, FuncInput input, FuncState state);
	// one event per broker interaction?

	// Client Logic

    // Depende del cliente
    // Que el cliente overridee esta y ahi haga una cadena de ifs y en la data de input ponga un valor para que se elija la funcion a ejecutarse. Es importante que se overridee esta y no usar simplemente encodewithselector porque tiene que ser una funcion "pure"
    //function funcLogic(FuncInput calldata input) public pure returns (FuncState memory finalState) {return finalState;} 

    // cambiar nombre a stateMap?
    // NO FIJO (y en el cliente) ya que el cliente puede optar por transformarla en una funcion vacia y mantener un estado implicito
    function funcMap() private {}

    // TODO ver que onda el tema de si una ejecucion antigua resulta ser mala. o tema de manipulacion (SI LA EJECUCION ANTIGUA ES MALA Y PASO EL TIEMPO, A MAMARLA. LO UNICO QUE SE PUEDE CORROBORAR AL SOLIDIFICAR UN REQUEST ES SI EL RESULTADO SE PUEDE DECODIFICAR A CIERTO STRUCT)
    // HACER QUE AL SOLIDIFICAR UNA FUNCION SE LLAME A UNA FUNCION QUE EN BASE CLIENT VA A SER VIRTUAL. ESTA SE PUEDE USAR PARA REGISTRAR OTRA PETICION EN BASE A LOS RESULTADOS, Y SI NO FUNCIONA, QUE SE JODA EL CLIENTE
}

// Otro mecanismo para evitar los challenges is que sea 100% democratic trust, seria que los ejecutores se registren en el broker,
// y el broker vaya dispatcheando trabajos, para cada oferta, el cliente provee una clave publica (de un par descartable, aunque se
// guarda la privada hasta el fin del proceso), y el broker le dispatchea el job a 3 (o N elegido por el cliente) ejecutores.
// Los ejecutores submitean el encrypt(pubKeyDescartable,concat(resultado,executerAddress)) [lo del concat es para que nadie copie
// el encryptado]. aca ver si poner un rango de tiempo despues del cual el cliente puede cancelar la oferta si no estan todos los
// resultados (para eso limitar el N de ejecutores, porque si el cliente pone 1000 ejecutores, obvio que no va a estar y puede
// retirarse. pensandolo mejor, que si por lo menos 3 ejecutores submitearon, que el cliente no se pueda retirar?) ver punishment
// para ejecutores lentos. el punishment para ejecutores incorrectos es el gas que pagan para submitear (y reputacion que le baja la
// prioridad de ser seleccionados?). cuestion, una vez estan todos los submit, el cliente revela la private key (usar escrow logic de
// fondos lockeados para que el cliente no se haga el rata) y ahi ver cual es la moda en los resultados y tomar ese, repartiendo la
// prima entre los buenos ejecutores
// una mejora que puede tener este es que solo se publiquen los hashes del codigo y una referencia o alguna forma super comprimida del
// codigo, asi deployar ClientImplementation no es tan caro. Es mas, capaz que ni hace falta una clase client, y puedo tomar varios
// lenguajes de programacion... PENSALDOLO MEJOR, TIENE QUE SER DETERMINISTA EL RESULTADO, ASIQUE CUIDADO CON ESO
// Ooooo, podria ser que dependa del ejecutor darse cuenta si la funcion es determinista o no, y en base a eso aceptar o no, pero eso me
// forzaria a cambiar el sistema de dispatch por un sistema de oferta y demanda (parecido al primer modelo).
// Hacer que la ejecucion sea en 2 partes sino: primero la parte determinista, que se submitea, y segundo, en base al resultado, la parte
// de calls a apis, etc, tipo con oraculos o incluso submitear otro job. la estructura de return del determinista puede ser:
// { 
//      data: bytes,
//      oracleCalls: [...],
//      contractCalls: [...]
// }
// y eso submitean los ejecutores, y despues depende del cliente ejecutar la funcion "procesarResultado" que hace las oracle calls (plug api registration with double key) y las
// contract calls OnChain. Aca ver que onda con las contract calls ejecutadas en "procesarResultado" vs la RequestChain nativa del baseClient

// TODO hacer contrato executor, ya para la segunda parte
// la segunda parte me saca la necesidad de el gas massive challenge
// la tercera parte me saca la necesidad de multiples executors, dando nacimiento a los Zero Trust rollups