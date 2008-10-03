# GStreamer QA system
#
#       tests/simple-encoder.py
#
# Copyright (c) 2007, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2008 Nokia Corporation
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
Simple encoder test
"""

from insanity.test import GStreamerTest
import gst

class SimpleEncoderTest(GStreamerTest):

    __test_name__ = "simple-encoder-test"
    __test_description__ = """Test encoding for video"""
    __test_arguments__ = {
        "codec" : ("Codec to use",
            "theora",
            None),
        "num-buffers": ( "Numbfer of buffers to use",
            100,
            None),
        "bitrate": ( "The bitrate of the resulting video",
            800,
            None)
        # TODO: add frame-size configuration
        }

    __test_output_files__ = {
        "video-enc":"Output file"
        }

    # mandatory
    @classmethod
    def get_file(self):
        import os.path
        return os.path.abspath(__file__)

    def remoteSetUp(self):
        self._codec = self.arguments.get("codec", "theora")
        self._num_buffers = self.arguments.get("num-buffers", 100)
        self._bitrate = self.arguments.get("bitrate", 800)
        self._out_file = self._outputfiles["video-enc"]
        # self._out_file = None
        GStreamerTest.remoteSetUp(self)

    def createPipeline(self):
        p = gst.Pipeline()

        base = self._codec
        src = gst.element_factory_make("videotestsrc")
        src.props.num_buffers = self._num_buffers
        enc = gst.element_factory_make(base + "enc")
        enc.props.bitrate = self._bitrate

        if self._out_file:
            try:
                mux = gst.element_factory_make("matroskamux")
                sink = gst.element_factory_make("filesink")
            except gst.ElementNotFoundError:
                self._out_file = None
            else:
                sink.props.location = self._out_file

                p.add(src, enc, mux, sink)
                gst.element_link_many(src, enc, mux, sink)

        if not self._out_file:
            mux = None
            sink = gst.element_factory_make("fakesink")

            p.add(src, enc, sink)
            gst.element_link_many(src, enc, sink)

        return p

    def pipelineReachedInitialState(self):
	return False
