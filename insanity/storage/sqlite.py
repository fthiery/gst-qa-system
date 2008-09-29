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
SQLite based DBStorage
"""

from insanity.log import error, warning, debug
from insanity.storage.dbstorage import DBStorage

try:
    # In Python 2.5, this is part of the standard library:
    from sqlite3 import dbapi2 as sqlite
except ImportError:
    # Previous versions have this as external dependency...
    from pysqlite2 import dbapi2 as sqlite
from cPickle import dumps

class SQLiteStorage(DBStorage):
    """
    Stores data in a sqlite db

    The 'async' setting will allow all writes to be serialized in a separate thread,
    allowing the testing to carry on.

    If you are only using the database for reading information, you should use
    async=False and only use the storage object from one thread.
    """

    def __init__(self, path, *args, **kwargs):
        self.path = path
        DBStorage.__init__(self, *args, **kwargs)

    def __repr__(self):
        return "<%s %s>" % (type(self), self.path)

    # DBStorage methods implementation
    def _openDatabase(self):
        debug("opening sqlite db for path '%s'", self.path)
        con = sqlite.connect(self.path, check_same_thread=False)
        # we do this so that we can store UTF8 strings in the database
        con.text_factory = str
        return con

    def _ExecuteScript(self, instructions, *args, **kwargs):
        """
        Executes the given script.
        """
        commit = kwargs.pop("commit", True)
        threadsafe = kwargs.pop("threadsafe", False)
        debug("%s args:%r kwargs:%r", instructions, args, kwargs)
        if not threadsafe:
            self._lock.acquire()
        try:
            cur = self.con.cursor()
            cur.executescript(instructions, *args, **kwargs)
            if commit:
                self.con.commit()
        finally:
            if not threadsafe:
                self._lock.release()
        return cur.lastrowid


    def _getDatabaseSchemeVersion(self):
        """
        Returns the scheme version of the currently loaded databse

        Returns None if there's no properly configured scheme, else
        returns the version
        """
        tables = self.__getAllTables()
        if not "version" in tables:
            return None
        # check if the version is the same as the current one
        res = self._FetchOne("SELECT version FROM version")
        if res == None:
            return None
        return res[0]

    def __getAllTables(self):
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
                value = str(dumps(val))
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

    def _getDBScheme(self):
        return DB_SCHEME

DB_SCHEME = """
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
   type INTEGER,
   resultpercentage FLOAT
);

CREATE TABLE subtests (
   testid INTEGER PRIMARY KEY,
   scenarioid INTEGER
);

CREATE TABLE monitor (
   id INTEGER PRIMARY KEY,
   testid INTEGER,
   type INTEGER,
   resultpercentage FLOAT
);

CREATE TABLE testclassinfo (
   id INTEGER PRIMARY KEY,
   type TEXT,
   parent TEXT,
   description TEXT,
   fulldescription TEXT
);

CREATE TABLE monitorclassinfo (
   id INTEGER PRIMARY KEY,
   type TEXT,
   parent TEXT,
   description TEXT
);

CREATE TABLE testrun_environment_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   intvalue INTEGER,
   txtvalue TEXT,
   blobvalue BLOB
);

CREATE TABLE test_arguments_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER,
   txtvalue TEXT,
   blobvalue BLOB
);

CREATE TABLE test_checklist_list (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER
);

CREATE TABLE test_extrainfo_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER,
   txtvalue TEXT,
   blobvalue BLOB
);

CREATE TABLE test_outputfiles_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   txtvalue TEXT
);

CREATE TABLE monitor_arguments_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER,
   txtvalue TEXT,
   blobvalue BLOB
);

CREATE TABLE monitor_checklist_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER
);

CREATE TABLE monitor_extrainfo_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER,
   txtvalue TEXT,
   blobvalue BLOB
);

CREATE TABLE monitor_outputfiles_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   txtvalue TEXT
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
   txtvalue TEXT
);

CREATE TABLE testclassinfo_extrainfo_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE TABLE testclassinfo_outputfiles_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE TABLE monitorclassinfo_arguments_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE TABLE monitorclassinfo_checklist_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE TABLE monitorclassinfo_extrainfo_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE TABLE monitorclassinfo_outputfiles_dict (
   id INTEGER PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE INDEX test_testrunid_idx ON test(testrunid);
CREATE INDEX subtests_scenarioid_idx ON subtests(scenarioid);
CREATE INDEX monitor_testid_idx ON monitor(testid);
CREATE INDEX testclassinfo_parent_idx ON testclassinfo (parent);
CREATE INDEX monitorclassinfo_parent_idx ON monitorclassinfo (parent);
CREATE INDEX testrun_env_dict_container_idx ON testrun_environment_dict (containerid);

CREATE INDEX t_a_dict_containerid_idx ON test_arguments_dict (containerid);
CREATE INDEX t_c_list_containerid_idx ON test_checklist_list (containerid);
CREATE INDEX t_ei_dict_containerid_idx ON test_extrainfo_dict (containerid);
CREATE INDEX t_of_dict_containerid_idx ON test_outputfiles_dict (containerid);

CREATE INDEX m_a_dict_containerid_idx ON monitor_arguments_dict (containerid);
CREATE INDEX m_c_dict_containerid_idx ON monitor_checklist_dict (containerid);
CREATE INDEX m_ei_dict_containerid_idx ON monitor_extrainfo_dict (containerid);
CREATE INDEX m_of_dict_containerid_idx ON monitor_outputfiles_dict (containerid);

CREATE INDEX tc_a_dict_c_idx ON testclassinfo_arguments_dict (containerid);
CREATE INDEX tc_c_dict_c_idx ON testclassinfo_checklist_dict (containerid);
CREATE INDEX tc_ei_dict_c_idx ON testclassinfo_extrainfo_dict (containerid);
CREATE INDEX tc_of_dict_c_idx ON testclassinfo_outputfiles_dict (containerid);

CREATE INDEX mc_a_dict_c_idx ON monitorclassinfo_arguments_dict (containerid);
CREATE INDEX mc_c_dict_c_idx ON monitorclassinfo_checklist_dict (containerid);
CREATE INDEX mc_ei_dict_c_idx ON monitorclassinfo_extrainfo_dict (containerid);
CREATE INDEX mc_of_dict_c_idx ON monitorclassinfo_outputfiles_dict (containerid);

CREATE INDEX test_type_idx ON test (type);
"""
