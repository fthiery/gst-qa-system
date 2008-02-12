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
from gstqa.scenario import Scenario
from gstqa.test import Test
try:
    # In Python 2.5, this is part of the standard library:
    from sqlite3 import dbapi2 as sqlite
except ImportError:
    # Previous versions have this as external dependency...
    from pysqlite2 import dbapi2 as sqlite
from cPickle import dumps, loads

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
   data INTEGER
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
   extrainfo INTEGER,
   outputfiles INTEGER
);

CREATE TABLE subtests (
   testid INTEGER PRIMARY KEY,
   scenarioid INTEGER
);

CREATE TABLE testclassinfo (
   type TEXT PRIMARY KEY,
   parent TEXT,
   description TEXT,
   arguments INTEGER,
   checklist INTEGER,
   extrainfo INTEGER,
   outputfiles INTEGER
);

CREATE TABLE dicts (
   id INTEGER PRIMARY KEY
);

CREATE TABLE testclassdicts (
   dictid INTEGER,
   keyid INTEGER,
   type INTEGER
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

CREATE TABLE outputfiledicts (
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

# Current database version
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
        for tblname in ["version", "testrun", "environment", "client",
                        "test", "subtests", "testclassinfo", "dicts",
                        "argumentsdicts", "extrainfodicts",
                        "outputfiledicts",
                        "environdicts", "checklistdicts",
                        "dictstr", "dictint", "dictblob"]:
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

    def _FetchOne(self, instruction, *args, **kwargs):
        # Convenience function to fetch all results
        cur = self.con.cursor()
        cur.execute(instruction, *args, **kwargs)
        return cur.fetchone()

    # dictionnary storage methods
    def _conformDict(self, pdict):
        # transforms the dictionnary values to types compatible with
        # the DB storage format
        if pdict == None:
            return None
        res = {}
        for key,value in pdict.iteritems():
            res[key] = value
        return res

    def _storeDict(self, dicttable, pdict):
        # get a unique dict key id
        insertstr = "INSERT INTO dicts VALUES (NULL)"
        dictid = self._ExecuteCommit(insertstr)
        debug("Got key id %d to insert in table %s", dictid, dicttable)

        pdict = self._conformDict(pdict)

        if not pdict:
            # empty dictionnary
            return dictid

        # figure out which values to add to which tables
        strs = []
        ints = []
        blobs = []
        insertstr = "INSERT INTO %s (id, name, value) VALUES (NULL, ?, ?)"
        for key,value in pdict.iteritems():
            debug("Adding key:%s , value:%r", key, value)
            val = value
            if isinstance(value, int):
                comstr = insertstr % "dictint"
                lst = ints
            elif isinstance(value, basestring):
                comstr = insertstr % "dictstr"
                lst = strs
            else:
                comstr = insertstr % "dictblob"
                lst = blobs
                val = sqlite.Binary(dumps(value))
            lst.append(self._ExecuteCommit(comstr, (key, val)))

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

    def _storeTestClassDict(self, dict):
        return self._storeDict("testclassdicts", dict)

    def _storeOutputFileDict(self, dict):
        return self._storeDict("outputfiledicts", dict)

    def _storeEnvironmentDict(self, dict):
        return self._storeDict("environdicts", dict)

    def _insertClassInfo(self, tclass):
        ctype = tclass.__dict__.get("__test_name__")
        if len(self._FetchAll("SELECT * FROM testclassinfo WHERE type=?",
                              (ctype, ))) >= 1:
            return False
        # get info
        desc = tclass.__dict__.get("__test_description__")
        args = tclass.__dict__.get("__test_arguments__")
        checklist = tclass.__dict__.get("__test_checklist__")
        extrainfo = tclass.__dict__.get("__test_extra_infos__")
        outputfiles = tclass.__dict__.get("__test_output_files__")
        if tclass == Test:
            parent = None
        else:
            parent = tclass.__base__.__dict__.get("__test_name__")

        # insert into db
        # dicts
        argsid = self._storeTestClassDict(args)
        checklistid = self._storeTestClassDict(checklist)
        extrainfoid = self._storeTestClassDict(extrainfo)
        outputfilesid = self._storeTestClassDict(outputfiles)
        # final line
        insertstr = "INSERT INTO testclassinfo (type, parent, description, arguments, checklist, extrainfo, outputfiles) VALUES (?, ?, ?, ?, ?, ?, ?)"
        self._ExecuteCommit(insertstr, (ctype, parent, desc, argsid, checklistid, extrainfoid, outputfilesid))
        return True

    def _storeTestClassInfo(self, testinstance):
        # check if we don't already have info for this class
        existstr = "SELECT * FROM testclassinfo WHERE type=?"
        res = self._FetchAll(existstr, (testinstance.__test_name__, ))
        if len(res) >= 1:
            # type already exists, returning
            return
        # we need an inverted mro (so we can now the parent class)
        for cl in testinstance.__class__.mro():
            if not self._insertClassInfo(cl):
                break
            if cl == Test:
                break


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
        envdict = testrun.getEnvironment()
        if envdict:
            # store environement
            envdictid = self._storeEnvironmentDict(envdict)
            insertstr = "INSERT INTO environment (testrunid, data) VALUES (?, ?)"
            self._ExecuteCommit(insertstr, (self.__testrunid, envdictid))
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
        if not isinstance(test, Test):
            raise TypeError("test isn't a Test instance !")
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
        if not self.__tests.has_key(test):
            self.newTestStarted(testrun, test)
        debug("test:%r", test)
        # if it's a scenario, fill up the subtests
        if isinstance(test, Scenario):
            sublist = []
            for sub in test.tests:
                self.newTestFinished(testrun, sub)
            # now add those to the subtests table
            insertstr = "INSERT INTO subtests (testid, scenarioid) VALUES (?,?)"
            for sub in test.tests:
                self._ExecuteCommit(insertstr, (self.__tests[sub],
                                                self.__tests[test]))
        updatestr = "UPDATE test SET arguments=?,results=?,resultpercentage=?,extrainfo=?,outputfiles=? WHERE id=?"
        resultpercentage = test.getSuccessPercentage()
        resultsid = self._storeCheckListDict(test.getCheckList())
        argsid = self._storeArgumentsDict(test.getArguments())
        extrainfoid = self._storeExtraInfoDict(test.getExtraInfo())
        outputfilesid = self._storeOutputFileDict(test.getOutputFiles())
        self._ExecuteCommit(updatestr, (argsid, resultsid,
                                        resultpercentage,
                                        extrainfoid, outputfilesid,
                                        self.__tests[test]))
        self._storeTestClassInfo(test)



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

    def getEnvironmentForTestRun(self, testrunid):
        debug("testrunid", testrunid)
        liststr = "SELECT data FROM environment WHERE testrunid=?"
        res = self._FetchOne(liststr, (testrunid, ))
        if len(res) == 0:
            return {}
        environid = res[0]
        dic = self._getDict("environdicts", environid)
        return dic

    def getTestsForTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = "SELECT id FROM test WHERE testrunid=?"
        res = self._FetchAll(liststr, (testrunid, ))
        if not res:
            return []
        return list(zip(*res)[0])

    def getFailedTestsForTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = "SELECT id FROM test WHERE testrunid=? and resultpercentage<>100.0"
        res = self._FetchAll(liststr, (testrunid, ))
        if not res:
            return []
        return list(zip(*res)[0])

    def getSucceededTestsForTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = "SELECT id FROM test WHERE testrunid=? and resultpercentage=100.0"
        res = self._FetchAll(liststr, (testrunid, ))
        if not res:
            return []
        return list(zip(*res)[0])

    def _getIntVal(self, keyid):
        res = self._FetchOne("SELECT name,value FROM dictint WHERE id=?",
                             (keyid, ))
        return res

    def _getStrVal(self, keyid):
        res = self._FetchOne("SELECT name,value FROM dictstr WHERE id=?",
                             (keyid, ))
        return res

    def _getBlobVal(self, keyid):
        res = self._FetchOne("SELECT name,value FROM dictblob WHERE id=?",
                             (keyid, ))
        name,val = res
        return (name, loads(str(val)))

    def _getDict(self, tableid, dictid):
        # returns a dict object
        # get all the key/type for that dictid
        searchstr = "SELECT keyid,type FROM %s WHERE dictid=?" % tableid
        res = self._FetchAll(searchstr, (dictid, ))
        d = {}
        for keyid, ktype in res:
            if ktype == DATA_TYPE_INT:
                keyname, keyval = self._getIntVal(keyid)
            elif ktype == DATA_TYPE_STR:
                keyname, keyval = self._getStrVal(keyid)
            elif ktype == DATA_TYPE_BLOB:
                keyname, keyval = self._getBlobVal(keyid)
            d[keyname] = keyval
        return d

    def getFullTestInfo(self, testid):
        """
        Returns a tuple with the following info:
        * the testrun id in which it was executed
        * the type of the test
        * the arguments (dictionnary)
        * the results (checklist dictionnary)
        * the result percentage
        * the extra information (dictionnary)
        * the output files (dictionnary)
        """
        searchstr = "SELECT testrunid,type,arguments,results,resultpercentage,extrainfo,outputfiles FROM test WHERE id=?"
        testrunid,ttype,argid,resid,resperc,extraid,outputfilesid = self._FetchOne(searchstr, (testid, ))
        args = self._getDict("argumentsdicts", argid)
        results = self._getDict("checklistdicts", resid)
        extras = self._getDict("extrainfodicts", extraid)
        outputfiles = self._getDict("outputfiledicts", outputfilesid)
        return (testrunid, ttype, args, results, resperc, extras, outputfiles)
