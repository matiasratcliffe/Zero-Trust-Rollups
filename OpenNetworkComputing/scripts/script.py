from brownie import ExecutionBroker, accounts


def deploy():
    ExecutionBroker.deploy({"from": accounts[0]})

