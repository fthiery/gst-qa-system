# GStreamer QA system
#
#       tests/scenario/gstmediatest.py
#
# Copyright (c) 2007, Edward Hervey <bilboed@bilboed.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Scenario simulating the behaviour of the historical gst-media-test scenarios
"""

from insanity.scenario import Scenario
from insanity.monitor import GstDebugLogMonitor

class GstMediaTestScenario(Scenario):
    """
    This is a scenario that will attempt to run the given test.
    If it doesn't reach 100% succes, it will be re-run with more aggressive
    monitoring.

    It automatically adds the correct monitors to the underlying tests, or
    sets the right parameter for tests that have default monitor.

    This reproduces the re-try behaviour of gst-media-test
    """

    __test_name__ = "GstMediaTestScenario"
    __test_description__ = """
    Re-runs failed subtests with higher debug level
    """
    __test_arguments__ = {
        "subtest-class": ( "TestClass to run", None, None ),
        "debug-level-1": ( "GST_DEBUG specification to use on first run",
                           "*:2", None ),
        "debug-level-2": ( "GST_DEBUG specification to use on second run",
                           "*:5", None )
        }
    __test_checklist__ = {
        "similar-results":"were the results similar over the two runs"
        }

    def setUp(self):
        if not Scenario.setUp(self):
            return False
        # add the initial test
        subtest = self.arguments.get("subtest-class")
        debuglevel = self.arguments.get("debug-level-1", "*:2")
        if not subtest:
            return False
        self.addSubTest(subtest, self.arguments,
                        [(GstDebugLogMonitor, {"debug-level": debuglevel})
                         ])
        return True

    def subTestDone(self, test):
        if len(self.tests) == 2:
            if test.getSuccessPercentage() == self.tests[0].getSuccessPercentage():
                self.validateStep("similar-results")
            return True
        if not test.getSuccessPercentage() == 100.0:
            subtest = self.arguments.get("subtest-class")
            debuglevel = self.arguments.get("debug-level-2", "*:5")
            self.addSubTest(subtest, self.arguments,
                            [(GstDebugLogMonitor, {"debug-level": debuglevel})
                             ])
        else:
            self.validateStep("similar-results")
        return True

