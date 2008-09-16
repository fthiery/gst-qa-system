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
import threading
from weakref import WeakKeyDictionary
from insanity.log import error, warning, debug
from insanity.scenario import Scenario
from insanity.test import Test
from insanity.monitor import Monitor
from insanity.utils import reverse_dict, map_dict, map_list
from insanity.storage.dbstorage import DBStorage, DB_SCHEME, DB_SCHEME_VERSION
from insanity.storage.async import AsyncStorage, queuemethod, finalqueuemethod
try:
    # In Python 2.5, this is part of the standard library:
    from sqlite3 import dbapi2 as sqlite
except ImportError:
    # Previous versions have this as external dependency...
    from pysqlite2 import dbapi2 as sqlite
from cPickle import dumps, loads

#
# FIXME : only accepts one client info at a time !
#

class SQLiteStorage(DBStorage, AsyncStorage):
    """
    Stores data in a sqlite db

    The 'async' setting will allow all writes to be serialized in a separate thread,
    allowing the testing to carry on.

    If you are only using the database for reading information, you should use
    async=False and only use the storage object from one thread.
    """

    def __init__(self, path, async=True, *args, **kwargs):
        self.path = path
        self.con = None
        self._lock = threading.Lock()
        self.__clientid = None

        # key: testrun, value: testrunid
        self.__testruns = WeakKeyDictionary()
        self.__tests = WeakKeyDictionary()

        # cache of mappings for testclassinfo
        # { 'testtype' : { 'dictname' : mapping } }
        self.__tcmapping = {}
        # cache of mappings for testclassinfo
        # { 'testtype' : { 'dictname' : mapping } }
        self.__mcmapping = {}
        DBStorage.__init__(self, *args, **kwargs)
        AsyncStorage.__init__(self, async)


    # DataStorage methods implementation
    @queuemethod
    def setClientInfo(self, softwarename, clientname, user):
        # check if that triplet is already present
        debug("softwarename:%s, clientname:%s, user:%s",
              softwarename, clientname, user)
        existstr = "SELECT id FROM client WHERE software=? AND name=? AND user=?"
        res = self._FetchAll(existstr, (softwarename, clientname, user))
        if len(res) == 1 :
            debug("Entry already present !")
            key = res[0][0]
        elif len(res) > 1:
            warning("More than one similar entry ???")
            raise Exception("Several client entries with the same information, fix db!")
        else:
            insertstr = """
            INSERT INTO client (id, software, name, user) VALUES (NULL, ?,?,?)
            """
            key = self._ExecuteCommit(insertstr, (softwarename, clientname, user))
        debug("got id %d", key)
        # cache the key
        self.__clientid = key
        return key

    @queuemethod
    def startNewTestRun(self, testrun):
        self._startNewTestRun(testrun)

    @queuemethod
    def endTestRun(self, testrun):
        self._endTestRun(testrun)

    @queuemethod
    def newTestStarted(self, testrun, test, commit=True):
        self._newTestStarted(testrun, test, commit)

    @queuemethod
    def newTestFinished(self, testrun, test):
        self._newTestFinished(testrun, test)

    def listTestRuns(self):
        liststr = "SELECT id FROM testrun"
        res = self._FetchAll(liststr)
        debug("Got %d testruns", len(res))
        if len(res):
            return list(zip(*res)[0])
        return []

    def getTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = """
        SELECT clientid,starttime,stoptime
        FROM testrun WHERE id=?"""
        res = self._FetchAll(liststr, (testrunid, ))
        if len(res) == 0:
            debug("Testrun not available in DB")
            return (None, None, None)
        if len(res) > 1:
            warning("More than one testrun with the same id ! Fix DB !!")
            return (None, None, None)
        return res[0]

    def getTestsForTestRun(self, testrunid, withscenarios=True):
        debug("testrunid:%d", testrunid)
        liststr = "SELECT id FROM test WHERE testrunid=?"
        res = self._FetchAll(liststr, (testrunid, ))
        if not res:
            return []
        tmp = list(zip(*res)[0])
        if not withscenarios:
            scenarios = self.getScenariosForTestRun(testrunid)
            for sc in scenarios.keys():
                tmp.remove(sc)
        return tmp

    def getScenariosForTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = """
        SELECT test.id,subtests.testid
        FROM test
        INNER JOIN subtests
        ON test.id=subtests.scenarioid
        WHERE test.testrunid=?"""
        res = self._FetchAll(liststr, (testrunid, ))
        if not res:
            return {}
        # make list unique
        dc = {}
        for scenarioid, subtestid in res:
            if not scenarioid in dc.keys():
                dc[scenarioid] = [subtestid]
            else:
                dc[scenarioid].append(subtestid)
        return dc

    def getClientInfoForTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = """
        SELECT client.software,client.name,client.user
        FROM client,testrun
        WHERE client.id=testrun.clientid AND testrun.id=?"""
        res = self._FetchAll(liststr, (testrunid,))
        return res[0]


    # DBStorage methods implementation
    def openDatabase(self):
        debug("opening sqlite db for path '%s'", self.path)
        self.con = sqlite.connect(self.path, check_same_thread=False)
        # we do this so that we can store UTF8 strings in the database
        self.con.text_factory = str

    def createTables(self):
        # check if tables aren't already created
        if self._checkForTables():
            return
        debug("Calling db creation script")
        self.con.executescript(DB_SCHEME)
        self.con.commit()
        if self._checkForTables() == False:
            error("Tables were not created properly !!")
        # add database version
        cmstr = "INSERT INTO version (version, modificationtime) VALUES (?, ?)"
        self._ExecuteCommit(cmstr, (DB_SCHEME_VERSION, int(time.time())))
        debug("Tables properly created")

    def _shutDown(self, callback, *args, **kwargs):
        """ Shut down the database, the callback will be called when it's finished
        processing pending actions. """
        if callback == None or not callable(callback):
            debug("No callback provided or not callable")
            return
        self.queueFinalAction(callback, *args, **kwargs)

    def _updateDatabaseFrom1To2(self):
        create1to2 = """
        CREATE INDEX test_type_idx ON test (type);
        """
        # Add usedtests_testrun table and index
        self.con.executescript(create1to2)
        self.con.commit()

    def _updateDatabase(self, oldversion, newversion):
        if oldversion < 2:
            self._updateDatabaseFrom1To2()

        # finally update the db version
        cmstr = "UPDATE version SET version=?,modificationtime=? WHERE version=?"
        self._ExecuteCommit(cmstr, (DB_SCHEME_VERSION, int (time.time()), oldversion))
        return True

    def _checkForTables(self):
        # return False if the tables aren't created
        tables = self._getAllTables()
        if len(tables) == 0 or not "version" in tables:
            return False

        ver = self._getDatabaseSchemeVersion()
        if not ver:
            return False
        if ver > DB_SCHEME_VERSION:
            warning("Tables were created using a newer database scheme than what we support")
            return False
        if ver == DB_SCHEME_VERSION:
            return True

        # FIXME : if ver != DB_SCHEME_VERSION, then update the database
        return self._updateDatabase(ver, DB_SCHEME_VERSION)

    def _ExecuteCommit(self, instruction, *args, **kwargs):
        # Convenience function to call execute and commit in one line
        # returns the last row id
        commit = kwargs.pop("commit", True)
        debug("%s args:%r kwargs:%r", instruction, args, kwargs)
        self._lock.acquire()
        cur = self.con.cursor()
        cur.execute(instruction, *args, **kwargs)
        if commit:
            self.con.commit()
        self._lock.release()
        return cur.lastrowid

    def _FetchAll(self, instruction, *args, **kwargs):
        # Convenience function to fetch all results
        self._lock.acquire()
        cur = self.con.cursor()
        cur.execute(instruction, *args, **kwargs)
        res = cur.fetchall()
        self._lock.release()
        return res

    def _FetchOne(self, instruction, *args, **kwargs):
        # Convenience function to fetch all results
        self._lock.acquire()
        cur = self.con.cursor()
        cur.execute(instruction, *args, **kwargs)
        res = cur.fetchone()
        self._lock.release()
        return res

    def _getAllTables(self):
        """
        Returns the name of all the available tables in the currently
        loaded database.
        """
        checktables = """
        SELECT name FROM sqlite_master
        WHERE type='table'
        ORDER BY name;
        """
        return [x[0] for x in self.con.execute(checktables).fetchall()]

    def _getDatabaseSchemeVersion(self):
        """
        Returns the scheme version of the currently loaded databse

        Returns None if there's no properly configured scheme, else
        returns the version
        """
        tables = self._getAllTables()
        if not "version" in tables:
            return None
        # check if the version is the same as the current one
        res = self._FetchOne("SELECT version FROM version")
        if res == None:
            return None
        return res[0]

    # dictionnary storage methods
    def _conformDict(self, pdict):
        # transforms the dictionnary values to types compatible with
        # the DB storage format
        if pdict == None:
            return None
        res = {}
        for key, value in pdict.iteritems():
            res[key] = value
        return res

    def _storeDict(self, dicttable, containerid, pdict):
        pdict = self._conformDict(pdict)

        if not pdict:
            # empty dictionnary
            debug("Empty dictionnary, returning")
            return

        insertstr = """INSERT INTO %s (id, containerid, name, %s)
        VALUES (NULL, ?, ?, ?)"""
        self._lock.acquire()
        cur = self.con.cursor()
        for key, value in pdict.iteritems():
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
        self._lock.release()

    def _storeList(self, dicttable, containerid, pdict):
        if not pdict:
            # empty dictionnary
            debug("Empty list, returning")
            return

        self._lock.acquire()
        cur = self.con.cursor()
        insertstr = """INSERT INTO %s (id, containerid, name, %s)
        VALUES (NULL, ?, ?, ?)"""
        for key, value in pdict:
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
        self._lock.release()

    def _storeTestArgumentsDict(self, testid, dic, testtype):
        # transform the dictionnary from names to ids
        maps = self._getTestClassArgumentMapping(testtype)
        return self._storeDict("test_arguments_dict",
                               testid, map_dict(dic, maps))

    def _storeTestCheckListList(self, testid, dic, testtype):
        maps = self._getTestClassCheckListMapping(testtype)
        return self._storeList("test_checklist_list",
                               testid, map_list(dic, maps))

    def _storeTestExtraInfoDict(self, testid, dic, testtype):
        maps = self._getTestClassExtraInfoMapping(testtype)
        return self._storeDict("test_extrainfo_dict",
                               testid, map_dict(dic, maps))

    def _storeTestOutputFileDict(self, testid, dic, testtype):
        maps = self._getTestClassOutputFileMapping(testtype)
        return self._storeDict("test_outputfiles_dict",
                               testid, map_dict(dic, maps))

    def _storeMonitorArgumentsDict(self, monitorid, dic, monitortype):
        maps = self._getMonitorClassArgumentMapping(monitortype)
        return self._storeDict("monitor_arguments_dict",
                               monitorid, map_dict(dic, maps))

    def _storeMonitorCheckListDict(self, monitorid, dic, monitortype):
        maps = self._getMonitorClassCheckListMapping(monitortype)
        return self._storeDict("monitor_checklist_dict",
                               monitorid, map_dict(dic, maps))

    def _storeMonitorExtraInfoDict(self, monitorid, dic, monitortype):
        maps = self._getMonitorClassExtraInfoMapping(monitortype)
        return self._storeDict("monitor_extrainfo_dict",
                               monitorid, map_dict(dic, maps))

    def _storeMonitorOutputFileDict(self, monitorid, dic, monitortype):
        maps = self._getMonitorClassOutputFileMapping(monitortype)
        return self._storeDict("monitor_outputfiles_dict",
                               monitorid, map_dict(dic, maps))

    def _storeTestClassArgumentsDict(self, testclassinfoid, dic):
        return self._storeDict("testclassinfo_arguments_dict",
                               testclassinfoid, dic)

    def _storeTestClassCheckListDict(self, testclassinfoid, dic):
        return self._storeDict("testclassinfo_checklist_dict",
                               testclassinfoid, dic)

    def _storeTestClassExtraInfoDict(self, testclassinfoid, dic):
        return self._storeDict("testclassinfo_extrainfo_dict",
                               testclassinfoid, dic)

    def _storeTestClassOutputFileDict(self, testclassinfoid, dic):
        return self._storeDict("testclassinfo_outputfiles_dict",
                               testclassinfoid, dic)

    def _storeMonitorClassArgumentsDict(self, monitorclassinfoid, dic):
        return self._storeDict("monitorclassinfo_arguments_dict",
                               monitorclassinfoid, dic)

    def _storeMonitorClassCheckListDict(self, monitorclassinfoid, dic):
        return self._storeDict("monitorclassinfo_checklist_dict",
                               monitorclassinfoid, dic)

    def _storeMonitorClassExtraInfoDict(self, monitorclassinfoid, dic):
        return self._storeDict("monitorclassinfo_extrainfo_dict",
                               monitorclassinfoid, dic)

    def _storeMonitorClassOutputFileDict(self, monitorclassinfoid, dic):
        return self._storeDict("monitorclassinfo_outputfiles_dict",
                               monitorclassinfoid, dic)

    def _storeEnvironmentDict(self, testrunid, dic):
        return self._storeDict("testrun_environment_dict",
                               testrunid, dic)

    def _insertTestClassInfo(self, tclass):
        ctype = tclass.__dict__.get("__test_name__").strip()
        searchstr = "SELECT * FROM testclassinfo WHERE type=?"
        if len(self._FetchAll(searchstr, (ctype, ))) >= 1:
            return False
        # get info
        desc = tclass.__dict__.get("__test_description__").strip()
        fdesc = tclass.__dict__.get("__test_full_description__")
        if fdesc:
            fdesc.strip()
        args = tclass.__dict__.get("__test_arguments__")
        checklist = tclass.__dict__.get("__test_checklist__")
        extrainfo = tclass.__dict__.get("__test_extra_infos__")
        outputfiles = tclass.__dict__.get("__test_output_files__")
        if tclass == Test:
            parent = None
        else:
            parent = tclass.__base__.__dict__.get("__test_name__").strip()

        # insert into db
        insertstr = """INSERT INTO testclassinfo
        (id, type, parent, description, fulldescription)
        VALUES (NULL, ?, ?, ?, ?)"""
        tcid = self._ExecuteCommit(insertstr, (ctype, parent, desc, fdesc))

        # store the dicts
        self._storeTestClassArgumentsDict(tcid, args)
        self._storeTestClassCheckListDict(tcid, checklist)
        self._storeTestClassExtraInfoDict(tcid, extrainfo)
        self._storeTestClassOutputFileDict(tcid, outputfiles)
        debug("done adding class info for %s [%d]", ctype, tcid)
        return True

    def _storeTestClassInfo(self, testinstance):
        # check if we don't already have info for this class
        debug("test name: %s", testinstance.__test_name__)
        existstr = "SELECT * FROM testclassinfo WHERE type=?"
        res = self._FetchAll(existstr, (testinstance.__test_name__, ))
        if len(res) > 0:
            # type already exists, returning
            return
        # we need an inverted mro (so we can know the parent class)
        for cl in testinstance.__class__.mro():
            if not self._insertTestClassInfo(cl):
                break
            if cl == Test:
                break

    def _insertMonitorClassInfo(self, tclass):
        ctype = tclass.__dict__.get("__monitor_name__").strip()
        searchstr = "SELECT * FROM monitorclassinfo WHERE type=?"
        if len(self._FetchAll(searchstr, (ctype, ))) >= 1:
            return False
        # get info
        desc = tclass.__dict__.get("__monitor_description__").strip()
        args = tclass.__dict__.get("__monitor_arguments__")
        checklist = tclass.__dict__.get("__monitor_checklist__")
        extrainfo = tclass.__dict__.get("__monitor_extra_infos__")
        outputfiles = tclass.__dict__.get("__monitor_output_files__")
        if tclass == Monitor:
            parent = None
        else:
            parent = tclass.__base__.__dict__.get("__monitor_name__").strip()

        # insert into db
        insertstr = """
        INSERT INTO monitorclassinfo (type, parent, description) VALUES (?, ?, ?)
        """
        tcid = self._ExecuteCommit(insertstr, (ctype, parent, desc))

        # store the dicts
        self._storeMonitorClassArgumentsDict(tcid, args)
        self._storeMonitorClassCheckListDict(tcid, checklist)
        self._storeMonitorClassExtraInfoDict(tcid, extrainfo)
        self._storeMonitorClassOutputFileDict(tcid, outputfiles)
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

    def _startNewTestRun(self, testrun):
        # create new testrun entry with client entry
        debug("testrun:%r", testrun)
        if not self.__clientid:
            raise Exception("Please specify client information before starting testruns")
        if testrun in self.__testruns.keys():
            warning("Testrun already started !")
            return
        insertstr = """
        INSERT INTO testrun (id, clientid, starttime, stoptime) VALUES (NULL, ?, ?, NULL)
        """
        testrunid = self._ExecuteCommit(insertstr,
                                        (self.__clientid,
                                         testrun._starttime))
        envdict = testrun.getEnvironment()
        if envdict:
            self._storeEnvironmentDict(testrunid, envdict)
        self.__testruns[testrun] = testrunid
        debug("Got testrun id %d", testrunid)
        return testrunid

    def _endTestRun(self, testrun):
        debug("testrun:%r", testrun)
        if not testrun in self.__testruns.keys():
            # add the testrun since it wasn't done before
            self._startNewTestRun(testrun)
        updatestr = "UPDATE testrun SET stoptime=? WHERE id=?"
        self._ExecuteCommit(updatestr, (testrun._stoptime, self.__testruns[testrun]))
        debug("updated")

    def _getTestTypeID(self, testtype):
        """
        Returns the test.id for the given testtype

        Returns None if there is no information regarding the given testtype
        """
        res = self._FetchOne("SELECT id FROM testclassinfo WHERE type=?",
                             (testtype, ))
        if res == None:
            return None
        return res[0]

    def _getMonitorTypeID(self, monitortype):
        """
        Returns the monitor.id for the given monitortype

        Returns None if there is no information regarding the given monitortype
        """
        res = self._FetchOne("SELECT id FROM monitorclassinfo WHERE type=?",
                             (monitortype, ))
        if res == None:
            return None
        return res[0]

    def _newTestStarted(self, testrun, test, commit=True):
        if not isinstance(test, Test):
            raise TypeError("test isn't a Test instance !")
        if not testrun in self.__testruns.keys():
            self._startNewTestRun(testrun)
        debug("test:%r", test)
        self._storeTestClassInfo(test)
        testtid = self._getTestTypeID(test.__test_name__)
        insertstr = "INSERT INTO test (id, testrunid, type) VALUES (NULL, ?, ?)"
        testid = self._ExecuteCommit(insertstr,
                                     (self.__testruns[testrun], testtid),
                                     commit=commit)
        debug("got testid %d", testid)
        self.__tests[test] = testid


    def _newTestFinished(self, testrun, test):
        debug("testrun:%r, test:%r", testrun, test)
        if not testrun in self.__testruns.keys():
            debug("different testrun, starting new one")
            self._startNewTestRun(testrun)
        if not self.__tests.has_key(test):
            debug("we don't have test yet, starting that one")
            self._newTestStarted(testrun, test, commit=False)
        tid = self.__tests[test]
        debug("test:%r:%d", test, tid)
        # if it's a scenario, fill up the subtests
        if isinstance(test, Scenario):
            debug("test is a scenario, adding subtests")
            for sub in test.tests:
                self._newTestFinished(testrun, sub)
            # now add those to the subtests table
            insertstr = "INSERT INTO subtests (testid, scenarioid) VALUES (?,?)"
            for sub in test.tests:
                self._ExecuteCommit(insertstr, (self.__tests[sub],
                                                self.__tests[test]))
            debug("done adding subtests")

        # store the dictionnaries
        self._storeTestArgumentsDict(tid, test.getArguments(),
                                     test.__test_name__)
        self._storeTestCheckListList(tid, test.getCheckList(),
                                     test.__test_name__)
        self._storeTestExtraInfoDict(tid, test.getExtraInfo(),
                                     test.__test_name__)
        self._storeTestOutputFileDict(tid, test.getOutputFiles(),
                                      test.__test_name__)

        # finally update the test
        updatestr = "UPDATE test SET resultpercentage=? WHERE id=?"
        resultpercentage = test.getSuccessPercentage()
        self._ExecuteCommit(updatestr, (resultpercentage, tid))

        # and on to the monitors
        for monitor in test._monitorinstances:
            self._storeMonitor(monitor, tid)
        debug("done adding information for test %d", tid)

    def _storeMonitor(self, monitor, testid):
        insertstr = """
        INSERT INTO monitor (id, testid, type, resultpercentage)
        VALUES (NULL, ?, ?, ?)
        """
        debug("monitor:%r:%d", monitor, testid)
        # store monitor
        self._storeMonitorClassInfo(monitor)

        monitortype = self._getMonitorTypeID(monitor.__monitor_name__)
        mid = self._ExecuteCommit(insertstr, (testid, monitortype,
                                              monitor.getSuccessPercentage()))
        # store related dictionnaries
        self._storeMonitorArgumentsDict(mid, monitor.getArguments(),
                                        monitor.__monitor_name__)
        self._storeMonitorCheckListDict(mid, monitor.getCheckList(),
                                        monitor.__monitor_name__)
        self._storeMonitorExtraInfoDict(mid, monitor.getExtraInfo(),
                                        monitor.__monitor_name__)
        self._storeMonitorOutputFileDict(mid, monitor.getOutputFiles(),
                                         monitor.__monitor_name__)

    # public retrieval API

    def _getDict(self, tablename, containerid, blobonly=False, txtonly=False,
                 intonly=False):
        # returns a dict object
        # get all the key/type for that dictid
        searchstr = "SELECT * FROM %s WHERE containerid=?" % tablename
        res = self._FetchAll(searchstr, (containerid, ))

        dc = {}
        for row in res:
            containerid, name = row[1:3]
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
                    val = str(tval)
                else:
                    val = loads(str(bval))
            dc[name] = val
        return dc

    def _getList(self, tablename, containerid, blobonly=False, txtonly=False,
                 intonly=False):
        # returns a list object
        # get all the key, value for that dictid
        searchstr = "SELECT * FROM %s WHERE containerid=?" % tablename
        res = self._FetchAll(searchstr, (containerid, ))

        dc = []
        for row in res:
            containerid, name = row[1:3]
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
                    val = str(tval)
                else:
                    val = loads(str(bval))
            dc.append((name, val))
        return dc


    def getEnvironmentForTestRun(self, testrunid):
        debug("testrunid", testrunid)
        return self._getDict("testrun_environment_dict", testrunid)

    def getFailedTestsForTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = """
        SELECT id
        FROM test
        WHERE testrunid=? AND resultpercentage<>100.0"""
        res = self._FetchAll(liststr, (testrunid, ))
        if not res:
            return []
        return list(zip(*res)[0])

    def getSucceededTestsForTestRun(self, testrunid):
        debug("testrunid:%d", testrunid)
        liststr = """
        SELECT id
        FROM test
        WHERE testrunid=? AND resultpercentage=100.0"""
        res = self._FetchAll(liststr, (testrunid, ))
        if not res:
            return []
        return list(zip(*res)[0])

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
        if not rawinfo:
            searchstr = """
            SELECT test.testrunid,testclassinfo.type,test.resultpercentage
            FROM test,testclassinfo
            WHERE test.id=? AND test.type=testclassinfo.id"""
        else:
            searchstr = """
            SELECT test.testrunid,test.type,test.resultpercentage
            FROM test
            WHERE test.id=?"""
        res = self._FetchOne(searchstr, (testid, ))
        if not res:
            return (None, None, None, None, None, None, None)
        testrunid, ttype, resperc = res
        args = self._getDict("test_arguments_dict", testid)
        results = self._getList("test_checklist_list", testid, intonly=True)
        extras = self._getDict("test_extrainfo_dict", testid)
        ofs = self._getDict("test_outputfiles_dict", testid, txtonly=True)
        if not rawinfo:
            args = map_dict(args,
                            reverse_dict(self._getTestClassArgumentMapping(ttype)))
            results = map_list(results,
                               reverse_dict(self._getTestClassCheckListMapping(ttype)))
            extras = map_dict(extras,
                              reverse_dict(self._getTestClassExtraInfoMapping(ttype)))
            ofs = map_dict(ofs,
                           reverse_dict(self._getTestClassOutputFileMapping(ttype)))
        return (testrunid, ttype, args, results, resperc, extras, ofs)

    def getTestClassInfo(self, testtype):
        searchstr = """SELECT id,parent,description,fulldescription
        FROM testclassinfo WHERE type=?"""
        res = self._FetchOne(searchstr, (testtype, ))
        if not res:
            return (None, None)
        tcid, rp, desc, fulldesc = res
        args = self._getDict("testclassinfo_arguments_dict", tcid, blobonly=True)
        checks = self._getDict("testclassinfo_checklist_dict", tcid, txtonly=True)
        extras = self._getDict("testclassinfo_extrainfo_dict", tcid, txtonly=True)
        outputfiles = self._getDict("testclassinfo_outputfiles_dict",
                                    tcid, txtonly=True)
        while rp:
            ptcid, prp = self._FetchOne(searchstr, (rp, ))[:2]
            args.update(self._getDict("testclassinfo_arguments_dict",
                                      ptcid, blobonly=True))
            checks.update(self._getDict("testclassinfo_checklist_dict",
                                        ptcid, txtonly=True))
            extras.update(self._getDict("testclassinfo_extrainfo_dict",
                                        ptcid, txtonly=True))
            outputfiles.update(self._getDict("testclassinfo_outputfiles_dict",
                                             ptcid, txtonly=True))
            rp = prp

        return (desc, fulldesc, args, checks, extras, outputfiles)

    def _getClassMapping(self, classtable, classtype, dictname):
        # returns a dictionnary of name : id mapping for a test's
        # arguments, including the parent class mapping
        searchstr = "SELECT parent,id FROM %s WHERE type=?" % classtable
        res = self._FetchOne(searchstr, (classtype, ))
        if not res:
            return {}
        rp, tcid = res
        mapsearch = """
        SELECT name,id
        FROM %s
        WHERE containerid=?""" % dictname
        maps = self._FetchAll(mapsearch, (tcid, ))
        while rp:
            res = self._FetchOne(searchstr, (rp, ))
            rp, tcid = res
            vals = self._FetchAll(mapsearch, (tcid, ))
            maps.extend(vals)

        return dict(maps)

    def _getTestClassMapping(self, testtype, dictname):
        # Search in the cache first
        if testtype in self.__tcmapping:
            if dictname in self.__tcmapping[testtype]:
                return self.__tcmapping[testtype][dictname]
        maps = self._getClassMapping("testclassinfo", testtype, dictname)
        if not testtype in self.__tcmapping:
            self.__tcmapping[testtype] = {}
        self.__tcmapping[testtype][dictname] = dict(maps)
        return self.__tcmapping[testtype][dictname]

    def _getMonitorClassMapping(self, monitortype, dictname):
        # Search in the cache first
        if monitortype in self.__mcmapping:
            if dictname in self.__mcmapping[monitortype]:
                return self.__mcmapping[monitortype][dictname]
        maps = self._getClassMapping("monitorclassinfo", monitortype, dictname)
        if not monitortype in self.__mcmapping:
            self.__mcmapping[monitortype] = {}
        self.__mcmapping[monitortype][dictname] = dict(maps)
        return self.__mcmapping[monitortype][dictname]

    def _getTestClassArgumentMapping(self, testtype):
        return self._getTestClassMapping(testtype, "testclassinfo_arguments_dict")

    def _getTestClassCheckListMapping(self, testtype):
        return self._getTestClassMapping(testtype, "testclassinfo_checklist_dict")

    def _getTestClassExtraInfoMapping(self, testtype):
        return self._getTestClassMapping(testtype, "testclassinfo_extrainfo_dict")

    def _getTestClassOutputFileMapping(self, testtype):
        return self._getTestClassMapping(testtype, "testclassinfo_outputfiles_dict")

    def _getMonitorClassArgumentMapping(self, monitortype):
        return self._getMonitorClassMapping(monitortype,
                                            "monitorclassinfo_arguments_dict")

    def _getMonitorClassCheckListMapping(self, monitortype):
        return self._getMonitorClassMapping(monitortype,
                                            "monitorclassinfo_checklist_dict")

    def _getMonitorClassExtraInfoMapping(self, monitortype):
        return self._getMonitorClassMapping(monitortype,
                                            "monitorclassinfo_extrainfo_dict")

    def _getMonitorClassOutputFileMapping(self, monitortype):
        return self._getMonitorClassMapping(monitortype,
                                            "monitorclassinfo_outputfiles_dict")


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
        res = self.getMonitorInfo(monitorid)
        if res == (None, None, None):
            return (None, None, None, None, None, None, None)
        testid, mtype, resperc = res
        args = map_dict(self._getDict("monitor_arguments_dict", monitorid),
                        reverse_dict(self._getMonitorClassArgumentMapping(mtype)))
        results = map_dict(self._getDict("monitor_checklist_dict",
                                         monitorid, intonly=True),
                           reverse_dict(self._getMonitorClassCheckListMapping(mtype)))
        extras = map_dict(self._getDict("monitor_extrainfo_dict", monitorid),
                          reverse_dict(self._getMonitorClassExtraInfoMapping(mtype)))
        outputfiles = map_dict(self._getDict("monitor_outputfiles_dict",
                                             monitorid, txtonly=True),
                               reverse_dict(self._getMonitorClassOutputFileMapping(mtype)))
        return (testid, mtype, args, results, resperc, extras, outputfiles)

    def getMonitorInfo(self, monitorid):
        """
        Returns a tuple with the following info:
        * the ID of the test on which the monitor was applied
        * the type of the monitor
        * the result percentage
        """
        searchstr = """
        SELECT monitor.testid,monitorclassinfo.type,monitor.resultpercentage
        FROM monitor,monitorclassinfo
        WHERE monitor.id=? AND monitorclassinfo.id=monitor.type"""
        res = self._FetchOne(searchstr, (monitorid, ))
        if not res:
            return (None, None, None)
        return res


    def findTestsByArgument(self, testtype, arguments, testrunid=None, monitorids=None):
        searchstr = """
        SELECT test.id
        FROM test, test_arguments_dict
        WHERE test.id=test_arguments_dict.containerid """
        searchargs = []
        if not testrunid == None:
            searchstr += "AND test.testrunid=? "
            searchargs.append(testrunid)
        searchstr += "AND test.type=? "
        searchargs.append(testtype)

        # we'll now recursively search for the compatible tests
        # we first start to look for all tests matching the first argument
        # then from those tests, find those that match the second,...
        # Break out from the loop whenever there's nothing more matching

        res = []

        for key, val in arguments.iteritems():
            if not res == []:
                tmpsearch = "AND test.id in (%s) " % ', '.join([str(x) for x in res])
            else:
                tmpsearch = ""
            value = val
            if isinstance(val, int):
                valstr = "intvalue"
            elif isinstance(val, basestring):
                valstr = "txtvalue"
            else:
                valstr = "blobvalue"
                value = sqlite.Binary(dumps(val))
            tmpsearch += "AND test_arguments_dict.name=? AND test_arguments_dict.%s=?" % valstr
            tmpargs = searchargs[:]
            tmpargs.extend([key, value])
            tmpres = self._FetchAll(searchstr + tmpsearch, tuple(tmpargs))
            res = []
            if tmpres == []:
                break
            tmp2 = list(zip(*tmpres)[0])
            # transform this into a unique list
            for i in tmp2:
                if not i in res:
                    res.append(i)

        # finally... make sure that for the monitors that both test
        # share, they have the same arguments
        if not monitorids == None:
            tmp = []
            monitors = [self.getFullMonitorInfo(x) for x in monitorids]
            for pid in res:
                similar = True
                pm = [self.getFullMonitorInfo(x) for x in self.getMonitorsIDForTest(pid)]

                samemons = []
                # for each candidate monitors
                for tid, mtype, margs, mres, mresperc, mextra, mout in pm:
                    # for each original monitor
                    for mon in monitors:
                        if mon[1] == mtype:
                            # same type of monitor, now check arguments
                            samemons.append(((tid, mtype, margs, mres,
                                              mresperc, mextra, mout), mon))
                if not samemons == []:
                    for cand, mon in samemons:
                        if not cand[2] ==  mon[2]:
                            similar = False
                if similar:
                    tmp.append(pid)
            res = tmp
        return res

