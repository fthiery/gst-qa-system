# GStreamer QA system
#
#       storage/mysql.py
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
MySQL based DBStorage

Requires the mysql-python module
http://mysql-python.sourceforge.net/
"""

from insanity.log import error, warning, debug
from insanity.storage.dbstorage import DBStorage
import MySQLdb

class MySQLStorage(DBStorage):
    """
    MySQL based DBStorage
    """

    def __init__(self, host="localhost", username="insanity",
                 passwd="madness", port=3306,
                 dbname="insanity",
                 *args, **kwargs):
        self.__host = host
        self.__port = port
        self.__username = username
        self.__passwd = passwd
        self.__dbname = dbname
        DBStorage.__init__(self, *args, **kwargs)

    def __repr__(self):
        return "<%s %s@%s:%d>" % (type(self),
                                  self.__dbname,
                                  self.__host,
                                  self.__port)

    def _openDatabase(self):
        con = MySQLdb.connect(host=self.__host,
                              port=self.__port,
                              user=self.__username,
                              passwd=self.__passwd,
                              db=self.__dbname)
        return con

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
        SHOW TABLES;
        """
        cursor = self.con.cursor()
        cursor.execute(checktables)
        res = cursor.fetchall()
        if not res:
            return []
        res = list(zip(*res)[0])
        return res

    def _ExecuteCommit(self, instruction, *args, **kwargs):
        """
        Calls .execute(instruction, *args, **kwargs) and .commit()

        Returns the last row id

        Threadsafe
        """
        commit = kwargs.pop("commit", True)
        threadsafe = kwargs.pop("threadsafe", False)
        instruction = instruction.replace('?', '%s')
        #if len(args):
        #    args = args[0]
        debug("%s args:%r kwargs:%r", instruction, args, kwargs)
        if not threadsafe:
            self._lock.acquire()
        try:
            cur = self.con.cursor()
            cur.execute(instruction, *args, **kwargs)
            if commit:
                self.con.commit()
        finally:
            if not threadsafe:
                self._lock.release()
        return cur.lastrowid

    def _ExecuteMany(self, instruction, *args, **kwargs):
        commit = kwargs.pop("commit", True)
        threadsafe = kwargs.pop("threadsafe", False)
        instruction = instruction.replace('?', '%s')
        if not threadsafe:
            self._lock.acquire()
        try:
            cur = self.con.cursor()
            cur.executemany(instruction, *args, **kwargs)
            if commit:
                self.con.commit()
        finally:
            if not threadsafe:
                self._lock.release()

    def _FetchAll(self, instruction, *args, **kwargs):
        """
        Executes the given SQL query and returns a list
        of tuples of the results

        Threadsafe
        """
        self._lock.acquire()
        try:
            instruction = instruction.replace('?', '%s')
            #if len(args):
            #    args = args[0]
            debug("%s args:%r kwargs:%r", instruction, args, kwargs)
            cur = self.con.cursor()
            cur.execute(instruction, *args, **kwargs)
            res = cur.fetchall()
            debug("Result %r", res)
        finally:
            self._lock.release()
        return list(res)

    def _FetchOne(self, instruction, *args, **kwargs):
        """
        Executes the given SQL query and returns a unique
        tuple of result

        Threadsafe
        """
        self._lock.acquire()
        try:
            instruction = instruction.replace('?', '%s')
            #if len(args):
            #    args = args[0]
            cur = self.con.cursor()
            debug("%s args:%r kwargs:%r", instruction, args, kwargs)
            cur.execute(instruction, *args, **kwargs)
            res = cur.fetchone()
            debug("Result %r", res)
        finally:
            self._lock.release()
        return res

    def _getDBScheme(self):
        return DB_SCHEME


DB_SCHEME = """
CREATE TABLE version (
   version integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   modificationtime INTEGER
);

CREATE TABLE testrun (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   clientid INTEGER,
   starttime INTEGER,
   stoptime INTEGER
);

CREATE TABLE client (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   software TEXT,
   name TEXT,
   user TEXT
);

CREATE TABLE test (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   testrunid INTEGER,
   type INTEGER,
   resultpercentage FLOAT
);

CREATE TABLE subtests (
   testid integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   scenarioid INTEGER
);

CREATE TABLE monitor (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   testid INTEGER,
   type INTEGER,
   resultpercentage FLOAT
);

CREATE TABLE monitorclassinfo (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   type VARCHAR(255),
   parent VARCHAR(255),
   description TEXT
);

CREATE TABLE testclassinfo (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   type TEXT,
   parent VARCHAR(255),
   description TEXT,
   fulldescription TEXT
);

CREATE TABLE testrun_environment_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   intvalue INTEGER,
   txtvalue TEXT,
   blobvalue BLOB
);

CREATE TABLE test_arguments_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER,
   txtvalue TEXT,
   blobvalue BLOB
);

CREATE TABLE test_checklist_list (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER
);

CREATE TABLE test_extrainfo_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER,
   txtvalue TEXT,
   blobvalue BLOB
);

CREATE TABLE test_outputfiles_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   txtvalue TEXT
);

CREATE TABLE monitor_arguments_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER,
   txtvalue TEXT,
   blobvalue BLOB
);

CREATE TABLE monitor_checklist_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER
);

CREATE TABLE monitor_extrainfo_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   intvalue INTEGER,
   txtvalue TEXT,
   blobvalue BLOB
);

CREATE TABLE monitor_outputfiles_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name INTEGER,
   txtvalue TEXT
);

CREATE TABLE testclassinfo_arguments_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   blobvalue BLOB
);

CREATE TABLE testclassinfo_checklist_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE TABLE testclassinfo_extrainfo_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE TABLE testclassinfo_outputfiles_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE TABLE monitorclassinfo_arguments_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE TABLE monitorclassinfo_checklist_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE TABLE monitorclassinfo_extrainfo_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
   containerid INTEGER,
   name TEXT,
   txtvalue TEXT
);

CREATE TABLE monitorclassinfo_outputfiles_dict (
   id integer NOT NULL AUTO_INCREMENT PRIMARY KEY,
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
