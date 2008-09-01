# GStreamer QA system
#
#       tests/playbin.py
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
Tests using playbin
"""

from insanity.test import GStreamerTest
import gst

class PlaybinTest(GStreamerTest):

    __test_name__ = "playbin-test"
    __test_description__ = """Test the behaviour of playbin"""
    __test_arguments__ = {
        "uri" : ( "URI to test with playbin", None, None)
        }

    @classmethod
    def get_file(self):
        import os.path
        return os.path.abspath(__file__)

    def createPipeline(self):
        try:
            p = gst.element_factory_make("playbin2")
        except:
            p = gst.element_factory_make("playbin")
        p.props.uri = self.arguments["uri"]
        p.props.audio_sink = gst.element_factory_make("fakesink", "audio-fake-sink")
        p.props.video_sink = gst.element_factory_make("fakesink", "video-fake-sink")
        return p
