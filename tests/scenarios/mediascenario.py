# GStreamer QA system
#
#       tests/scenario/mediascenario.py
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
Simple media-based scenarios
"""

from insanity.scenario import ListScenario
from tests.ismedia import IsMediaTest

class MediaBarrierScenario(ListScenario):

    __test_name__ = """media-barrier-scenario"""
    __test_description__ = """
    Only runs the given subtests if the uri/file is a usable media type
    """
    __test_full_description__ = """
    This scenario will first check the mime-type of the given uri/file
    and if it is not a useable media type, will return without executing
    the given tests.
    """
    __non_media_types__ = [
        "application/x-rar",
        "application/zip",
        "application/x-gzip",
        "text/plain"
        ]

    def setUp(self):
        if not ListScenario.setUp(self):
            return False
        # first add a typefind test
        self.addSubTest(IsMediaTest,
                        self.arguments,
                        [], position=0)
        return True

    def subTestDone(self, test):
        if ListScenario.subTestDone(self, test) == False:
            return False
        if isinstance(test, IsMediaTest):
            # get the type
            mtype = test.getExtraInfo()["mime-type"]
            if mtype in self.__non_media_types__:
                return False
        return True
