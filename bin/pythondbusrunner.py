#!/usr/bin/env python

# GStreamer QA system
#
#       pythondbusrunner.py
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
Runner for DBus remote python tests
"""

usage = """%s - Remote DBUS Python test runner

Usage : %s <test_uuid>
   test_uuid : Unique identifier corresponding to the test in the daemon

   PRIVATE_DBUS_ADDRESS should also be set to the address of the
   private DBus address.
"""

import gobject
gobject.threads_init()
import sys
import os
import dbus
import dbus.bus
import dbus.service
import imp
import gstqa
from gstqa.log import critical, error, warning, debug, info, initLogging
from dbus.mainloop.glib import DBusGMainLoop

initLogging()

## FIXME
## We need to exit when
## * there's an error
## * we receive "done" from the instance

class DbusRunner(dbus.service.Object):

    def __init__(self, bus, uuid, busname):
        self.ml = gobject.MainLoop()
        self.bus = bus
        objectpath = "/net/gstreamer/Insanity/Test/RemotePythonRunner%s" % uuid
        dbus.service.Object.__init__(self, conn=self.bus,
                                     object_path=objectpath,
                                     bus_name=busname)
        self.testInstance=None
        # we also need a timeout to exit if we didn't get any connection !

    def run(self):
        self.ml.run()

    @dbus.service.method(dbus_interface="net.gstreamer.Insanity.RemotePythonRunner",
                         in_signature="sssa{sv}", out_signature="b",
                         utf8_strings=True)
    def createTestInstance(self, filename, modulename,
                           classname, kwargs):
        args = dict(kwargs)
        args["proxy"] = False
        args["bus"] = self.bus
        debug("filename:%s, modulename:%s, classname:%s", filename,
              modulename, classname)
        debug("args : %r", kwargs)
        # create instance
        # import classname from filename
        if modulename == "__main__":
            debug("Non-standard module, importing from file")
            modname = "MainApplication"
            modfile = file(filename)
            mod = None
            try:
                mod = imp.load_module(modname, modfile, filename, ('', 'U', 1))
            finally:
                modfile.close()
            # return True if instance was created properly, else False
            if mod == None:
                return False
        else:
            debug("import module %s", modulename)
            mod = __import__(modulename, fromlist=[modulename])
        debug("Got module %r", mod)
        # get class
        cls = mod.__dict__.get(classname)
        debug("Creating instance of %r", cls)
        self.testInstance = cls(**args)
        debug("Instance created %r", self.testInstance)
        self.testInstance.connect("done", self._instanceDoneCb)
        return True

    def _instanceDoneCb(self, instance):
        debug("instance done, exiting mainloop")
        self.ml.quit()

if __name__ == "__main__":
    if len(sys.argv) < 2 or os.getenv("PRIVATE_DBUS_ADDRESS") == None:
        print usage % (sys.argv[0], sys.argv[0])
        sys.exit(1)
    uuid = sys.argv[1]

    dbusadd = os.getenv("PRIVATE_DBUS_ADDRESS")

    try:
        bus = dbus.bus.BusConnection(dbusadd, mainloop=DBusGMainLoop())
        busname = dbus.service.BusName("net.gstreamer.Insanity.Test.Test%s" % uuid, bus)

        dbr = DbusRunner(bus, uuid, busname)
        sys.exit(dbr.run())
    except:
        sys.exit(1)
