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
import imp
import string
import gobject
gobject.threads_init()
import gst
from gstqa.log import critical, error, warning, debug, info, exception

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
        exception("Couldn't get pickle from file %s", resfile)
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
    thispath = os.path.abspath(__file__)
    # The compiled module suffix can be ".pyc" or ".pyo":
    suffixes = [s[0] for s in imp.get_suffixes()
                if s[2] == imp.PY_COMPILED]
    for suffix in suffixes:
        if thispath.endswith(suffix):
            thispath = thispath[:-len(suffix)] + ".py"
            break
    pargs = [thispath, respath]
    try:
        debug("spawning subprocess %r", pargs)
        proc = subprocess.Popen(pargs, env=environ)
    except:
        exception("Spawning remote process (%s) failed" % (" ".join(pargs),))
        os.remove(respath)
        callback({})
    else:
        gobject.timeout_add(500, _pollSubProcess, proc, respath, callback)

##
## SUBPROCESS METHODS/FUNCTIONS
##

def _tupletostr(atup):
    return string.join([str(x) for x in atup], ".")

def _getGStreamerRegistry():
    import stat
    # returns a dictionnary with the contents of the registry:
    # key : plugin-name
    # value : (version, filename, date, [features])
    #   [features] is a list of the names of the pluginfeatures
    reg = gst.registry_get_default()
    d = {}
    for p in reg.get_plugin_list():
        name = p.get_name()
        filename = p.get_filename()
        if filename:
            date = os.stat(filename)[stat.ST_MTIME]
        else:
            date = 0
        version = p.get_version()
        features = [x.get_name() for x in reg.get_feature_list_by_plugin(name)]
        d[name] = (filename, date, version, features)
    return d

def _getGStreamerEnvironment():
    # returns a dictionnary with the GStreamer specific details
    d = {}
    d["pygst-version"] = _tupletostr(gst.get_pygst_version())
    d["pygst-path"] = gst.__path__[0]
    d["pygst-file"] = gst.__file__
    d["gst-version"] = _tupletostr(gst.get_gst_version())
    d["gst-registry"] = _getGStreamerRegistry()
    return d

def _getGObjectEnvironment():
    d = {}
    d["pygobject-path"] = gobject.__path__[0]
    d["pygobject-file"] = gobject.__file__
    d["glib-version"] = _tupletostr(gobject.glib_version)
    d["pygobject-version"] = _tupletostr(gobject.pygobject_version)
    d["pygtk-version"] = _tupletostr(gobject.pygtk_version)
    return d

def _privateCollectEnvironment():
    """
    Method called from the subprocess to collect environment
    """
    res = {}
    res["env-variables"] = os.environ.copy()
    res["uname"] = os.uname()
    res.update(_getGObjectEnvironment())
    res.update(_getGStreamerEnvironment())
    return res

if __name__ == "__main__":
    # args : <outputfile>
    d = _privateCollectEnvironment()
    mf = open(sys.argv[1], "wb+")
    cPickle.dump(d, mf)
    mf.close()
