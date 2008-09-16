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

class DataStorage:
    """
    Base class for storing data
    """
    def __init__(self):
        self.setUp()

    # methods to implement in subclasses
    def setUp(self):
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
        pass

    def startNewTestRun(self, testrun):
        """Inform the DataStorage that the given testrun has started."""
        pass

    def endTestRun(self, testrun):
        """Inform the DataStorage that the given testrun is closed and done."""
        # mark the testrun as closed and done
        pass

    def newTestStarted(self, testrun, test):
        """Inform the DataStorage that the given test has started for the
        given testrun."""
        # create new entry in tests table
        pass

    def newTestFinished(self, testrun, test):
        """Inform the DataStorage that the given test of the given testrun
        has finished."""
        pass

    # public retrieval API

    def listTestRuns(self):
        """
        Returns the list of testruns ID currently available
        """
        pass

    def getTestRun(self, testrunid):
        """
        Returns a tuple containing the information about the given testrun.
        (clientid, starttime, stoptime)

        If the testrun doesn't exist, it will return the following tuple:
        (None, None, None)
        """
        pass

    def getTestsForTestRun(self, testrunid, withscenarios=True):
        """
        Returns the list of testid for the given testrunid

        If withscenarios is True, scenarios will also be returned.
        If withscenarios is False, only non-scenario tests will be returned.
        """
        pass

    def getScenariosForTestRun(self, testrunid):
        """
        Returns the scenarios for the given testrunid

        The dictionnary has:
        * key : the testid of the scenario
        * value : A list of testid of the subtests
        """

    def getClientInfoForTestRun(self, testrunid):
        """
        Returns the Client information for the given testrunid.

        The result is a tuple of strings:
        * software
        * name
        * user
        """
        pass

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

class DBStorage(DataStorage):
    """
    Stores data in a database

    Don't use this class directly, but one of its subclasses
    """

    # DataStorage methods implementation

    def setUp(self):
        # open database
        self.openDatabase()

        # createTables if needed
        self.createTables()

    def close(self, callback=None, *args, **kwargs):
        self._shutDown(callback, *args, **kwargs)


    # Methods to be implemented in subclasses

    def openDatabase(self):
        raise NotImplementedError

    def createTables(self):
        raise NotImplementedError

    def _shutDown(self, callback, *args, **kwargs):
        raise NotImplementedError
