#!/usr/bin/env python

# GStreamer QA system
#
#       environment.py
#
# Copyright (c) 2007, Edward Hervey <bilboed@bilboed.com>
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
Environment-related methods and classes
"""

import cPickle
import subprocess
import os
import tempfile
import sys
import string
import gobject
gobject.threads_init()

# TODO : methods/classes to retrieve/process environment
#
# examples:
#   env variablse
#   gstreamer versions
#   pluggable env retrievers
#   Application should be able to add information of its own
def _pollSubProcess(process, resfile, callback):
    res = process.poll()
    if res == None:
        return True
    # get dictionnary from resultfile
    try:
        mf = open(resfile, "rb")
        resdict = cPickle.load(mf)
        mf.close()
        os.remove(resfile)
    except:
        resdict = {}
    # call callback with dictionnary
    callback(resdict)
    return False

def collectEnvironment(environ, callback):
    """
    Using the given environment variables, spawn a new process to collect
    various environment information.

    Returns a dictionnary of information.

    When the information collection is done, the given callback will be called
    with the dictionnary of information as it's sole argument.
    """
    resfile, respath = tempfile.mkstemp()
    os.close(resfile)
    thispath = os.path.abspath(__file__.replace(".pyc", ".py"))
    pargs = [thispath, respath]
    proc = subprocess.Popen(pargs, env=environ)
    gobject.timeout_add(500, _pollSubProcess, proc, respath, callback)

##
## SUBPROCESS METHODS/FUNCTIONS
##

def tupletostr(atup):
    return string.join([str(x) for x in atup], ".")

def _getGStreamerEnvironment():
    # returns a dictionnary with the GStreamer specific details
    import pygst
    pygst.require("0.10")
    import gst
    d = {}
    d["pygst-version"] = tupletostr(gst.get_pygst_version())
    d["gst-version"] = tupletostr(gst.get_gst_version())
    # FIXME : Collect all information from the registry
    return d

def _privateCollectEnvironment():
    """
    Method called from the subprocess to collect environment
    """
    res = {}
    res["env-variables"] = os.environ.copy()
    res["uname"] = os.uname()
    res.update(_getGStreamerEnvironment())
    return res

if __name__ == "__main__":
    # args : <outputfile>
    d = _privateCollectEnvironment()
    mf = open(sys.argv[1], "wb+")
    cPickle.dump(d, mf)
    mf.close()
