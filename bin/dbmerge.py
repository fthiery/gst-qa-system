#!/usr/bin/env python
# GStreamer QA system
#
#       bin/dbmerge.py
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
Tool to merge testruns from one DBStorage to another
"""

import sys
from optparse import OptionParser
from insanity.log import initLogging
from insanity.storage.sqlite import SQLiteStorage
from insanity.storage.mysql import MySQLStorage

# Use URI for DBStorage
# mysql://user:password@location/dbname
# sqlite://file/full/location

def make_sqlite_storage(location):
    return SQLiteStorage(path=location, async=False)

def make_mysql_storage(uri):
    username="insanity"
    passwd="madness"
    port=3306
    host="localhost"
    dbname="insanity"
    if '@' in uri:
        userpass, uri = uri.split('@', 1)
        if ':' in userpass:
            username, passwd = userpass.split(':', 1)
        else:
            username = userpass
    if '/' in uri:
        uri, dbname = uri.rsplit('/', 1)
    if ':' in uri:
        host, port = uri.split(':', 1)
        port = int(port)
    else:
        host = uri
    return MySQLStorage(username=username, passwd=passwd,
                        port=port, host=host, dbname=dbname,
                        async=False)

if __name__ == "__main__":
    usage = "usage: %prog"
    parser = OptionParser(usage=usage)
    parser.add_option("-t", "--testrun", dest="testrun",
                      help="Specify a testrun id to merge from",
                      type=int,
                      default=-1)
    parser.add_option("-o", "--origin", dest="origin",
                      help="SQLite DB from which to merge from",
                      type=str, default=None)
    parser.add_option("-s", "--origin-mysql", dest="origin_mysql",
                      help="Mysql DB from which to merge from ([user[:password]@]host[:port][/dbname])",
                      type=str, default=None)
    parser.add_option("-d", "--destination", dest="destination",
                      help="SQLite DB to merge into",
                      type=str, default=None)
    parser.add_option("-y", "--destination-mysql", dest="destination_mysql",
                      help="Mysql DB to merge into ([user[:password]@]host[:port][/dbname])",
                      type=str, default=None)
    (options, args) = parser.parse_args(sys.argv[1:])
    if (not (options.origin or options.origin_mysql)) \
           and (not (options.destination or options.destination_mysql)):
        parser.print_help()
        sys.exit()
    initLogging()
    if options.origin:
        origin = make_sqlite_storage(options.origin)
    elif options.origin_mysql:
        origin = make_mysql_storage(options.origin_mysql)
    if options.destination:
        destination = make_sqlite_storage(options.destination)
    elif options.destination_mysql:
        destination = make_mysql_storage(options.destination_mysql)

    # and finally merge !
    if options.testrun != -1:
        runs = [ options.testrun ]
    else:
        runs = []
    destination.merge(origin, runs)
