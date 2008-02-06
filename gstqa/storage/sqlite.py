# GStreamer QA system
#
#       storage/sqlite.py
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
SQLite based DataStorage
"""

import time
from weakref import WeakKeyDictionary
from gstqa.log import critical, error, warning, debug, info
from gstqa.storage.storage import DBStorage
from pysqlite2 import dbapi2 as sqlite

TABLECREATION = """
CREATE TABLE version (
   version INTEGER,
   modificationtime INTEGER
);

CREATE TABLE testrun (
   id INTEGER PRIMARY KEY,
   clientid INTEGER,
   starttime INTEGER,
   stoptime INTEGER
);

CREATE TABLE environment (
   testrunid INTEGER,
   data BLOB
);

CREATE TABLE client (
   id INTEGER PRIMARY KEY,
   software TEXT,
   name TEXT,
   user TEXT
);

CREATE TABLE test (
   id INTEGER PRIMARY KEY,
   testrunid INTEGER,
   type TEXT,
   arguments INTEGER,
   results INTEGER,
   resultpercentage FLOAT,
   extrainfo INTEGER
);

CREATE TABLE scenario (
   id INTEGER PRIMARY KEY,
   testrunid INTEGER,
   type TEXT,
   arguments BLOB,
   results BLOB,
   resultpercentage FLOAT,
   extrainfo BLOB,
   subtests BLOB
);

CREATE TABLE testclassinfo (
   type TEXT PRIMARY KEY,
   parent TEXT,
   description TEXT,
   arguments BLOB,
   checklist BLOB,
   extrainfo BLOB
);

CREATE TABLE dicts (
   id INTEGER PRIMARY KEY
);

CREATE TABLE argumentsdicts (
   dictid INTEGER,
   keyid INTEGER,
   type INTEGER
);

CREATE TABLE extrainfodicts (
   dictid INTEGER,
   keyid INTEGER,
   type INTEGER
);

CREATE TABLE environdicts (
   dictid INTEGER,
   keyid INTEGER,
   type INTEGER
);

CREATE TABLE checklistdicts (
   dictid INTEGER,
   keyid INTEGER,
   type INTEGER
);

CREATE TABLE dictstr (
   id INTEGER PRIMARY KEY,
   name STRING,
   value STRING
);

CREATE TABLE dictint (
   id INTEGER PRIMARY KEY,
   name STRING,
   value INTEGER
);

CREATE TABLE dictblob (
   id INTEGER PRIMARY KEY,
   name STRING,
   value BLOB
);
"""

DATABASE_VERSION = 1

DATA_TYPE_INT = 0
DATA_TYPE_STR = 1
DATA_TYPE_BLOB = 2

#
# FIXME / WARNING
# The current implementation only supports handling of one testrun at a time !
#

class SQLiteStorage(DBStorage):
    """
    Stores data in a sqlite db
    """

    def __init__(self, *args, **kwargs):
        DBStorage.__init__(self, *args, **kwargs)
        self.__clientid = None
        self.__testrunid = None
        self.__testrun = None
        self.__tests = WeakKeyDictionary()

    def openDatabase(self):
        debug("opening sqlite db for path '%s'", self.path)
        self.con = sqlite.connect(self.path)

    def createTables(self):
        # check if tables aren't already created
        if self._checkForTables():
            return
        debug("Calling db creation script")
        self.con.executescript(TABLECREATION)
        self.con.commit()
        if self._checkForTables() == False:
            error("Tables were not created properly !!")
        # add database version
        self._ExecuteCommit("INSERT INTO version (version, modificationtime) VALUES (?, ?)",
                            (DATABASE_VERSION, int(time.time())))
        debug("Tables properly created")

    def _checkForTables(self):
        # return False if the tables aren't created
        CHECKTABLES = """
        SELECT name FROM sqlite_master
        WHERE type='table'
        ORDER BY name;
        """
        tables = [x[0] for x in self.con.execute(CHECKTABLES).fetchall()]
        if len(tables) == 0:
            return False
        # FIXME : Really check if all tables are present
        for tblname in ["testrun", "environment", "client", "test",
                        "scenario", "testclassinfo"]:
            if not tblname in tables:
                return False
        return True

    def _ExecuteCommit(self, instruction, *args, **kwargs):
        # Convenience function to call execute and commit in one line
        # returns the last row id
        cur = self.con.cursor()
        cur.execute(instruction, *args, **kwargs)
        self.con.commit()
        return cur.lastrowid

    def _FetchAll(self, instruction, *args, **kwargs):
        # Convenience function to fetch all results
        cur = self.con.cursor()
        cur.execute(instruction, *args, **kwargs)
        return cur.fetchall()

    # dictionnary storage methods
    def _conformDict(self, dict):
        # transforms the dictionnary values to types compatible with
        # the DB storage format
        res = {}
        for key,value in dict.iteritems():
            if isinstance(value, int):
                res[key] = long(value)
            else:
                res[key] = value
        return res

    def _storeDict(self, dicttable, dict):
        # get a unique dict key id
        insertstr = "INSERT INTO dicts VALUES (NULL)"
        dictid = self._ExecuteCommit(insertstr)
        debug("Got key id %d to insert in table %s", dictid, dicttable)

        dict = self._conformDict(dict)

        # figure out which values to add to which tables
        strs = []
        ints = []
        blobs = []
        insertstr = "INSERT INTO %s (id, name, value) VALUES (NULL, ?, ?)"
        for key,value in dict.iteritems():
            debug("Adding key:%s , value:%r", key, value)
            if isinstance(value, int):
                comstr = insertstr % "dictint"
                lst = ints
            elif isinstance(value, basestring):
                comstr = insertstr % "dictstr"
                lst = strs
            else:
                comstr = insertstr % "dictblob"
                lst = blobs
            lst.append(self._ExecuteCommit(comstr, (key, value)))

        # Now add the various values to the dicttable
        insertstr = "INSERT INTO %s (dictid, keyid, type) VALUES (? , ?, ?)" % dicttable
        for keyid in ints:
            self._ExecuteCommit(insertstr, (dictid, keyid, DATA_TYPE_INT))
        for keyid in strs:
            self._ExecuteCommit(insertstr, (dictid, keyid, DATA_TYPE_STR))
        for keyid in blobs:
            self._ExecuteCommit(insertstr, (dictid, keyid, DATA_TYPE_BLOB))
        return dictid

    def _storeArgumentsDict(self, dict):
        return self._storeDict("argumentsdicts", dict)

    def _storeCheckListDict(self, dict):
        return self._storeDict("checklistdicts", dict)

    def _storeExtraInfoDict(self, dict):
        return self._storeDict("extrainfodicts", dict)

    # public storage API

    def setClientInfo(self, softwarename, clientname, user, id=None):
        # check if that triplet is already present
        debug("softwarename:%s, clientname:%s, user:%s", softwarename, clientname, user)
        existstr = "SELECT id FROM client WHERE software=? AND name=? AND user=?"
        res = self._FetchAll(existstr, (softwarename, clientname, user))
        if len(res) == 1 :
            debug("Entry already present !")
            key = res[0][0]
        elif len(res) > 1:
            warning("More than one similar entry ???")
            raise Exception("There are more than one client entry with the same information, fix database !")
        else:
            key = self._ExecuteCommit("INSERT INTO client (id, software, name, user) VALUES (NULL, ?,?,?)",
                                      (softwarename, clientname, user))
        debug("got id %d", key)
        # cache the key
        self.__clientid = key
        return key

    def startNewTestRun(self, testrun):
        # create new testrun entry with client entry
        debug("testrun:%r", testrun)
        if not self.__clientid:
            raise Exception("Please specify client information before starting the testruns")
        if self.__testrun:
            warning("Apparently the previous testrun didn't exit successfully")
        insertstr = "INSERT INTO testrun (id, clientid, starttime, stoptime) VALUES (NULL, ?, ?, NULL)"
        self.__testrunid = self._ExecuteCommit(insertstr, (self.__clientid, testrun._starttime))
        self.__testrun = testrun
        debug("Got testrun id %d", self.__testrunid)

    def endTestRun(self, testrun):
        debug("testrun:%r", testrun)
        if not self.__testrun == testrun:
            # add the testrun since it wasn't done before
            self.startNewTestRun(testrun)
        updatestr = "UPDATE testrun SET stoptime=? WHERE id=?"
        self._ExecuteCommit(updatestr, (testrun._stoptime, self.__testrunid))
        debug("updated")

    def newTestStarted(self, testrun, test):
        if not self.__testrun == testrun:
            self.startNewTestRun(testrun)
        debug("test:%r", test)
        insertstr = "INSERT INTO test (id, testrunid, type) VALUES (NULL, ?, ?)"
        testid = self._ExecuteCommit(insertstr, (self.__testrunid, test.__test_name__))
        debug("got testid %d", testid)
        self.__tests[test] = testid

    def newTestFinished(self, testrun, test):
        if not self.__testrun == testrun:
            self.startNewTestRun(testrun)
        if not self.__tests[test]:
            self.newTestStarted(testrun, test)
        debug("test:%r", test)
        updatestr = "UPDATE test SET arguments=?,results=?,resultpercentage=?,extrainfo=? WHERE id=?"
        # FIXME : TEMPORARY SERIALIZATION !!!
        # Put a proper serialization method
        resultpercentage = test.getSuccessPercentage()
        resultsid = self._storeCheckListDict(test.getCheckList())
        argsid = self._storeArgumentsDict(test.getArguments())
        extrainfoid = self._storeExtraInfoDict(test.getExtraInfo())
        self._ExecuteCommit(updatestr, (argsid, resultsid,
                                        resultpercentage,
                                        extrainfoid,
                                        self.__tests[test]))

    # public retrieval API

    def getClientInfoForTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = "SELECT client.software,client.name,client.user FROM client,testrun WHERE client.id=testrun.clientid AND testrun.id=?"
        res = self._FetchAll(liststr, (testrunid,))
        return res[0]

    def listTestRuns(self):
        liststr = "SELECT id FROM testrun"
        res = self._FetchAll(liststr)
        debug("Got %d testruns", len(res))
        return list(zip(*res)[0])

    def getTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = "SELECT clientid,starttime,stoptime FROM testrun WHERE id=?"
        res = self._FetchAll(liststr, (testrunid, ))
        if len(res) == 0:
            debug("Testrun not available in DB")
            return (None, None, None)
        if len(res) > 1:
            warning("More than one testrun with the same id ! Fix DB !!")
            return (None, None, None)
        return res[0]

    def getTestsForTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = "SELECT id FROM test WHERE testrunid=?"
        res = self._FetchAll(liststr, (testrunid, ))
        return list(zip(*res)[0])
