# GStreamer QA system
#
#       gstutils.py
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
Miscellaneous utility functions and classes related to testing GStreamer
"""

import os.path
import string

def get_gstreamer_env_variables(mainpath=None, gstcorepath=None, gstbasepath=None,
                                gstgoodpath=None, gstbadpath=None, gstuglypath=None,
                                gstffmpegpath=None, gstpythonpath=None,
                                gnonlinpath=None):
    """
    Returns a dictionnary of environment variables that will allow using the
    specified *uninstalled* gstreamer modules.

    If mainpath is specified, then all gstreamer modules are expected to be located
    within that path (ex : $mainpath/gstreamer/, $mainpath/gst-python/, ...).

    If not-specified, only the specified paths will be filled. This can be useful
    when mixing releases and development modules.

    All the resulting environment variables *should* be pre-pended to the existing
    ones.
    """
    res = {}
    ldlibs = []
    ppath = []
    if mainpath:
        gstcorepath=os.path.join(mainpath, "gstreamer")
        gstbasepath=os.path.join(mainpath, "gst-plugins-base")
        gstgoodpath=os.path.join(mainpath, "gst-plugins-good")
        gstbadpath=os.path.join(mainpath, "gst-plugins-bad")
        gstuglypath=os.path.join(mainpath, "gst-plugins-ugly")
        gstffmpegpath=os.path.join(mainpath, "gst-ffmpeg")
        gstpythonpath=os.path.join(mainpath, "gst-python")
        gnonlinpath=os.path.join(mainpath, "gnonlin")

    # libraries
    if gstbadpath:
        ldlibs.append(os.path.join(gstbadpath, "gst-libs/gst/app/.libs"))

    if gstbasepath:
        for i in ["audio", "cdda", "fft", "interfaces", "pbutils", "netbuffer",
                  "riff", "rtp", "rtsp", "sdp", "tag", "utils", "video"]:
            ldlibs.append(os.path.join(gstbasepath, "gst-libs/gst/%s/.libs" % i))

    if gstcorepath:
        for i in ["base", "net", "check", "controller", "dataprotocol"]:
            ldlibs.append(os.path.join(gstcorepath, "libs/gst/%s/.libs" % i ))
        ldlibs.append(os.path.join(gstcorepath, "gst/.libs"))

    # python stuff
    if gstpythonpath:
        res["PYTHONPATH"] = gstpythonpath

    # and finally the plugin paths
    if gstcorepath:
        ppath.append(gstcorepath)
    if gstbasepath:
        ppath.append(gstbasepath)
    if gstgoodpath:
        ppath.append(gstgoodpath)
    if gstbadpath:
        ppath.append(gstbadpath)
    if gstuglypath:
        ppath.append(gstuglypath)
    if gstffmpegpatch:
        ppath.append(gstffmpegpatch)
    if gnonlinpath:
        ppath.append(gnonlinpath)

    # convert everything to strings
    res["LD_LIBRARY_PATH"] = string.join(ldlibs, ":")
    res["DYLD_LIBRARY_PATH"] = string.join(ldlibs, ":")
    res["GST_PLUGIN_PATH"] = string.join(ppath, ":")

    return res
