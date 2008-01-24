# GStreamer QA system
#
#       scenario.py
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

import gobject
from test import Test
from log import critical, error, warning, debug, info

class Scenario(Test):
    """
    Test that runs other tests with optional programmatic decisions
    and result processing.
    """
    __test_name__ = "scenario"
    __test_description__ = """Base class for scenarios"""
    __test_timeout__ = 600 # 10 minutes because the subtests will handle themselves

    # TODO :
    #  auto-aggregation of arguments, checklists and extra-info
    #  Scenario might want to add some arguments, checks, extra-info ?
    #  arg/checklist/extra-info names might need to be prefixed ?
    #    Ex : <test-name>-<nb>-<name>
    #  Override timeout !

    # implement methods to:
    # * decide which test should be run first
    # * what should be done when a test is done

    # Test methods overrides

    def setUp(self):
        if not Test.setUp(self):
            return False
        self._tests = [] # list of (test, args, monitors)
        self.tests = [] # executed tests

        # FIXME : asynchronous starts ???
        return True

    def tearDown(self):
        # FIXME : implement this for the case where we are aborted !
        pass

    def test(self):
        # get the first test to run
        self._startNextSubTest()

    def getSuccessPercentage(self):
        if not self.tests:
            return 0.0
        res = reduce(lambda x, y: x+y, [z.getSuccessPercentage() for z in self.tests]) / len(self.tests)
        return res

    # private methods

    def _startNextSubTest(self):
        try:
            testclass, args, monitors = self._tests.pop(0)
            debug("About to create subtest %r with arguments %r", testclass, args)
            instance = testclass(testrun=self._testrun,
                                 bus = self.arguments["bus"],
                                 **args)
        except Exception, e:
            warning("Failed to create instance of class %r : %r", testclass, e)
            self.stop()
            return
        # connect to signals
        self.tests.append(instance)
        instance.connect("done", self._subTestDoneCb)
        instance.run()
        # returning False so that idle_add() doesn't call us again
        return False

    # sub-test callbacks
    def _subTestDoneCb(self, subtest):
        debug("Done with subtest %r", subtest)
        carryon = self.subTestDone(subtest)
        if carryon and len(self._tests) > 0:
            # startup the next test !
            debug("Carrying on with next test")
            gobject.idle_add(self._startNextSubTest)
        else:
            debug("No more subtests to run, stopping")
            self.stop()

    # overridable methods

    def setNextSubTest(self, testclass, arguments, monitors):
        """
        testclass : a testclass to run next, can be a Scenario
        arguments : dictionnary of arguments
        monitors : list of Monitor to run the test with

        This method can be called several times in a row at any moment.
        """
        # filter out unused arguments in arguments
        args = {}
        for validkey in testclass.getFullArgumentList():
            args[validkey] = arguments[validkey]
        self._tests.append((testclass, args, monitors))

    def subTestDone(self, subtest):
        """
        subclass should implement this method to know when a subtest is
        done. This is the right place to call setNextSubTest().

        Return True (default) if we should carry on with the next subtest (if any).
        Return False if we should not carry on with further tests.
        """
        return True

    # implement Test methods

    # setUp
    # tearDown
    # stop
    # start

    pass

class ListScenario(Scenario):
    """
    Scenario that will run each test one after the other on the same
    arguments.
    """

    __test_arguments__ = {
        "subtest-list" : "List of Testclass to run sequentially",
        "fatal-subtest-failure" : "Do not carry on with next subtest if previous failed"
        }

    def setUp(self):
        if not Scenario.setUp(self):
            return False
        # add the tests
        for subtest in self.arguments["subtest-list"]:
            self.setNextSubTest(subtest,
                                self.arguments,
                                [])
        return True

    def subTestDone(self, test):
        # if we don't have fatal-subtest-failure, carry on if any
        if self.arguments["fatal-subtest-failure"] == False:
            return True
        # else we only carry on if the test was 100% succesfull
        if test.getSuccessPercentage() == 100.0:
            return True
        return False
