# GStreamer QA system
#
#       threads.py
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
Convenience methods and classes for multi-threading
"""

# code from pitivi/threads.py

import threading
import gobject
from insanity.log import critical, error, warning, debug, info

class Thread(threading.Thread, gobject.GObject):
    """
    GObject-powered thread
    """

    __gsignals__ = {
        "done" : ( gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   ( ))
        }

    def __init__(self):
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)

    def stop(self):
        """ stop the thread, do not override """
        self.abort()
        self.emit("done")

    def run(self):
        """ thread processing """
        self.process()
        gobject.idle_add(self.emit, "done")

    def process(self):
        """ Implement this in subclasses """
        raise NotImplementedError

    def abort(self):
        """ Abort the thread. Subclass have to implement this method ! """
        pass

gobject.type_register(Thread)

class CallbackThread(Thread):

    def __init__(self, callback, *args, **kwargs):
        Thread.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def process(self):
        self.callback(*self.args, **self.kwargs)

gobject.type_register(CallbackThread)

class ThreadMaster(gobject.GObject):
    """
    Controls all thread existing in pitivi
    """

    def __init__(self):
        gobject.GObject.__init__(self)
        self.threads = []

    def addThread(self, threadclass, *args):
        # IDEA : We might need a limit of concurrent threads ?
        # ... or some priorities ?
        # FIXME : we should only accept subclasses of our Thread class
        debug("Adding thread of type %r" % threadclass)
        thread = threadclass(*args)
        thread.connect("done", self._threadDoneCb)
        self.threads.append(thread)
        debug("starting it...")
        thread.start()
        debug("started !")

    def _threadDoneCb(self, thread):
        debug("thread %r is done" % thread)
        self.threads.remove(thread)

    def stopAllThreads(self):
        debug("stopping all threads")
        joinedthreads = 0
        while(joinedthreads < len(self.threads)):
            for thread in self.threads:
                debug("Trying to stop thread %r" % thread)
                try:
                    thread.join()
                    joinedthreads += 1
                except:
                    warning("what happened ??")

