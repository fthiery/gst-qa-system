# GStreamer QA system
#
#       storage/dbstorage.py
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
Database DataStorage
"""

from insanity.log import error, warning, debug
from insanity.storage.storage import DataStorage

class DBStorage(DataStorage):
    """
    Stores data in a database

    Don't use this class directly, but one of its subclasses
    """

    # DataStorage methods implementation

    def setUp(self):
        # open database
        self.openDatabase()

        # check if we have an existing database with valid
        # tables.
        version = self.getDatabaseSchemeVersion()
        if version == None:
            # createTables if needed
            self.createTables()
        elif version < DB_SCHEME_VERSION:
            self.updateTables(DB_SCHEME_VERSION)
        else:
            warning("")

    def close(self, callback=None, *args, **kwargs):
        self._shutDown(callback, *args, **kwargs)


    # Methods to be implemented in subclasses

    def openDatabase(self):
        """Open the database"""
        raise NotImplementedError

    def getDatabaseSchemeVersion(self):
        """
        Returns the scheme version of the currently loaded databse

        Returns None if there's no properly configured scheme, else
        returns the version
        """
        raise NotImplementedError

    def updateTables(self, fromversion, toversion):
        """
        Update the tables from <toversion> to <toversion> database
        scheme.
        """
        raise NotImplementedError

    def createTables(self):
        """Makes sure the tables are properly created"""
        raise NotImplementedError

    def _shutDown(self, callback, *args, **kwargs):
        raise NotImplementedError

DB_SCHEME_VERSION = 2

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
