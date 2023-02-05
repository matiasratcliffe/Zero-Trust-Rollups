from scripts.classes.auxiliar.accountsManager import AccountsManager
from scripts.classes.contracts import ClientFactory
from scripts.classes.executor import Executor
import code;
from time import sleep
from scripts.logger import Logger

from brownie.network.event import EventWatcher

def main():
    Logger.log("------------------- New Execution -------------------", raw=True)
    client = ClientFactory.getInstance()
    executor = Executor(AccountsManager.getAccount(), client.broker, True)
    client.createRequest(client.encodeInput(1, [10]), funds=10)
    sleep(2)
    executor.solverLoopRound()
    sleep(2)
    Logger.log("-----------------------------------------------------", raw=True)
    code.interact(local=dict(globals(), **locals()))

def callbackfunc(data):
    print(f"Callback called: {str(data)}")

if __name__ == "__main__":
    main()
