from scripts.classes.utils.logger import Logger


class TestExecutor:
    def setup_method(self, method):
        Logger.logIndentation=0

    def teardown_method(self, method):
        pass

    def test_creation(self):
        pass

    # TODO tests de ExecutionBroker y de executor (comportamiento de los buffers y eventos)