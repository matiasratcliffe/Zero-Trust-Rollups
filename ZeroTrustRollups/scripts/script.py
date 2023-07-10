from brownie import APIConsumer, accounts


from scripts.classes.utils.contractProvider import BrokerFactory, APIProviderFactory
from scripts.classes.APIProvider import APIProvider

broker = BrokerFactory.getInstance()
apiProvider = APIProviderFactory.getInstance()
apiConsumer = APIConsumer.deploy(broker.address, apiProvider.address, {"from": accounts[0]})

apiProvider = APIProvider()
api = apiProvider.registerAPI(accounts.add(), "MOCK")
apiResponse = api.getSignedResponse()


