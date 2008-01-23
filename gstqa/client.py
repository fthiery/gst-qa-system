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

import gobject
gobject.threads_init()
import dbus
import dbus.service
import dbus.mainloop.glib
import dbustools

from testrun import TestRun
from log import critical, error, warning, debug, info, initLogging

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

    def __init__(self, singlerun=False, *args, **kwargs):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        info("starting")
        self._ml = gobject.MainLoop()
        self._bus = dbustools.get_private_session_bus()
        self._busname = dbus.service.BusName("net.gstreamer.TesterClient", self._bus)
        #dbus.service.Object.__init__(self, dbustools.get_private_session_bus(), "/here")
        dbus.service.Object.__init__(self, self._bus, "/here")
        self._testruns = []
        self._storage = None
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
        gobject.idle_add(self._runNext)
        try:
            self._ml.run()
        except KeyboardInterrupt:
            debug("Interrupted, calling clean-up")
            self.quit()

    def quit(self):
        """
        Stop the client
        """
        debug("Quitting...")
        self._running = False
        if self._current:
            self._current.abort()
        dbustools.kill_private_dbus()
        # TODO : maybe we need to abort/cleanup some other things
        # like the DataStorage ?

        self._ml.quit()

    def setStorage(self, storage):
        """
        Specify the DataStorage to use with this client
        """
        self._storage = storage

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
        pass

    def test_run_done(self, testrun):
        pass

    def test_run_aborted(self, testrun):
        pass

    # DEBUG : REMOVE ME !
    # DEBUG : REMOVE ME !
    @dbus.service.method(dbus_interface='net.gstreamer.Insanity',
                         in_signature='', out_signature='')
    def nothing(self):
        print "Nothing !!!"
