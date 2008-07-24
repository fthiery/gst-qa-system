# GStreamer QA system
#
#       generators/playlist.py
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
Playlist-related generators
"""

from insanity.generator import Generator
#from insanity.log import critical, error, warning, debug, info

# FIXME
#   Should check to see if we actually have valid URI(s)

class PlaylistGenerator(Generator):
    """
    Takes a list of playlist file location
    Returns a full list of URIs contained in those files
    """

    __args__ = {
        "location":"location of the playlist file"
        }

    def _generate(self):
        res = []
        location = self.kwargs.get("location", None)
        if not location:
            return res
        resfile = open(location, "r")
        # this is a bit too simplistic
        res = [x.strip() for x in resfile.readlines() if x.strip()]
        resfile.close()
        return res

