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

from gstqa.log import critical, error, warning, debug, info
from gstqa.storage.storage import DBStorage
from pysqlite2 import dbapi2 as sqlite

TABLECREATION = """
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
   arguments BLOB,
   results BLOB,
   resultpercentage FLOAT,
   extrainfo BLOB
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
"""

class SQLiteStorage(DBStorage):
    """
    Stores data in a sqlite db
    """

    def __init__(self, *args, **kwargs):
        DBStorage.__init__(self, *args, **kwargs)
        self.__clientid = None
        self.__testrunid = None
        self.__testrun = None

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
        self._ExecuteCommit(updatestr, (self.__testrunid, testrun._stoptime))
        debug("updated")

    # public retrieval API

    def listTestRuns(self):
        liststr = "SELECT id from testrun"
        res = self._FetchAll(liststr)
        debug("Got %d testruns", len(res))
        return list(zip(*res)[0])
