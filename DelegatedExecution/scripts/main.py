from scripts.classes.auxiliar.accountsManager import AccountsManager
from scripts.classes.contracts import ClientFactory
from scripts.classes.executor import Executor
import code;


def main():
    client = ClientFactory.getInstance()
    request = client.createRequest(client.encodeInput(1, [10]), funds=10)
    executor = Executor(AccountsManager.getAccount(), client.broker)
    client.broker.acceptRequest(request.id, executor.account) ## TODO actually I wouldnt do this here, I need a function in executor that runs one round of scan for open requests and accepts it
    result = executor.computeResult(request.id)
    print(result)
    code.interact(local=dict(globals(), **locals()))

if __name__ == "__main__":
    main()
