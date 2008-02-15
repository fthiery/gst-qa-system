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

from gstqa.scenario import Scenario
from tests.gnltest import GnlFileSourceTest
from tests.typefind import TypeFindTest

class FullGnlFileSourceScenario(Scenario):

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

        # don't carry on if it didn't succeed
        if not test.getSuccessPercentage() == 100.0:
            return False

        # let's have a look at the streams
        infos = test.getExtraInfo()
        if not 'streams' in infos.keys():
            return False

        # finally, add a GnlFileSourceTest for each stream
        streams = infos["streams"]
        for stream in streams:
            padname, length, caps = stream
            args = self.arguments.copy()
            args["caps-string"] = caps
            self.addSubTest(GnlFileSourceTest, args)
        self.__doneTypeFindTest = True
        return True
