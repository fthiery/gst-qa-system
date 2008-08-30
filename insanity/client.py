# GStreamer QA system
#
#       client.py
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
Tester Client

This is a convenience class which allows control and feedback over:
* What tests/scenarios to be run
* What output to use
* What data storage to use

Many subclasses can be created, including but not limited to:
* Command line interface
* Graphical application
* Daemon to be accessed via network
"""

import os
import gobject
gobject.threads_init()
import dbus
import dbus.service
import dbus.mainloop.glib
import time

# import all tests and scenarios
import insanity.utils as utils
utils.scan_for_tests()

import insanity.dbustools as dbustools
from insanity.testrun import TestRun
from insanity.scenario import Scenario
from insanity.log import warning, debug, info, exception, initLogging

initLogging()

# TODO
#
# * methods for reporting progress/failures/... that subclasses can
#   implement
# * methods for giving instructions that subclasses can use
#
# QUESTIONS
# * how do we give configuration settings ??

class TesterClient(dbus.service.Object):
    """
    Base class for Tester clients
    """

    # class variables
    __software_name__ = """USER FORGOT TO PUT CLIENT NAME"""
    """
    Subclasses of TesterClient need to put the name of their software in __software_name__
    """

    def __init__(self, singlerun=False, storage=None,
                 *args, **kwargs):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        info("starting")
        self._ml = gobject.MainLoop()
        self._bus = dbustools.get_private_session_bus()
        self._busname = dbus.service.BusName("net.gstreamer.TesterClient", self._bus)
        #dbus.service.Object.__init__(self, dbustools.get_private_session_bus(), "/here")
        dbus.service.Object.__init__(self, self._bus, "/here")
        self._testruns = []
        self._storage = None
        if storage:
            self.setStorage(storage)
        # _current is the current TestRun being executed
        self._current = None
        # _running is True if the mainloop is running
        self._running = False
        # If _singlerun == True, the client will quit after
        # all testruns are done
        self._singlerun = singlerun

    def run(self):
        """
        Start the client
        """
        if self._running:
            return
        self._running = True
        self._ensureStorageAvailable()
        gobject.idle_add(self._runNext)

    def quit(self):
        """
        Stop the client
        """
        debug("Quitting...")
        if not self._running:
            debug("we were already quitting")
            return
        self._running = False
        try:
            if self._current:
                self._current.abort()
        finally:
            try:
                self._storage.shutDown(self._exit)
            except:
                self._exit()

    def _exit(self):
        debug("Really quitting")
        try:
            dbustools.kill_private_dbus()
        finally:
            self._ml.quit()

    def setStorage(self, storage):
        """
        Specify the DataStorage to use with this client
        """
        if self._storage:
            # disconnect gracefully
            pass
        if storage == None:
            # Yes, default is sqlitestorage !
            from insanity.storage.sqlite import SQLiteStorage
            storage = SQLiteStorage(path="testrun.db")
        self._storage = storage
        # give client info, this can always be modified later on
        self._storage.setClientInfo(*self.getClientInfo())

    def getClientInfo(self):
        """
        Returns a tuple with:
        * The name of the software,
        * The identifier of the machine running this client
        * The identifier of the user running this client (most likely email)

        Sub-classes can override this to return more specific information, this
        information will be stored in the results.
        """
        softname = self.__software_name__
        # FQDN of the machine
        import socket
        clientname = socket.getfqdn()
        # user, email address or username
        for i in ["EMAIL_ADDRESS", "MAIL_ADDRESS", "REAL_NAME", "USERNAME"]:
            username = os.getenv(i)
            if username:
                break
        return (softname, clientname, username)

    def _ensureStorageAvailable(self):
        if self._storage:
            return
        self.setStorage(None)

    def _runNext(self):
        """
        Run next testrun if available
        """
        if not self._running:
            warning("Not running")
            return False
        if self._current:
            warning("Already running a TestRun [%s]" % self._current)
            return False
        if self._testruns == []:
            debug("No more TestRun(s) available")
            if self._singlerun:
                debug("Single-Run mode, now exiting")
                self.quit()
            return False
        self._current = self._testruns.pop(0)
        debug("Current testrun is now %s" % self._current)
        # connect signals
        self._current.connect("start", self._currentStartCb)
        self._current.connect("done", self._currentDoneCb)
        self._current.connect("aborted", self._currentAbortedCb)
        # give access to the data storage object
        self._current.setStorage(self._storage)
        # and run it!
        self._current.run()
        return False

    ## TestRun callbacks

    def _currentStartCb(self, current):
        self.test_run_start(current)

    def _currentDoneCb(self, current):
        self.test_run_done(current)
        if current == self._current:
            self._current = None
            self._runNext()

    def _currentAbortedCb(self, current):
        self.test_run_aborted(current)
        if current == self._current:
            self._current = None
            self._runNext()

    ## methods for giving test instructions
    ## Those instructions are in fact TestRun objects !

    def addTestRun(self, testrun):
        """
        Add a TestRun to the execution queue.
        """
        if not isinstance(testrun, TestRun):
            print "This is not a valid TestRun !", testrun
            return
        self._testruns.append(testrun)
        if self._running:
            self._runNext()

    ## overrideable methods

    ## methods for reporting progress to subclasses
    def test_run_start(self, testrun):
        """
        Subclasses can implement this method to know when a testrun has
        started.
        """
        pass

    def test_run_done(self, testrun):
        """
        Subclasses can implement this method to know when a testrun has
        finished.
        """
        pass

    def test_run_aborted(self, testrun):
        """
        Subclasses can implement this method to know when a testrun has
        been aborted.
        """
        pass

class CommandLineTesterClient(TesterClient):
    """
    Base class for command line clients.

    It will show the ongoing status of the testruns.

    Offers possibility to output verbose printout of ongoing tests
    """

    def __init__(self, verbose=False, *args, **kwargs):
        """
        verbose : If True, will output verbose details on ongoing test
        """
        TesterClient.__init__(self, *args, **kwargs)
        self._verbose = verbose

    def run(self):

        TesterClient.run(self)

        # Now run the main loop, which blocks until finished or quitting:
        try:
            self._ml.run()
        except KeyboardInterrupt:
            exception("Interrupted, calling clean-up")
            self.quit()

    def test_run_start(self, testrun):
        print "Starting", testrun
        testrun.connect("single-test-done", self._singleTestDoneCb)
        if self._verbose:
            self._printTestRunEnvironment(testrun)

    def test_run_done(self, testrun):
        print "Done with", testrun
        ids = self._storage.listTestRuns()
        for key in ids:
            clientid, starttime, stoptime = self._storage.getTestRun(key)
            print "TestRun #%d from client %d" % (key, clientid)
            softw,name,user = self._storage.getClientInfoForTestRun(key)
            print "\t\tsoftware:%s,name:%s,user:%s" % (softw,name,user)
            print "\tStart:", time.ctime(starttime)
            print "\tStop:", time.ctime(stoptime)
            print "\tNb tests:", len(self._storage.getTestsForTestRun(key))
            print "\n"

    def test_run_aborted(self, testrun):
        print "Aborted", testrun

    def _singleTestDoneCb(self, testrun, test):
        self.printSingleTestResult(test, testrun=testrun)

    def _printTestRunEnvironment(self, testrun):
        d = testrun.getEnvironment()
        if d:
            print "Environment:"
            for key,val in d.iteritems():
                if isinstance(val, dict):
                    print "\t% -30s:" % (key)
                    for dk,dv in val.iteritems():
                        print "\t\t% -30s:\t%s" % (dk,dv)
                else:
                    print "\t% -30s:\t%s" % (key,val)

    def printSingleTestResult(self, test, offset=0, testrun=None):
        stub = " " * offset
        if testrun:
            pos = testrun.getCurrentBatchPosition()
            length = testrun.getCurrentBatchLength()
            perc = float(pos * 100.0) / float(length)
            print stub, "Test %r is done (Success:%5.1f%%)  %5d / %5d  [%5.1f%%]" % (test, test.getSuccessPercentage(), pos, length, perc)
        else:
            print stub, "Test %r is done (Success:%5.1f%%)" % (test, test.getSuccessPercentage())
        if self._verbose:
            # print out all details from test
            print stub, "Arguments:"
            ta = test.arguments
            fa = test.getFullArgumentList()
            for arg in [x for x in fa if ta.has_key(x)]:
                print stub, "  %s : %s\t\t%s" % (arg, fa[arg][0], ta[arg])
            # print results from test
            print stub, "Results"
            tc = test.getCheckList()
            fc = test.getFullCheckList()
            for step,val in tc:
                print stub, "  %30s:%10s\t\t%s" % (step, val, fc[step])

            infos = test.getExtraInfo()
            if infos:
                print stub, "Extra information:"
            for extra in infos:
                print stub, "  %30s :\t%s" % (extra, infos[extra])
            if isinstance(test, Scenario):
                for sub in test.tests:
                    print stub, "Sub Test"
                    self.printSingleTestResult(sub, offset=offset+4)
                print "\n"
