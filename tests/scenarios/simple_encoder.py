import os.path

from insanity.scenario import Scenario
from insanity.monitor import GstDebugLogMonitor

from tests.simple_encoder import SimpleEncoderTest

class SimpleEncoderScenario(Scenario):

    __test_name__ = "simple-encoder-scenario"
    __test_description__ = "Scenario for multiple video encoder tests"

    def setUp(self):
        if not Scenario.setUp(self):
            return False

        self.addSubTest(SimpleEncoderTest, {"codec":"theora"})
        self.addSubTest(SimpleEncoderTest, {"codec":"schro"})

        return True

    def subTestDone(self, test):
        return True

