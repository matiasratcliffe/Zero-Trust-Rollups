# aca hago las funciones para interactuar con los contratos ya corriendo, lo primero que corro son las cosas de setup
#from scripts.setup import get_account, setup_contracts
from brownie import ClientImplementation, ExecutionBroker, network, accounts
from scripts.entities.contract.client import Client
from scripts.entities.contract.broker import Broker
import code;


def main():
    broker = Broker()
    client = Client.create(accounts[0], broker)
    print(f"Client address: {client.instance.address}")
    #clientRetrieved = Client.getInstance()
    
    code.interact(local=dict(globals(), **locals()))

if __name__ == "__main__":
    main()
