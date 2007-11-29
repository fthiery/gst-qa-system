# GStreamer QA system
#
#       test.py
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


class Test:
    """
    Runs a series of commands
    """
    __test_name__ = "test-base-class"
    __test_description__ = """Base class for tests"""
    __test_arguments__ = { }
    __test_checklist__ = { }

    def __init__(self, *args, **kwargs):
        pass

    def run(self):
        # runs the given test

    def setUp(self):
        pass

    def tearDown(self):
        pass


class GStreamerTest:
    """
    Tests that specifically run a GStreamer pipeline
    """
    pass

class CmdLineTest:
    """
    Tests that run a command line application/script.
    """
    pass
