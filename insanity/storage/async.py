# GStreamer QA system
#
#       storage/async.py
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
Asynchronous storage interface
"""

from insanity.threads import ActionQueueThread

class queuemethod(object):
    def __init__(self, fn):
        self.fn = fn

    def __get__(self, obj, klass=None):
        def wrapper(*args, **kwargs):
            if obj._async:
                obj.queueAction(self.fn, obj, *args, **kwargs)
            else:
                self.fn(obj, *args, **kwargs)
        return wrapper

class finalqueuemethod(object):
    def __init__(self, fn):
        self.fn = fn

    def __get__(self, obj, klass=None):
        def wrapper(*args, **kwargs):
            if obj._async:
                obj.queueFinalAction(self.fn, obj, *args, **kwargs)
            else:
                self.fn(obj, *args, **kwargs)
        return wrapper


class AsyncStorage:
    """
    Interface for asynchronous storing Storage
    """

    def __init__(self, async=True):
        self._async = async
        if self._async:
            self._actionthread = ActionQueueThread()
            self._actionthread.start()

    def queueAction(self, cb, *args, **kwargs):
        if self._async:
            self._actionthread.queueAction(cb, *args, **kwargs)

    def queueFinalAction(self, cb, *args, **kwargs):
        if self._async:
            self._actionthread.queueFinalAction(cb, *args, **kwargs)

