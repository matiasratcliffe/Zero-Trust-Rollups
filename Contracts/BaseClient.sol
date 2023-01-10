// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

abstract contract BaseClient {

    struct ClientInput {
        uint functionToRun;
        bytes data;
    }

    constructor() {
        // aca linkear con Broker hardcoded?
    }

    function clientLogic(bytes calldata input) public virtual pure returns (bytes memory);
    // ver forma de mapear o hacer cadena? (es decir que una ejecucion resulte en otra oferta? se puede manteniendo el determinismo??? quizas agregar una opcion bool para una nueva registracion post sumision/solidificacion (extra payment?)

    //hacer el register aca? o medio lio porque habria que pasamanear fondos?

    //re register chain offer

    // que el cliente tenga una funcion para hacer oferta, y que se base en los fondos que ya tenga el contrato cliente, y que, al ser una funcion de la que egresan fondos, solo pueda ser llamada por el owner del contrato cliente, o por el broker (ambas addresses hardcodeadas en el constructor)

}