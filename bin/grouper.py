#!/usr/bin/env python

# GStreamer QA system
#
#       grouper.py
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
Finds similarities in a testrun and groups them
"""

import sys
import string
import time
from optparse import OptionParser
from insanity.storage.sqlite import SQLiteStorage

( TRUE_VALIDATED,
  FALSE_VALIDATED,
  UNVALIDATED ) = range(3)

statusnames = ["True", "False", "Unvalidated" ]

class CheckGroup:

    def __init__(self, checkname):
        self.name = checkname
        self.trues = []
        self.falses = []
        self.unvalidated = []

    def allTrue(self):
        if len(self.falses) == 0 and len(self.unvalidated) == 0:
            return True
        return False

    def allFalse(self):
        if len(self.trues) == 0 and len(self.unvalidated) == 0:
            return True
        return False

    def allUnvalidated(self):
        if len(self.trues) == 0 and len(self.falses) == 0:
            return True
        return False

    def getFalseUnvalid(self):
        res = self.falses[:]
        res.extend(self.unvalidated)
        return res

    def __repr__(self):
        return "<Checkgroup %s>" % self.name

class Node:
    def __init__(self, tests, name=None):
        self.tests = tests
        self.true = None
        self.false = None
        self.unvalid = None
        self.name = name

    def isEndBranch(self):
        if self.true == None and self.false == None and self.unvalid == None:
            return True
        return False

    def isSingleBranch(self):
        if ((self.true == None and self.false == None)
            or (self.false == None and self.unvalid == None)
            or (self.true == None and self.unvalid == None)):
            return True
        return False

    def getSingleBranch(self):
        if self.true:
            return self.true
        if self.false:
            return self.false
        return self.unvalid


class CheckNode(Node):
    def __init__(self, group, tests, status, *args, **kwargs):
        Node.__init__(self, tests, *args, **kwargs)
        self.group = group
        if group and not self.name:
            self.name = self.group.name
        self.true = None
        self.false = None
        self.unvalid = None
        self.status = status

    def __repr__(self):
        if self.status == TRUE_VALIDATED:
            val = "True"
        elif self.status == FALSE_VALIDATED:
            val = "False"
        elif self.status == UNVALIDATED:
            val = "Unvalidated"
        else:
            val = ""
        return "<%s: %s>" % (self.name, val)

class MetaNode(Node):
    """
    A CheckNode that can contains several nodes
    i.e. check1.true and check2.true
    """

    def __init__(self, nodes):
        self.nodes = nodes[:]
        Node.__init__(self, self.nodes[0].tests)

    def __repr__(self):
        res = [repr(x) for x in self.nodes]
        return "[%s]" % string.join(res)

def intersect(la, lb):
    return [x for x in la if x in lb]

def print_node(node, depth=0):
    if isinstance(node, CheckNode):
        print " " * depth, node, len(node.tests)
    else:
        # it's a metanode !
        print " " * depth, "MultiNode"
        for node in node.nodes:
            if node.status == None:
                print " " * depth, "->", node.name
            else:
                print " " * depth, "->", node.name, ":", statusnames[node.status]
        print " " * depth, "  Count:", len(node.tests)
    if node.true:
        print_node(node.true, depth+1)
    if node.false:
        print_node(node.false, depth+1)
    if node.unvalid:
        print_node(node.unvalid, depth+1)

def simplify_node(node):
    # we concatenate nodes with one-branched subnodes
    nodes = []
    while node and node.isSingleBranch():
        lastnode = node
        nodes.append(lastnode)
        node = node.getSingleBranch()

    if nodes:
        node = MetaNode(nodes)
        node.true = lastnode.true
        node.false = lastnode.false
        node.unvalid = lastnode.unvalid

    if node.true:
        node.true = simplify_node(node.true)
    if node.false:
        node.false = simplify_node(node.false)
    if node.unvalid:
        node.unvalid = simplify_node(node.unvalid)

    return node


def _doit(grouplist, tests=None, status=None, n=None):
    # take the first group,
    # create a node
    # fill it up and callrecursively on subnodes
    if tests == []:
        return None
    if grouplist == []:
        return n

    g = grouplist.pop(0)
    if tests == None or n == None:
        tests = g.getFalseUnvalid()
        tests.extend(g.trues)
        n = CheckNode(g, tests, status, name="ALL TESTS")

    trues = intersect(g.trues, tests)
    falses = intersect(g.falses, tests)
    unvalids = intersect(g.unvalidated, tests)

    if trues:
        nt = CheckNode(g, trues, TRUE_VALIDATED)
        n.true = _doit(grouplist[:], trues, TRUE_VALIDATED, nt)
    if falses:
        nf = CheckNode(g, falses, FALSE_VALIDATED)
        n.false = _doit(grouplist[:], falses, FALSE_VALIDATED, nf)
    if unvalids:
        nu = CheckNode(g, unvalids, UNVALIDATED)
        n.unvalid = _doit(grouplist[:], unvalids, UNVALIDATED, nu)

    return n

def find_similarities(group):
    # will do a deeper analysis on similarities amongst
    # the given group

    # first sort the groups by most problematic
    # and at the same time, get rid of the allTrue
    l = [(len(v.getFalseUnvalid()), v) for k,v in group.iteritems() if not group[k].allTrue()]
    l.sort(reverse=True)
    if l == []:
        return
    root = _doit(list(zip(*l)[1]))

    # With this tree we can prune it to 
    print_node(root)
    simp = simplify_node(root)
    print ""
    print_node(simp)

def group_tests(db, trid):
    if not trid in db.listTestRuns():
        print "Testrun id #%d is not available" % trid
        sys.exit(1)
    testsid = db.getTestsForTestRun(trid, withscenarios=False)

    print "%d tests available" % len(testsid)

    tests = {}

    for test in testsid:
        trid, ttype, args, checks, perc, extr, outp = db.getFullTestInfo(test)
        if not ttype in tests:
            tests[ttype] = {}
            # initialize it with all possible checkitems
            desc, fdesc, targs, tchecks, te, to = db.getTestClassInfo(ttype)
            for checkname in tchecks.iterkeys():
                tests[ttype][checkname] = CheckGroup(checkname)
        tg = tests[ttype]
        for checkitem in tg.iterkeys():
            checks = dict(checks)
            if not checkitem in checks:
                tg[checkitem].unvalidated.append(test)
            elif checks[checkitem] == True:
                tg[checkitem].trues.append(test)
            else:
                tg[checkitem].falses.append(test)

    return tests

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "Usage : compare.py <testrundbfile> <testrunid>"
        sys.exit(0)
    db = SQLiteStorage(sys.argv[1], async=False)
    # the last two arguments are the testrunid to compare
    trid = int(sys.argv[2])
    res = group_tests(db, trid)
    for testname in res.iterkeys():
        print "Test ", testname
        print "  TRUE/FALSE/INVALIDATED/NAME"
        for checkitem,checkgroups in res[testname].iteritems():
            if checkgroups.allTrue():
                continue
            print "%8d %8d %8d   %s" % (len(checkgroups.trues),
                                        len(checkgroups.falses),
                                        len(checkgroups.unvalidated),
                                        checkitem)
        # and more statistics
        alltrue = [g for g in res[testname].iterkeys() if res[testname][g].allTrue()]
        allfalse = [g for g in res[testname].iterkeys() if res[testname][g].allFalse()]
        allunvalidated = [g for g in res[testname].iterkeys() if res[testname][g].allUnvalidated()]
        print ""
        if alltrue:
            print "   The following checkitem(s) are always True"
            print "     ", string.join(alltrue, ', ')
        if allfalse:
            print "   The following checkitem(s) are always False"
            print "     ", string.join(allfalse, ', ')
        if allunvalidated:
            print "   The following checkitem(s) were never validated"
            print "     ", string.join(allunvalidated, ', ')
        print ""

        find_similarities(res[testname])
