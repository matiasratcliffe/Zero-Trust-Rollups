from brownie import ExecutionBroker, accounts


def deploy():
    ExecutionBroker.deploy({"from": accounts[0]})
    return ExecutionBroker[-1]

def testRand(broker, floor, ceil, rounds=100, numbers=5):
    appearences = {}
    for i in range(floor, ceil):
        appearences[i] = 0
    for i in range(rounds):
        result = broker.getRandomNumbers(numbers, floor, ceil, {"from": accounts[0]}).return_value
        if result != None:
            for r in result:
                appearences[r] += 1
    return appearences