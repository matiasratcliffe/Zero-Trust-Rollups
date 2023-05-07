from brownie import ExecutionBroker, config, network
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.utils.logger import Logger


@Logger.LogClassMethods()
class BrokerFactory:
    DEFAULT_EXECUTION_TIME_FRAME = 10
    BASE_STAKE_AMOUNT = 1e6
    MAXIMUM_EXECUTION_POWER_ALLOWED = 10000
    MAXIMUM_NUMBER_OF_EXECUTORS_ALLOWED = 5

    def getInstance():
        if "brokerContractAddress" in config["networks"][network.show_active()]:
            return BrokerFactory.at(address=config["networks"][network.show_active()]["brokerContractAddress"])
        elif (BrokerFactory.count() > 0):
            return BrokerFactory.at(index=-1)
        else:
            return BrokerFactory.create(Accounts.getAccount())

    def create(account=None):
        if account == None:
            account = Accounts.getAccount()
        ExecutionBroker.deploy(
            BrokerFactory.DEFAULT_EXECUTION_TIME_FRAME,
            BrokerFactory.BASE_STAKE_AMOUNT,
            BrokerFactory.MAXIMUM_EXECUTION_POWER_ALLOWED,
            BrokerFactory.MAXIMUM_NUMBER_OF_EXECUTORS_ALLOWED,
            {"from": account},
            publish_source=config["networks"][network.show_active()]["verify"]
        )
        return BrokerFactory.at(index=-1)
    
    def at(index=None, address=None):
        if address and not index:
            return ExecutionBroker.at(address)
        if index and not address:
            return ExecutionBroker[index]
        raise "This method requires 1 keyValue parameter (address XOR index)"

    def count():
        return len(ExecutionBroker)