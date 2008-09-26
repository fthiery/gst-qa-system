# GStreamer QA system
#
#       storage/storage.py
#
# Copyright (c) 2008, Edward Hervey <bilboed@bilboed.com>
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
Classes and methods related to storing/retrieving results/data/...
"""

class DataStorage(object):
    """
    Base class for storing data
    """
    def __init__(self):
        self._setUp()

    # methods to implement in subclasses
    def _setUp(self):
        raise NotImplementedError

    def findTestsByArgument(self, testtype, arguments, testrunid=None, monitors=None):
        """
        Return all test ids of type <testtype> and with arguments <arguments>

        arguments is a dictionnary
        If specified, only tests belonging to the given testrunid will be
        returned.
        """
        raise NotImplementedError

    # public API
    def close(self, callback=None, *args, **kwargs):
        """
        Close the storage.

        The callback (if any given) will be called when the Storage has
        finished processing any pending actions.

        If the Storage was not being used asynchronously, that callback will
        be called straight away.
        """
        raise NotImplementedError

    # public storage API

    def setClientInfo(self, softwarename, clientname, user):
        """
        Set the information about the runnign client.
        Returns a unique identifier to this client in the storage.

        softwarename : the name of the software running the tests
        clientname : the name of the (client) machine
        user : the email or name of the user running the tests
        """
        raise NotImplementedError

    def startNewTestRun(self, testrun, clientid):
        """
        Inform the DataStorage that the given testrun has started for the given
        client.

        You may get the clientid by using setClientInfo
        """
        raise NotImplementedError

    def endTestRun(self, testrun):
        """Inform the DataStorage that the given testrun is closed and done."""
        # mark the testrun as closed and done
        raise NotImplementedError

    def newTestStarted(self, testrun, test):
        """Inform the DataStorage that the given test has started for the
        given testrun."""
        # create new entry in tests table
        raise NotImplementedError

    def newTestFinished(self, testrun, test):
        """Inform the DataStorage that the given test of the given testrun
        has finished."""
        raise NotImplementedError

    # public retrieval API

    def listTestRuns(self):
        """
        Returns the list of testruns ID currently available
        """
        raise NotImplementedError

    def getTestRun(self, testrunid):
        """
        Returns a tuple containing the information about the given testrun.
        (clientid, starttime, stoptime)

        If the testrun doesn't exist, it will return the following tuple:
        (None, None, None)
        """
        raise NotImplementedError

    def getTestsForTestRun(self, testrunid, withscenarios=True):
        """
        Returns the list of testid for the given testrunid

        If withscenarios is True, scenarios will also be returned.
        If withscenarios is False, only non-scenario tests will be returned.
        """
        raise NotImplementedError

    def getScenariosForTestRun(self, testrunid):
        """
        Returns the scenarios for the given testrunid

        The dictionnary has:
        * key : the testid of the scenario
        * value : A list of testid of the subtests
        """
        raise NotImplementedError

    def getClientInfoForTestRun(self, testrunid):
        """
        Returns the Client information for the given testrunid.

        The result is a tuple of strings:
        * software
        * name
        * user
        """
        raise NotImplementedError

    def getEnvironmentForTestRun(self, testrunid):
        """
        Returns a dictionnary of the environment of the given testrunid.
        """
        raise NotImplementedError

    def getFailedTestsForTestRun(self, testrunid):
        """
        Returns the list of failed tests in the given testrun
        """
        raise NotImplementedError

    def getSucceededTestsForTestRun(self, testrunid):
        """
        Returns the list of succeeded tests in the given testrun.
        """
        raise NotImplementedError

    def getFullTestInfo(self, testid, rawinfo=False):
        """
        Returns a tuple with the following info:
        * the testrun id in which it was executed
        * the type of the test
        * the arguments (dictionnary)
        * the results (checklist list)
        * the result percentage
        * the extra information (dictionnary)
        * the output files (dictionnary)

        If rawinfo is set to True, then the keys of the following
        dictionnaries will be integer identifiers (and not strings):
        * arguments, results, extra information, output files
        Also, the testtype will be the testclass ID (and not a string)
        """
        raise NotImplementedError

    def getTestClassInfo(self, testtype):
        """
        Returns a tuple with the following info:
        * Description of the Test class
        * Full description of the Test class
        * the argumenbts (dictionnary)
        * the checks (dictionnary)
        * the extra information (dictionnary)
        * the output files (dictionnary)
        """
        raise NotImplementedError

    def getMonitorsIDForTest(self, testid):
        """
        Returns the list of monitor ID for the given testid
        """
        raise NotImplementedError

    def getFullMonitorInfo(self, monitorid):
        """
        Returns a tuple with the following info:
        * the ID of the test on which this monitor was applied
        * the type of the monitor
        * the arguments (dictionnary)
        * the results (dictionnary)
        * the result percentage
        * the extra information (dictionnary)
        * the output files (dictionnary)
        """
        raise NotImplementedError

    def getMonitorInfo(self, monitorid):
        """
        Returns a tuple with the following info:
        * the ID of the test on which the monitor was applied
        * the type of the monitor
        * the result percentage
        """
        raise NotImplementedError

class FileStorage(DataStorage):
    """
    Base class for storing data to a file

    Don't use this class directly, but one of its subclasses
    """

    def __init__(self, path, *args, **kwargs):
        self.path = path
        DataStorage.__init__(self, *args, **kwargs)

class NetworkStorage(DataStorage):
    """
    Stores data to a remote storage

    Don't use this class directly, but one of its subclasses
    """
    # properties
    # * host
    # * port
    pass

