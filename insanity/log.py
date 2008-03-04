# GStreamer QA system
#
#       client.py
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
Logging features

Outputs information on stderr

Set INSANITY_DEBUG env variable to the required level

INSANITY_DEBUG   LEVEL
-------------------------
1               CRITICAL
2               ERROR
3               WARNING
4               INFO
5               DEBUG
"""

from logging import *
import sys
import os


##
## LOGGING
##
## TODO :
##  Should improve this to have categories
##  Add convenience functions for objects, maybe an interface
##     This might be tricky, need to go up some frames to get proper
##     filename and lineno.

__logging_setup__ = False

def initLogging():
    """
    Setup the logging system according to environment variables
    """
    global __logging_setup__
    if __logging_setup__ == True:
        info("Logging was already setup, returning")
        return

    majv, minv = sys.version_info[:2]

    debugformat = "%(asctime)s  0x%(thread)x  %(levelname)10s  %(filename)s:%(lineno)d:"
    if (majv, minv) >= (2, 5):
        debugformat += "%(funcName)s: %(message)s"
    else:
        debugformat += ": %(message)s"
    debuglevel = ERROR

    # get default level INSANITY_DEBUG
    if os.getenv("INSANITY_DEBUG"):
        insdeb = int(os.getenv("INSANITY_DEBUG"))
        if insdeb > 0 and insdeb <= 5:
            levels = [CRITICAL, ERROR,
                      WARNING, INFO,
                      DEBUG]
            debuglevel = levels[insdeb - 1]

    # basicConfig
    basicConfig(level = debuglevel, format = debugformat)
    info("Logging is now properly setup")
    __logging_setup__ = True
