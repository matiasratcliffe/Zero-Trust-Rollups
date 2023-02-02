from brownie import (
    config,
    network,
    accounts,
    ExecutionBroker,
    ClientImplementation
)
## aca hacer todo lo que sea get accounts o get contracts, osea, get handles con la plataforma y comunicacion con el rpc (deploy si es necesario)


def setup_contracts():
    account = get_account(0)
    def deployClient():
        ClientImplementation.deploy(
            ExecutionBroker[-1].address,
            {"from": account}
        )
    def deployBroker():
        ExecutionBroker.deploy(
            {"from": account},
            #publish_source=config["networks"][network.show_active()].get("verify", False)
        )

    if (len(ExecutionBroker) == 0):
        deployBroker()
        deployClient()
    elif (len(ClientImplementation) == 0):
        deployClient()