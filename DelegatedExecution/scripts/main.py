from scripts.classes.accountsManager import AccountsManager
from scripts.classes.contractProvider import ClientFactory
from scripts.classes.requestor import Requestor
from scripts.classes.executor import Executor
from scripts.logger import Logger
from time import sleep
import code


def main():
    Logger.log("------------------- New Execution -------------------", raw=True)
    clientContract = ClientFactory.getInstance()
    requestor = Requestor(clientContract)
    executor = Executor(AccountsManager.getAccount(), clientContract.brokerContract(), True)
    requestor.createRequest(functionToRun=1, dataArray=[10], funds=10)
    sleep(2)
    executor.solverLoopRound()
    sleep(2)
    Logger.log("-----------------------------------------------------", raw=True)
    code.interact(local=dict(globals(), **locals()))


if __name__ == "__main__":
    main()
