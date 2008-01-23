# GStreamer QA system
#
#       utils.py
#
# Copyright (c) 2007, Edward Hervey <bilboed@bilboed.com>
# Copyright (C) 2004 Johan Dahlin <johan at gnome dot org>
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
Miscellaneous utility functions and classes
"""

from random import randint

__uuids = []

def randuuid():
    """
    Generates a random uuid, not guaranteed to be unique.
    """
    return "%016x" % randint(0, 2**128)

def acquire_uuid():
    """
    Returns a guaranted unique identifier.
    When the user of that UUID is done with it, it should call
    release_uuid(uuid) with that identifier.
    """
    global __uuids
    uuid = randuuid()
    while uuid in __uuids:
        uuid = randuuid()
    __uuids.append(uuid)
    return uuid

def release_uuid(uuid):
    """
    Releases the use of a unique identifier.
    """
    global __uuids
    if not uuid in __uuids:
        return
    __uuids.remove(uuid)
