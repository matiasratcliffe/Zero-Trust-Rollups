from scripts.classes.utils.logger import Logger
from scripts.classes.utils.contractProvider import APIProviderFactory, APIConsumerFactory, BrokerFactory
from scripts.classes.utils.accountsManager import Accounts
from scripts.classes.APIProvider import APIProvider, APIOracle, MockAPI
from scripts.classes.APIConsumer import APIConsumer
from scripts.classes.utils.logger import Logger


class TestAPIs:
    def setup(self):
        pass

    def teardown(self):
        pass

    def setup_method(self, method):
        Logger.logIndentation=0

    def teardown_method(self, method):
        pass

    def test_api_oracle(self):
        apiIdentifier = "MOCK"
        apiConsumer   = APIConsumer(APIConsumerFactory.getInstance())
        apiProvider   = APIProvider(APIProviderFactory.getInstance())
        apiOracle     = APIOracle(BrokerFactory.getInstance(), APIProviderFactory.getInstance(), Accounts.getAccount())
        apiProvider.registerAPI(Accounts.addLocalAccount(), apiIdentifier)

        reqID = apiConsumer.createRequest([apiIdentifier], funds=1e14)
        apiWrong = MockAPI(Accounts.addLocalAccount(), "WRONG", "{bytes response; bytes signature;}")
        apiRight = MockAPI(Accounts.getFromIndex(10), "MOCK", "{bytes response; bytes signature;}")
        apiOracle._acceptRequest(reqID)
        assert apiOracle._submitResult(reqID, apiWrong.getSignedResponse()) == False
        apiOracle._acceptRequest(reqID)
        assert apiOracle._submitResult(reqID, apiRight.getSignedResponse()) == True

    def notest2(self):
        #apiOracle._resolveRequest(reqID)
        pass    
