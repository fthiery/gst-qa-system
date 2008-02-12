# GStreamer QA system
#
#       testrun.py
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
Test runs

A TestRun is the execution of one or more tests/scenarios with various
arguments.
It will also collect the state of the environment.

The smallest TestRun is a single test without any arguments nor any
monitors.

Tests have access to the TestRun within which they are being executed
so they can look for results of other tests.

Access to the TestRun from test instances will be possible via DBus IPC.
"""

import gobject
import time
from log import critical, error, warning, debug, info
from test import Test
from arguments import Arguments
import gstqa.environment as environment
import dbustools
import dbus.gobject_service
import tempfile
import os

##
## TODO/FIXME
##
## Add possibility to add/modify/remove env variables
##   This will be needed to run test with different environments
##   WITHOUT having to restart the daemon.

class TestRun(gobject.GObject):
    __gsignals__ = {
        "start" : (gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   ()),
        "done" : (gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   ()),
        "aborted" : (gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   ( )),
        # a test started/ended
        # Warning, it is not automatically a SingleTest
        "single-test-done" : (gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT, )),
        "single-test-start" : (gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT, )),

        # new-remote-test (uuid)
        #  emitted when a new test has appeared on the private bus
        "new-remote-test" : (gobject.SIGNAL_RUN_LAST,
                             gobject.TYPE_NONE,
                             (gobject.TYPE_STRING, )),
        "removed-remote-test" : (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE,
                                 (gobject.TYPE_STRING, ))
        }

    def __init__(self, maxnbtests=1, workingdir=None):
        """
        maxnbtests : Maximum number of tests to run simultaneously in each batch.
        workingdir : Working directory (default : getcwd() + /outputfiles/)
        """
        gobject.GObject.__init__(self)
        self._setupPrivateBus()
        self._tests = [] # list of (test, arguments, monitors)
        self._storage = None
        self._currenttest = None
        self._currentmonitors = None
        self._currentarguments = None
        self._runninginstances = []
        self._maxnbtests = maxnbtests
        self._starttime = None
        self._stoptime = None
        self._environment = {}
        self._workingdir = workingdir or os.path.join(os.getcwd(), "outputfiles")

    ## PUBLIC API

    def run(self):
        """
        Start executing the tests.
        """
        self._collectEnvironment()

    def abort(self):
        """
        Abort the tests execution.
        """
        # TODO : fill
        for test in self._runninginstances:
            test.stop()
        self.emit("aborted")

    def setStorage(self, storage):
        self._storage = storage

    def addTest(self, test, arguments, monitors=[]):
        """
        Adds test with the given arguments (or generator) and monitors
        to the list of tests to be run
        """
        if not isinstance(test, type) and not issubclass(test, Test):
            raise TypeError("Given test is not a Test object !")
        # arguments NEED to be an Arguments object or a dictionnary
        if isinstance(arguments, dict):
            # convert dictionnary to Arguments
            info("Creating Arguments for %r" % arguments)
            arguments = Arguments(**arguments)
        elif not isinstance(arguments, Arguments):
            raise TypeError("Test arguments need to be an Arguments object or a dictionnary")
        self._tests.append((test, arguments, monitors))

    def getEnvironment(self):
        """
        Returns the environment information of this testrun as a
        dictionnary.
        """
        return self._environment

    ## PRIVATE API

    def _setupPrivateBus(self):
        self._bus = dbustools.get_private_session_bus()
        self._bus_address = dbustools.get_private_bus_address()
        self._dbusobject = self._bus.get_object("org.freedesktop.DBus",
                                                "/org/freedesktop/DBus")
        self._dbusiface = dbus.Interface(self._dbusobject,
                                         "org.freedesktop.DBus")
        self._dbusiface.connect_to_signal("NameOwnerChanged",
                                          self._dbusNameOwnerChangedSignal)
        #self._busname = dbus.service.BusName("net.gstreamer.insanity.TestRun", self._bus)
        #dbus.gobject_service.ExportedGObject.__init__(self, self._bus, "/TestRun/XXX")

    def _dbusNameOwnerChangedSignal(self, name, oldowner, newowner):
        # we only care about connections named net.gstreamer.Insanity.Test.xxx
        info("name:%s , oldowner:%s, newowner:%s" % (name, oldowner, newowner))
        if not name.startswith("net.gstreamer.Insanity.Test.Test"):
            return
        # extract uuid
        uuid = name.rsplit('.Test', 1)[-1]
        if newowner == "":
            self.emit("removed-remote-test", uuid)
        elif oldowner == "":
            self.emit("new-remote-test", uuid)

    def _collectEnvironment(self):
        """
        Collect the environment settings, parameters, variables,...
        """
        environment.collectEnvironment(os.environ, self._gotEnvironment)

    def _gotEnvironment(self, resdict):
        info("Got environment %r", resdict)
        self._environment = resdict
        self.emit("start")
        self._starttime = int(time.time())
        self._storage.startNewTestRun(self)
        gobject.idle_add(self._runNextBatch)

    def _singleTestStart(self, test):
        info("test %r started", test)
        self.emit("single-test-start", test)
        self._storage.newTestStarted(self, test)

    def _singleTestDone(self, test):
        info("Done with test %r , success rate %02f%%",
             test, test.getSuccessPercentage())
        self.emit("single-test-done", test)
        # FIXME : Improvement : disconnect all signals from that test
        if test in self._runninginstances:
            self._runninginstances.remove(test)
        self._storage.newTestFinished(self, test)
        gobject.idle_add(self._runNext)

    def _singleTestCheck(self, test, check):
        pass

    def _runNext(self):
        """ Run the next test+arg+monitor combination """
        if len(self._runninginstances) >= self._maxnbtests:
            warning("We were already running the max number of tests")
            return False
        info("Getting next test arguments for this batch")
        try:
            kwargs = self._currentarguments.next()
        except StopIteration:
            if len(self._runninginstances):
                info("No more arguments, but still a test running")
                return False
            info("No more arguments, we're finished with this batch")
            self._runNextBatch()
            return False

        # grab the next arguments
        testclass = self._currenttest
        monitors = self._currentmonitors

        # create test with arguments
        debug("Creating test %r with arguments %r" % (testclass, kwargs))
        test = testclass(testrun=self, bus=self._bus,
                         bus_address=self._bus_address,
                         **kwargs)
        for monitor in monitors:
            test.addMonitor(monitor)

        test.connect("start", self._singleTestStart)
        test.connect("done", self._singleTestDone)
        test.connect("check", self._singleTestCheck)

        # add instance to running tests
        self._runninginstances.append(test)

        # apply monitors
        # start test
        test.run()

        # if we can still create a new test, call ourself again
        if len(self._runninginstances) < self._maxnbtests:
            warning("still more test to run (current:%d/max:%d)",
                    len(self._runninginstances), self._maxnbtests)
            gobject.idle_add(self._runNext)
        return False

    def _runNextBatch(self):
        """ Runs the next test batch """
        if len(self._tests) == 0:
            # if nothing left, stop
            info("No more tests batch to run, we're done")
            self._stoptime = int(time.time())
            self._storage.endTestRun(self)
            self.emit("done")
            return False

        info("Getting next test batch")
        # pop out the next batch
        test, args, monitors = self._tests.pop(0)
        self._currenttest = test
        self._currentmonitors = monitors
        self._currentarguments = args

        info("Current test : %r" % test)
        info("Current monitors : %r" % monitors)
        info("Current arguments : %r" % args)

        # and run the first one of that batch
        self._runNext()
        return False

    def get_temp_file(self):
        """ Return a temporary file object """
        # we create temporary files in a specified directory
        if not os.path.exists(self._workingdir):
            os.makedirs(self._workingdir)
        return tempfile.mkstemp(prefix="gstqa-output-",
                                dir=self._workingdir)


gobject.type_register(TestRun)

class ListTestRun(TestRun):
    """
    Convenience class to specify a list of tests that will be run
    with the same arguments/generator and monitor(s).

    Parameters:
    * fatal-failure : boolean (default:False)
    If set to True, a test will only be run if the previous test for
    the same argument has completed successfully.
    """

    def __init__(self, tests, arguments, monitors=[], *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)
        for test in tests:
            self.addTest(test, arguments, monitors)

def single_test_run(test, arguments=[], monitor=None):
    """
    Convenience function to create a TestRun for a single test
    """
    t = TestRun()
    t.addTest(test, arguments, monitors)
    return t
