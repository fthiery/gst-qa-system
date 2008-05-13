# GStreamer QA system
#
#       tests/scenario/gnltest.py
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
Full gnonlin scenario
"""

from insanity.scenario import Scenario
from tests.gnltest import GnlFileSourceTest
from tests.typefind import TypeFindTest
import gst

class FullGnlFileSourceScenario(Scenario):
    __test_description__ = """
    Runs gnlfilesource test on each media stream of the given uri
    """
    __test_full_description__ = """
    Will analyze a given uri (using typefind-test) and then add a gnltest
    for each contained stream.
    """
    __test_name__ = "full-gnlfilesource-scenario"

    def setUp(self):
        if not Scenario.setUp(self):
            return False
        self.__doneTypeFindTest = False
        # add the initial typefind test
        self.addSubTest(TypeFindTest, self.arguments)
        return True

    def subTestDone(self, test):
        # if we've already seen the typefind test, return True
        if self.__doneTypeFindTest:
            return True

        # let's have a look at the streams
        infos = test.getExtraInfo()
        if not 'streams' in infos.keys():
            return False

        if not 'total-uri-duration' in infos.keys():
            return False

        uriduration = infos['total-uri-duration']
        if uriduration <= 0:
            return False
        # pick a duration/media-start which is within the given uri duration
        mstart = uriduration / 2
        duration = gst.SECOND
        if uriduration < 2 * gst.SECOND:
            duration = mstart

        # we can carry on if we have some raw streams
        upstreams = infos["streams"]
        streams = self._extractRawStreams(upstreams)
        if streams == []:
            return False

        # finally, add a GnlFileSourceTest for each stream
        for stream in streams:
            padname, length, caps = stream
            args = self.arguments.copy()
            args["caps-string"] = caps
            args["media-start"] = mstart
            args["duration"] = duration
            self.addSubTest(GnlFileSourceTest, args)
        self.__doneTypeFindTest = True
        return True

    def _extractRawStreams(self, streams):
        res = []
        for stream in streams:
            padname, length, caps = stream
            if caps.startswith("audio/x-raw-"):
                res.append((padname, length, "audio/x-raw-int;audio/x-raw-float"))
            elif caps.startswith("video/x-raw-"):
                res.append((padname, length, "video/x-raw-yuv;video/x-raw-rgb"))
        return res
