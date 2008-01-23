# GStreamer QA system
#
#       monitor.py
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

# TODO
#
# Add default monitor (spawn process, crash, timeout, IPC)
#    maybe in a different file...

class Monitor:
    """
    Monitors a test
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def processResults(self):
        pass
    pass

class FileBasedMonitorInterface:
    """
    Interface for monitors that record data to file(s)
    """

    # TODO :
    #  We should create the unique/temporary files in a location
    #  specified by the client configuration
    #
    #  Make sure we can handle several files

    def requestUniqueFileLocation(self):
        # returns an opened file object
        pass

    def deleteAllFiles(self):
        # used to clean up failed tests or files no longer needed
        pass
    pass


##
## TODO : maybe the two classes below don't make sense and should
## just be an option in the base Monitor class.
##

class AsyncMonitor(Monitor):
    """
    Monitors that will record data and THEN process it
    """
    pass

class DirectMonitor(Monitor):
    """
    Monitors that will record and process data at the same time
    """
    pass

class BasicMonitor(Monitor):
    """
    The BasicMonitor is the only compulsory monitor

    It will:
    * spawn the test in a separate process
    * detect segmentation faults
    * handle higher-level timeouts (?)
    """

    pass
