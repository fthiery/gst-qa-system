#!/bin/env python

# GStreamer QA system
#
#       dumpresults.py
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
Dumps the results of a test results DB
"""

import sys
import time
from optparse import OptionParser
from gstqa.storage.sqlite import SQLiteStorage

def printTestRunInfo(db, testrunid, verbose=False):
    # id , date, nbtests, client
    cid, starttime, stoptime = db.getTestRun(testrunid)
    softname, clientname, clientuser = db.getClientInfoForTestRun(testrunid)
    tests = db.getTestsForTestRun(testrunid)
    print "[% 3d]\tDate:%s\tnbtests:% 5d\tClient : %s/%s/%s" % (testrunid,
                                                                time.ctime(starttime),
                                                                len(tests),
                                                                softname,
                                                                clientname,
                                                                clientuser)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-l", "--list", dest="list",
                      help="List the available test runs",
                      action="store_true",
                      default=False)
    parser.add_option("-t", "--testrun", dest="testrun",
                      help="Specify a testrun id",
                      type=int,
                      default=-1)
    (options, args) = parser.parse_args(sys.argv[1:])
    if len(args) != 1:
        print "You need to specify a database file !"
        parser.print_help()
        sys.exit()
    db = SQLiteStorage(path=args[0])
    print db
    if options.list:
        # list all available test rus
        testruns = db.listTestRuns()
        for runid in testruns:
            printTestRunInfo(db, runid)
    else:
        pass
