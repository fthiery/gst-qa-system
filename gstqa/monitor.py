# GStreamer QA system
#
#       monitor.py
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

# TODO
#
# Add default monitor (spawn process, crash, timeout, IPC)
#    maybe in a different file...

# Design
#
# Monitors can do one or more of the following:
# * set/add/change Environment variables
# * wrap the test (ex : valgrind)
#   Ex : sometool --with -some -option [regularlauncher args]...
# * redirect Standard I/O to some files or functions
#   => Requires being able to create temporary files
# * postprocess output
# * has a checklist like tests
# * can modify timeout (i.e. with valgrind)

import string
import os
import os.path
from gstqa.test import Test, DBusTest, GStreamerTest
from gstqa.log import critical, error, warning, debug, info

class Monitor:
    """
    Monitors a test
    """
    __monitor_name__ = "monitor"
    __monitor_description__ = "Base Monitor class"
    __monitor_arguments__ = {}
    __monitor_output_files__ = {}
    __monitor_checklist__ = {}
    __monitor_extra_infos__ = {}
    __applies_on__ = Test

    def __init__(self, testrun, instance, *args, **kwargs):
        self.testrun = testrun
        self.test = instance
        self.arguments = kwargs
        self._checklist = {}
        self._extraInfo = {}
        self._outputfiles = {}

    def setUp(self):
        return True

    def tearDown(self):
        pass

    def processResults(self):
        pass

    def _populateChecklist(self):
        """ fill the instance checklist with default values """
        ckl = self.getFullCheckList()
        for key in ckl.keys():
            self._checklist[key] = False

    ## Methods for tests to return information

    def validateStep(self, checkitem):
        """
        Validate a step in the checklist.
        checkitem is one of the keys of __test_checklist__

        Called by the test itself
        """
        info("step %s for item %r" % (checkitem, self))
        if not checkitem in self._checklist:
            return
        self._checklist[checkitem] = True

    def extraInfo(self, key, value):
        """
        Give extra information obtained while running the tests.

        If key was already given, the new value will override the value
        previously given for the same key.

        Called by the test itself
        """
        debug("%s : %r", key, value)
        self._extraInfo[key] = value

    def setOutputFile(self, key, value):
        """
        Report the location of an output file
        """
        debug("%s : %s", key, value)
        self._outputfiles["key"] = value

    # getters

    def getCheckList(self):
        """
        Returns the instance checklist.
        """
        return self._checklist

    def getArguments(self):
        """
        Returns the list of arguments for the given test
        """
        validkeys = self.getFullArgumentList().keys()
        res = {}
        for key in self.arguments.iterkeys():
            if key in validkeys:
                res[key] = self.arguments[key]
        return res

    ## Class methods

    @classmethod
    def getFullCheckList(cls):
        """
        Returns the full monitor checklist. This is used to know all the
        possible check items for this instance, along with their description.
        """
        d = {}
        for cl in cls.mro():
            if "__monitor_checklist__" in cl.__dict__:
                d.update(cl.__monitor_checklist__)
            if cl == Test:
                break
        return d

    @classmethod
    def getFullArgumentList(cls):
        """
        Returns the full list of arguments with descriptions.
        """
        d = {}
        for cl in cls.mro():
            if "__monitor_arguments__" in cls.__dict__:
                d.update(cl.__monitor_arguments__)
            if cl == Test:
                break
        return d

    @classmethod
    def getFullExtraInfoList(cls):
        """
        Returns the full list of extra info with descriptions.
        """
        d = {}
        for cl in cls.mro():
            if "__monitor_extra_infos__" in cls.__dict__:
                d.update(cl.__monitor_extra_infos__)
            if cl == Test:
                break
        return d

    @classmethod
    def getFullOutputFilesList(cls):
        """
        Returns the full list of output files with descriptions.
        """
        d = {}
        for cl in cls.mro():
            if "__monitor_output_files__" in cls.__dict__:
                d.update(cl.__monitor_output_files__)
            if cl == Test:
                break
        return d


class GstDebugLogMonitor(Monitor):
    """
    Activates GStreamer debug logging and stores it in a file
    """
    __monitor_name__ = "gst-debug-log-monitor"
    __monitor_description__ = "Logs GStreamer debug activity"
    __monitor_arguments__ = {
        "debug-level" : "GST_DEBUG value (defaults to '*:2')"
        }
    __monitor_output_files__ = {
        "gst-log-file" : "file containing the GST_DEBUG log"
        }
    __applies_on__ = GStreamerTest

    # needs to redirect stderr to a file
    def setUp(self):
        Monitor.setUp(self)
        # set gst_debug to 0
        self.test._environ["GST_DEBUG"] = self.arguments.get("debug-level", "*:2")
        # get file for redirection
        self._logfile, self._logfilepath = self.testrun.get_temp_file(nameid="gst-debug-log")
        debug("Got temporary file %s", self._logfilepath)
        if self.test._stderr:
            warning("stderr is already being used, can't setUp monitor")
            return False
        self.test._stderr = self._logfile
        self.setOutputFile("gst-log-file", self._logfilepath)
        return True

    def tearDown(self):
        if self._logfile:
            os.close(self._logfile)

class ValgrindMemCheckMonitor(Monitor):
    """
    Runs the test within a valgrind --tool=memcheck environment
    """
    __monitor_name__ = "valgrind-memcheck-monitor"
    __monitor_description__ = "Checks for memory leaks using valgrind memcheck"
    __monitor_arguments__ = {
        "suppression-files":"coma separated list of suppresion files"
        }
    __monitor_output_files__ = {
        "memcheck-log" : "Full log from valgrind memcheck"
        }

    __applies_on__ = DBusTest

    def setUp(self):
        Monitor.setUp(self)
        self._logfile, self._logfilepath = self.testrun.get_temp_file(nameid="valgrind-memcheck")
        # prepend valgrind options
        ourargs = ["valgrind", "--tool=memcheck",
                   "--leak-check=full", "--trace-children=yes",
                   "--leak-resolution=med", "--num-callers=20",
                   "--log-file=%s" % self._logfilepath]
        # add the suppression files
        sups = self.arguments.get("suppression-files")
        if sups:
            for sup in string.split(sups, ','):
                ourargs.append("--suppressions=%s" % sup)
        ourargs.extend(self.test._preargs)
        self.test._preargs = ourargs
        self.setOutputFile("memcheck-log", self._logfilepath)
        # set some env variables
        self.test._environ["G_SLICE"] = "always-malloc"
        # multiply timeout by 4
        if not self.test.setTimeout(self.test.getTimeout() * 4):
            warning("Couldn't change the timeout !")
            return False
        # multiply async-setup-timeout by 4 !
        if not self.test.setAsyncSetupTimeout(self.test.getAsyncSetupTimeout() * 4):
            warning("Couldn't change the asynchronous setup timeout !")
            return False
        return True

    def tearDown(self):
        if self._logfile:
            os.close(self._logfile)

class GDBMonitor(Monitor):
    """
    Sets up the environment in order to collect core dumps and
    get backtraces.

    This monitor will NOT run the test under gdb

    For this monitor to work, you need to have the two following
    kernel values set properly:

    /proc/sys/kernel/core_uses_pid = 1
    /proc/sys/kernel/core_pattern = core
    """

    __applies_on__ = DBusTest

    # doesn't need to do any redirections
    # setup 'ulimit -c unlimited'
    # when the test is done, check whether it crashed, if so:
    #  * run a gdb script to collect a backtrace
    #  * remove core file

    def setUp(self):
        Monitor.setUp(self)
        # add some env variables
        self.test._environ["G_DEBUG"] = "fatal_warnings"
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CORE, (-1, -1))
        except:
            warning("Couldn't change core limit")
            return False
        return True

    def tearDown(self):
        # if the return value of the subprocess is non-null, we most
        # likely have a crasher and core dump
        if not self.test._returncode == 0:
            debug("non-null returncode [%d] for pid %d",
                  self.test._returncode,
                  self.test._pid)
            # try to find the core file
            core = self._findCoreFile()
            if core:
                debug("Got core file %s", core)
                # FIXME : Actually get backtrace :)
                os.remove(core)

    def _findCoreFile(self):
        cwd = self.testrun.getWorkingDirectory()
        root, dirs, files = list(os.walk(cwd))[0]
        debug("files : %r", files)
        for fname in files:
            if fname == "core":
                return os.path.join(cwd, fname)
            if fname == "core.%d" % self.test._pid:
                return os.path.join(cwd, fname)
        return None

class FileBasedMonitorInterface:
    """
    Interface for monitors that record data to file(s)
    """

    # TODO :
    #  We should create the unique/temporary files in a location
    #  specified by the client configuration
    #
    #  Make sure we can handle several files

    def requestUniqueFileLocation(self):
        # returns an opened file object
        pass

    def deleteAllFiles(self):
        # used to clean up failed tests or files no longer needed
        pass
    pass
