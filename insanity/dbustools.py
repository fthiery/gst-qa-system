# GStreamer QA system
#
#       dbus.py
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
D-Bus convenience methods and classes
"""

#
# Service accesible from test instances
#
# domain : net.gstreamer.Insanity
#
# objects
#   /TestRun/<TestRunID>
#   /TestRun/<TestRunID>/<TestName>/<TestID>
#

import dbus
from dbus.bus import BusConnection
from dbus.mainloop.glib import DBusGMainLoop
import tempfile
import subprocess
import os
import signal
from insanity.log import critical, error, warning, debug, info

private_bus = None
private_bus_address = None
private_bus_pid = None

def spawn_session_dbus():
    """
    Spawns a session dbus daemon.

    Returns a tuple of (DBUS_SESSION_BUS_ADDRESS, DBUS_SESSION_BUS_PID) if the
    daemon could be started properly
    """
    debug("Spawning private DBus daemon")
    logfilefd, logfilename = tempfile.mkstemp()

    # spawn dbus-launch
    subprocess.call(["dbus-launch"],
                    stdout = logfilefd,
                    stderr = subprocess.STDOUT)

    # parse the returned values
    afile = file(logfilename)

    res = [x.strip().split('=', 1)[-1] for x in afile.readlines()]
    afile.close()
    os.remove(logfilename)
    info("%r" % res)
    # return the tuple result
    return tuple(res)

def kill_private_dbus():
    """
    Kill the private dbus daemon used by the client
    """
    global private_bus_pid, private_bus, private_bus_address
    if private_bus_pid:
        info("Killing private dbus daemon [pid:%d]" % int(private_bus_pid))
        os.kill(int(private_bus_pid), signal.SIGKILL)
        private_bus = None
        private_bus_address = None
        private_bus_pid = None

def get_private_session_bus():
    """
    Get the private dbus BusConnection to use in the client.
    Tests should NOT use this method
    """
    global private_bus, private_bus_pid, private_bus_address
    if private_bus == None:
        if private_bus_pid:
            # cleanup
            kill_private_dbus()
        private_bus_address, private_bus_pid = spawn_session_dbus()[:2]
        debug("Creating BusConnection for address %s" % private_bus_address)
        gml = DBusGMainLoop()
        private_bus = BusConnection(private_bus_address, mainloop=gml)
    return private_bus

def get_private_bus_address():
    """
    Get the address of the private dbus daemon used in the client.
    This is the address that test instances can connect to in order
    to communicate with the Test Client.
    """
    global private_bus, private_bus_pid, private_bus_address
    if private_bus == None:
        if private_bus_pid:
            # cleanup
            kill_private_dbus()
        private_bus_address, private_bus_pid = spawn_session_dbus()[:2]
        print "Creating BusConnection for address", private_bus_address
        gml = DBusGMainLoop()
        private_bus = BusConnection(private_bus_address, mainloop=gml)
    return private_bus_address

def unwrap(x):
    """Hack to unwrap D-Bus values, so that they're easier to read when
    printed."""

    if isinstance(x, list):
        return map(unwrap, x)

    if isinstance(x, tuple):
        return tuple(map(unwrap, x))

    if isinstance(x, dict):
        return dict([(unwrap(k), unwrap(v)) for k, v in x.iteritems()])

    for t in [unicode, str, long, int, float, bool]:
        if isinstance(x, t):
            return t(x)

    return x
