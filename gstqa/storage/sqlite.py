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
from gstqa.monitor import Monitor
try:
    # In Python 2.5, this is part of the standard library:
    from sqlite3 import dbapi2 as sqlite
except ImportError:
    # Previous versions have this as external dependency...
    from pysqlite2 import dbapi2 as sqlite
from cPickle import dumps, loads

# New dictionnaries table have the following name
# <container name>_<dictionnary name>_dict

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
   resultpercentage FLOAT
);

CREATE TABLE subtests (
   testid INTEGER PRIMARY KEY,
   scenarioid INTEGER
);

CREATE TABLE monitor (
   id INTEGER PRIMARY KEY,
   testid INTEGER,
   type TEXT,
   resultpercentage FLOAT
);

CREATE TABLE testclassinfo (
   type TEXT PRIMARY KEY,
   parent TEXT,
   description TEXT,
   fulldescription TEXT
);

CREATE TABLE monitorclassinfo (
   type TEXT PRIMARY KEY,
   parent TEXT,
   description TEXT
);

CREATE TABLE testrun_environment_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   intvalue INTEGER,
   txtvalue TXT,
   blobvalue BLOB
);

CREATE TABLE test_arguments_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   intvalue INTEGER,
   txtvalue TXT,
   blobvalue BLOB
);

CREATE TABLE test_checklist_list (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   intvalue INTEGER
);

CREATE TABLE test_extrainfo_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   intvalue INTEGER,
   txtvalue TXT,
   blobvalue BLOB
);

CREATE TABLE test_outputfiles_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TXT
);

CREATE TABLE monitor_arguments_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   intvalue INTEGER,
   txtvalue TXT,
   blobvalue BLOB
);

CREATE TABLE monitor_checklist_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   intvalue INTEGER
);

CREATE TABLE monitor_extrainfo_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   intvalue INTEGER,
   txtvalue TXT,
   blobvalue BLOB
);

CREATE TABLE monitor_outputfiles_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TXT
);

CREATE TABLE testclassinfo_arguments_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   blobvalue BLOB
);

CREATE TABLE testclassinfo_checklist_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TXT
);

CREATE TABLE testclassinfo_extrainfo_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TXT
);

CREATE TABLE testclassinfo_outputfiles_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TXT
);

CREATE TABLE monitorclassinfo_arguments_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TXT
);

CREATE TABLE monitorclassinfo_checklist_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TXT
);

CREATE TABLE monitorclassinfo_extrainfo_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TXT
);

CREATE TABLE monitorclassinfo_outputfiles_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TXT
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
        self.con = sqlite.connect(self.path, check_same_thread=False)

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
        for tblname in ["version", "testrun", "client",
                        "test", "subtests", "monitor", "testclassinfo",
                        "monitorclassinfo",
                        "testrun_environment_dict",
                        "test_arguments_dict", "test_checklist_list",
                        "test_extrainfo_dict", "test_outputfiles_dict",
                        "monitor_arguments_dict", "monitor_checklist_dict",
                        "monitor_extrainfo_dict", "monitor_outputfiles_dict",
                        "testclassinfo_arguments_dict", "testclassinfo_checklist_dict",
                        "testclassinfo_extrainfo_dict", "testclassinfo_outputfiles_dict",
                        "monitorclassinfo_arguments_dict", "monitorclassinfo_checklist_dict",
                        "monitorclassinfo_extrainfo_dict", "monitorclassinfo_outputfiles_dict"
                        ]:
            if not tblname in tables:
                return False
        return True

    def _ExecuteCommit(self, instruction, *args, **kwargs):
        # Convenience function to call execute and commit in one line
        # returns the last row id
        commit = kwargs.pop("commit", True)
        debug("%s args:%r kwargs:%r", instruction, args, kwargs)
        cur = self.con.cursor()
        cur.execute(instruction, *args, **kwargs)
        if commit:
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

    def _storeDict(self, dicttable, containerid, pdict):
        pdict = self._conformDict(pdict)

        if not pdict:
            # empty dictionnary
            debug("Empty dictionnary, returning")
            return

        insertstr = "INSERT INTO %s (id, containerid, name, %s) VALUES (NULL, ?, ?, ?)"
        cur = self.con.cursor()
        for key,value in pdict.iteritems():
            debug("Adding key:%s , value:%r", key, value)
            val = value
            if isinstance(value, int):
                valstr = "intvalue"
            elif isinstance(value, basestring):
                valstr = "txtvalue"
            else:
                valstr = "blobvalue"
                val = sqlite.Binary(dumps(value))
            comstr = insertstr % (dicttable, valstr)
            cur.execute(comstr, (containerid, key, val))

    def _storeList(self, dicttable, containerid, pdict):
        if not pdict:
            # empty dictionnary
            debug("Empty list, returning")
            return

        cur = self.con.cursor()
        insertstr = "INSERT INTO %s (id, containerid, name, %s) VALUES (NULL, ?, ?, ?)"
        for key,value in pdict:
            debug("Adding key:%s , value:%r", key, value)
            val = value
            if isinstance(value, int):
                valstr = "intvalue"
            elif isinstance(value, basestring):
                valstr = "txtvalue"
            else:
                valstr = "blobvalue"
                val = sqlite.Binary(dumps(value))
            comstr = insertstr % (dicttable, valstr)
            cur.execute(comstr, (containerid, key, val))

    def _storeTestArgumentsDict(self, testid, dict):
        return self._storeDict("test_arguments_dict", testid, dict)

    def _storeTestCheckListList(self, testid, dict):
        return self._storeList("test_checklist_list", testid, dict)

    def _storeTestExtraInfoDict(self, testid, dict):
        return self._storeDict("test_extrainfo_dict", testid, dict)

    def _storeTestOutputFileDict(self, testid, dict):
        return self._storeDict("test_outputfiles_dict", testid, dict)

    def _storeMonitorArgumentsDict(self, monitorid, dict):
        return self._storeDict("monitor_arguments_dict", monitorid, dict)

    def _storeMonitorCheckListDict(self, monitorid, dict):
        return self._storeDict("monitor_checklist_dict", monitorid, dict)

    def _storeMonitorExtraInfoDict(self, monitorid, dict):
        return self._storeDict("monitor_extrainfo_dict", monitorid, dict)

    def _storeMonitorOutputFileDict(self, monitorid, dict):
        return self._storeDict("monitor_outputfiles_dict", monitorid, dict)

    def _storeTestClassArgumentsDict(self, testclassinfoid, dict):
        return self._storeDict("testclassinfo_arguments_dict", testclassinfoid, dict)

    def _storeTestClassCheckListDict(self, testclassinfoid, dict):
        return self._storeDict("testclassinfo_checklist_dict", testclassinfoid, dict)

    def _storeTestClassExtraInfoDict(self, testclassinfoid, dict):
        return self._storeDict("testclassinfo_extrainfo_dict", testclassinfoid, dict)

    def _storeTestClassOutputFileDict(self, testclassinfoid, dict):
        return self._storeDict("testclassinfo_outputfiles_dict", testclassinfoid, dict)

    def _storeMonitorClassArgumentsDict(self, monitorclassinfoid, dict):
        return self._storeDict("monitorclassinfo_arguments_dict", monitorclassinfoid, dict)

    def _storeMonitorClassCheckListDict(self, monitorclassinfoid, dict):
        return self._storeDict("monitorclassinfo_checklist_dict", monitorclassinfoid, dict)

    def _storeMonitorClassExtraInfoDict(self, monitorclassinfoid, dict):
        return self._storeDict("monitorclassinfo_extrainfo_dict", monitorclassinfoid, dict)

    def _storeMonitorClassOutputFileDict(self, monitorclassinfoid, dict):
        return self._storeDict("monitorclassinfo_outputfiles_dict", monitorclassinfoid, dict)

    def _storeEnvironmentDict(self, testrunid, dict):
        return self._storeDict("testrun_environment_dict", testrunid, dict)

    def _insertTestClassInfo(self, tclass):
        ctype = tclass.__dict__.get("__test_name__")
        if len(self._FetchAll("SELECT * FROM testclassinfo WHERE type=?",
                              (ctype, ))) >= 1:
            return False
        # get info
        desc = tclass.__dict__.get("__test_description__")
        fdesc = tclass.__dict__.get("__test_full_description__")
        args = tclass.__dict__.get("__test_arguments__")
        checklist = tclass.__dict__.get("__test_checklist__")
        extrainfo = tclass.__dict__.get("__test_extra_infos__")
        outputfiles = tclass.__dict__.get("__test_output_files__")
        if tclass == Test:
            parent = None
        else:
            parent = tclass.__base__.__dict__.get("__test_name__")

        # insert into db
        insertstr = "INSERT INTO testclassinfo (type, parent, description, fulldescription) VALUES (?, ?, ?, ?)"
        tcid = self._ExecuteCommit(insertstr, (ctype, parent, desc, fdesc))

        # store the dicts
        self._storeTestClassArgumentsDict(tcid, args)
        self._storeTestClassCheckListDict(tcid, checklist)
        self._storeTestClassExtraInfoDict(tcid, extrainfo)
        self._storeTestClassOutputFileDict(tcid, outputfiles)
        self.con.commit()
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
            if not self._insertTestClassInfo(cl):
                break
            if cl == Test:
                break

    def _insertMonitorClassInfo(self, tclass):
        ctype = tclass.__dict__.get("__monitor_name__")
        if len(self._FetchAll("SELECT * FROM monitorclassinfo WHERE type=?",
                              (ctype, ))) >= 1:
            return False
        # get info
        desc = tclass.__dict__.get("__monitor_description__")
        args = tclass.__dict__.get("__monitor_arguments__")
        checklist = tclass.__dict__.get("__monitor_checklist__")
        extrainfo = tclass.__dict__.get("__monitor_extra_infos__")
        outputfiles = tclass.__dict__.get("__monitor_output_files__")
        if tclass == Monitor:
            parent = None
        else:
            parent = tclass.__base__.__dict__.get("__monitor_name__")

        # insert into db
        insertstr = "INSERT INTO monitorclassinfo (type, parent, description) VALUES (?, ?, ?)"
        tcid = self._ExecuteCommit(insertstr, (ctype, parent, desc))

        # store the dicts
        self._storeMonitorClassArgumentsDict(tcid, args)
        self._storeMonitorClassCheckListDict(tcid, checklist)
        self._storeMonitorClassExtraInfoDict(tcid, extrainfo)
        self._storeMonitorClassOutputFileDict(tcid, outputfiles)
        self.con.commit()
        return True

    def _storeMonitorClassInfo(self, monitorinstance):
        # check if we don't already have info for this class
        existstr = "SELECT * FROM monitorclassinfo WHERE type=?"
        res = self._FetchAll(existstr, (monitorinstance.__monitor_name__, ))
        if len(res) >= 1:
            # type already exists, returning
            return
        # we need an inverted mro (so we can now the parent class)
        for cl in monitorinstance.__class__.mro():
            if not self._insertMonitorClassInfo(cl):
                break
            if cl == Monitor:
                break



    # public storage API

    def _setClientInfo(self, softwarename, clientname, user, id=None):
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

    def setClientInfo(self, softwarename, clientname, user, id=None):
        self._lock.acquire()
        self._setClientInfo(softwarename, clientname, user)
        self._lock.release()

    def startNewTestRun(self, testrun):
        self._lock.acquire()
        self._startNewTestRun(testrun)
        self._lock.release()

    def _startNewTestRun(self, testrun):
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
            self._storeEnvironmentDict(self.__testrunid, envdict)
        self.__testrun = testrun
        debug("Got testrun id %d", self.__testrunid)

    def endTestRun(self, testrun):
        self._lock.acquire()
        self._endTestRun(testrun)
        self._lock.release()

    def _endTestRun(self, testrun):
        debug("testrun:%r", testrun)
        if not self.__testrun == testrun:
            # add the testrun since it wasn't done before
            self._startNewTestRun(testrun)
        updatestr = "UPDATE testrun SET stoptime=? WHERE id=?"
        self._ExecuteCommit(updatestr, (testrun._stoptime, self.__testrunid))
        debug("updated")

    def newTestStarted(self, testrun, test, commit=True):
        self._lock.acquire()
        self._newTestStarted(testrun, test, commit)
        self._lock.release()

    def _newTestStarted(self, testrun, test, commit=True):
        if not isinstance(test, Test):
            raise TypeError("test isn't a Test instance !")
        if not self.__testrun == testrun:
            self._startNewTestRun(testrun)
        debug("test:%r", test)
        insertstr = "INSERT INTO test (id, testrunid, type) VALUES (NULL, ?, ?)"
        testid = self._ExecuteCommit(insertstr,
                                     (self.__testrunid, test.__test_name__),
                                     commit=commit)
        debug("got testid %d", testid)
        self.__tests[test] = testid


    def newTestFinished(self, testrun, test):
        self._lock.acquire()
        self._newTestFinished(testrun, test)
        self._lock.release()

    def _newTestFinished(self, testrun, test):
        if not self.__testrun == testrun:
            self._startNewTestRun(testrun)
        if not self.__tests.has_key(test):
            self._newTestStarted(testrun, test, commit=False)
        tid = self.__tests[test]
        debug("test:%r:%d", test, tid)
        # if it's a scenario, fill up the subtests
        if isinstance(test, Scenario):
            sublist = []
            for sub in test.tests:
                self._newTestFinished(testrun, sub)
            # now add those to the subtests table
            insertstr = "INSERT INTO subtests (testid, scenarioid) VALUES (?,?)"
            for sub in test.tests:
                self._ExecuteCommit(insertstr, (self.__tests[sub],
                                                self.__tests[test]))

        # store the dictionnaries
        self._storeTestArgumentsDict(tid, test.getArguments())
        self._storeTestCheckListList(tid, test.getCheckList())
        self._storeTestExtraInfoDict(tid, test.getExtraInfo())
        self._storeTestOutputFileDict(tid, test.getOutputFiles())
        self.con.commit()

        # finally update the test
        updatestr = "UPDATE test SET resultpercentage=? WHERE id=?"
        resultpercentage = test.getSuccessPercentage()
        self._ExecuteCommit(updatestr, (resultpercentage, tid))
        self._storeTestClassInfo(test)

        # and on to the monitors
        for monitor in test._monitorinstances:
            self._storeMonitor(monitor, tid)

    def _storeMonitor(self, monitor, testid):
        insertstr = """
        INSERT INTO monitor (id, testid, type, resultpercentage)
        VALUES (NULL, ?, ?, ?)
        """
        # store monitor
        mid = self._ExecuteCommit(insertstr, (testid, monitor.__monitor_name__,
                                              monitor.getSuccessPercentage()))
        # store related dictionnaries
        self._storeMonitorArgumentsDict(mid, monitor.getArguments())
        self._storeMonitorCheckListDict(mid, monitor.getCheckList())
        self._storeMonitorExtraInfoDict(mid, monitor.getExtraInfo())
        self._storeMonitorOutputFileDict(mid, monitor.getOutputFiles())
        self.con.commit()
        self._storeMonitorClassInfo(monitor)

    # public retrieval API

    def _getDict(self, tablename, containerid, blobonly=False, txtonly=False, intonly=False):
        # returns a dict object
        # get all the key/type for that dictid
        searchstr = "SELECT * FROM %s WHERE containerid=?" % tablename
        res = self._FetchAll(searchstr, (containerid, ))

        d = {}
        for row in res:
            id, containerid, name = row[:3]
            if intonly or txtonly:
                val = row[3]
            elif blobonly:
                val = loads(str(row[3]))
            else:
                # we need to figure it out
                ival, tval, bval = row[3:]
                if not ival == None:
                    val = ival
                elif not tval == None:
                    val = tval
                else:
                    val = loads(str(bval))
            d[name] = val
        return d

    def _getList(self, tablename, containerid, blobonly=False, txtonly=False, intonly=False):
        # returns a list object
        # get all the key, value for that dictid
        searchstr = "SELECT * FROM %s WHERE containerid=?" % tablename
        res = self._FetchAll(searchstr, (containerid, ))

        d = []
        for row in res:
            id, containerid, name = row[:3]
            if intonly or txtonly:
                val = row[3]
            elif blobonly:
                val = loads(str(row[3]))
            else:
                # we need to figure it out
                ival, tval, bval = row[3:]
                if not ival == None:
                    val = ival
                elif not tval == None:
                    val = tval
                else:
                    val = loads(str(bval))
            d.append((name, val))
        return d


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
        return self._getDict("testrun_environment_dict", testrunid)

    def getTestsForTestRun(self, testrunid, withscenarios=True):
        debug("testrunid:%d", testrunid)
        liststr = "SELECT id FROM test WHERE testrunid=?"
        res = self._FetchAll(liststr, (testrunid, ))
        if not res:
            return []
        tmp = list(zip(*res)[0])
        if not withscenarios:
            scenarios = self.getScenariosForTestRun(testrunid)
            print tmp
            print scenarios
            for x in scenarios.keys():
                tmp.remove(x)
        return tmp

    def getScenariosForTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = "SELECT test.id,subtests.testid FROM test INNER JOIN subtests ON test.id=subtests.scenarioid WHERE test.testrunid=?"
        res = self._FetchAll(liststr, (testrunid, ))
        if not res:
            return []
        # make list unique
        d = {}
        for scenarioid, subtestid in res:
            if not scenarioid in d.keys():
                d[scenarioid] = [subtestid]
            else:
                d[scenarioid].append(subtestid)
        return d

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

    def getFullTestInfo(self, testid):
        """
        Returns a tuple with the following info:
        * the testrun id in which it was executed
        * the type of the test
        * the arguments (dictionnary)
        * the results (checklist list)
        * the result percentage
        * the extra information (dictionnary)
        * the output files (dictionnary)
        """
        searchstr = "SELECT testrunid,type,resultpercentage FROM test WHERE id=?"
        res = self._FetchOne(searchstr, (testid, ))
        if not res:
            return (None, None, None, None, None, None, None)
        testrunid,ttype,resperc = res
        args = self._getDict("test_arguments_dict", testid)
        results = self._getList("test_checklist_list", testid, intonly=True)
        extras = self._getDict("test_extrainfo_dict", testid)
        outputfiles = self._getDict("test_outputfiles_dict", testid, txtonly=True)
        return (testrunid, ttype, args, results, resperc, extras, outputfiles)

    def getMonitorsIDForTest(self, testid):
        """
        Returns a list of monitorid for the given test
        """
        searchstr = "SELECT id FROM monitor WHERE testid=?"
        res = self._FetchAll(searchstr, (testid, ))
        if not res:
            return []
        return list(zip(*res)[0])

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
        searchstr = "SELECT testid,type,resultpercentage FROM monitor WHERE id=?"
        res = self._FetchOne(searchstr, (monitorid, ))
        if not res:
            return (None, None, None, None, None, None, None)
        testid,mtype,resperc = res
        args = self._getDict("monitor_arguments_dict", monitorid)
        results = self._getDict("monitor_checklist_dict", monitorid, intonly=True)
        extras = self._getDict("monitor_extrainfo_dict", monitorid)
        outputfiles = self._getDict("monitor_outputfiles_dict", monitorid, txtonly=True)
        return (testid, mtype, args, results, resperc, extras, outputfiles)

