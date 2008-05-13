#!/usr/bin/env python

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
Compare two testruns
"""

import sys
import time
from optparse import OptionParser
from insanity.storage.sqlite import SQLiteStorage

def printTestInfo(db, testid, failedonly=False):
    trid, ttype, args, checks, resperc, extras, outputfiles = db.getFullTestInfo(testid)
    if failedonly and resperc == 100.0:
        return
    # test number + name
    print "Test #% 3d (%s) Success : %0.1f%%" % (testid, ttype, resperc)
    # arguments
    print "Arguments :"
    for key,val in args.iteritems():
        print "\t% -30s:\t%s" % (key, val)
    # results
    print "Results :"
    for key,val in checks:
        print "\t% -30s:\t%d" % (key, val)
    if extras:
        print "Extra Information:"
        for key,val in extras.iteritems():
            print "\t% -30s:\t%s" % (key, val)
    if outputfiles:
        print "Output files:"
        for key,val in outputfiles.iteritems():
            print "\t% -30s:\t%s" % (key,val)
    # monitors
    monitors = db.getMonitorsIDForTest(testid)
    if monitors:
        print "Applied Monitors:"
        for mid in monitors:
            tid,mtyp,args,results,resperc,extras,outputfiles = db.getFullMonitorInfo(mid)
            print "\tMonitor #% 3d (%s) Success : %0.1f%%" % (mid, mtyp, resperc)
            if args:
                print "\t\tArguments :"
                for k,v in args.iteritems():
                    print "\t\t\t% -30s:\t%s" % (k,v)
            if results:
                print "\t\tResults :"
                for k,v in results.iteritems():
                    print "\t\t\t% -30s:\t%s" % (k,v)
            if extras:
                print "\t\tExtra Information :"
                for k,v in extras.iteritems():
                    print "\t\t\t% -30s:\t%s" % (k,v)
            if outputfiles:
                print "\t\tOutput Files :"
                for k,v in outputfiles.iteritems():
                    print "\t\t\t% -30s:\t%s" % (k,v)
    print ""

def compare(storage, testrun1, testrun2):
    """
    Compares the given testruns

    Returns a tuple of 5 values:
    * list of testid in testrun2 which are not in testrun1
    * list of testid in testrun1 which are not in testrun2
    * list of testid in testrun2 which have improved
    * list of testid in testrun2 which have regressed
    * a dictionnary mapping of:
      * testid from testrun2
      * list of corresponding testid from testrun1
    """
    testruns = storage.listTestRuns()
    if not testrun1 in testruns or not testrun2 in testruns:
        print "Give testrun ids aren't available in the given storage file"
        return
    tests1 = storage.getTestsForTestRun(testrun1, withscenarios=False)

    tests2 = storage.getTestsForTestRun(testrun2, withscenarios=False)

    if len(tests1) == len(tests2):
        print "Both testruns have the same number of tests"

    newmapping = {}
    oldinnew = []
    newtests = []

    for newid in tests2:
        tid, ttype, args, results, resperc, extras, outputfiles = storage.getFullTestInfo(newid)
        monitors = storage.getMonitorsIDForTest(newid)
        ancestors = storage.findTestsByArgument(ttype, args, testrun1, monitors)
        if ancestors == []:
            newtests.append(newid)
        else:
            newmapping[newid] = ancestors
            oldinnew.extend(ancestors)

    testsgone = [x for x in tests1 if not x in oldinnew]
    print "Removed ", testsgone
    print "Still present ", oldinnew
    print "New tests ", newtests
    print "Mapping", newmapping

    # we should now process the newmapping to figure out regressions
    # and improvements
    regs = []
    imps = []
    for new, olds in newmapping.iteritems():
        old = olds[0]
        tid1, x1, a1, res1, perc1, extra1, output1 = storage.getFullTestInfo(old)
        tid2, x2, a2, res2, perc2, extra2, output2 = storage.getFullTestInfo(new)
        if perc1 == 100 and perc2 == 100:
            continue
        if perc1 < perc2:
            imps.append(new)
        elif perc1 > perc2:
            regs.append(new)

    print "REGRESSIONS", len(regs), regs
    print "IMPROVEMENTS", len(imps), imps

    return (newtests, testsgone, imps, regs, newmapping)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print "Usage : compare.py <testrundbfile> <testrunid> <testrunid>"
        sys.exit(0)
    db = SQLiteStorage(sys.argv[1])
    # the last two arguments are the testrunid to compare
    a,b = [int(x) for x in sys.argv[-2:]]
    new, gone, imps, regs, mapping = compare(db, a, b)
    print "****REGRESSIONS****"
    for test in regs:
        for ptest in mapping[test]:
            print "OLD TEST %d", ptest
            printTestInfo(db, ptest)
        print "NEW TEST %d", test
        printTestInfo(db, test)
