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
Tests using GNonlin non-linear set of plugins
"""

import gobject
gobject.threads_init()
from insanity.test import GStreamerTest
from insanity.log import critical, error, warning, debug, info
import gst

def valtime(someval):
    if someval == gst.CLOCK_TIME_NONE:
        return -1
    return someval

class GnlFileSourceTest(GStreamerTest):

    __test_name__ = "gnlfilesource-test"
    __test_description__ = """
    Tests the behaviour of gnlfilesource on various files.
    """
    __test_arguments__ = {
        "uri" : ( "URI to test gnlfilesource with",
                  None, None ),
        "start" : ( "start position in nanoseconds",
                    0, None ),
        "duration" : ( "duration in nanoseconds",
                       gst.SECOND, None ) ,
        "media-start" : ( "media-start position in nanoseconds",
                          5 * gst.SECOND, None ),
        "media-duration" : ( "media-duration in nanoseconds",
                             None, "Same as duration if not specified" ),
        "caps-string" : ( "caps property to use on gnlfilesource as a string",
                          "audio/x-raw-int;audio/x-raw-float", None)
        }

    __test_checklist__ = {
        "correct-newsegment-format" : "The new-segment was in the correct format (gst.FORMAT_TIME)",
        "correct-newsegment-start" : "The new-segment had the correct 'start' value",
        "correct-newsegment-stop" : "The new-segment had the correct 'stop' value",
        "correct-newsegment-position" : "The new-segment had the correct 'position' value",
        "correct-initial-buffer" : "The first buffer received had the proper timestamp",
        "first-buffer-after-newsegment" : "The first buffer was seen after a newsegment"
        }

    __test_extra_infos__ = {
        "first-buffer-timestamp" : "The timestamp of the first buffer",
        "newsegment-values" : "The values of the first newsegment"
        }

    __pipeline_initial_state__ = gst.STATE_PAUSED

    @classmethod
    def get_file(self):
        import os.path
        return os.path.abspath(__file__)

    def remoteSetUp(self):
        self._fakesink = None
        self._gotFirstBuffer = False
        self._gotNewSegment = False
        self._start = self.arguments.get("start", 0)
        self._duration = self.arguments.get("duration", gst.SECOND)
        self._mstart = self.arguments.get("media-start", 5 * gst.SECOND)
        self._mduration = self.arguments.get("media-duration", self._duration)
        warning("Got caps-string:%r", self.arguments.get("caps-string", "audio/x-raw-int;audio/x-raw-float"))
        self._caps = gst.Caps(str(self.arguments.get("caps-string", "audio/x-raw-int;audio/x-raw-float")))
        GStreamerTest.remoteSetUp(self)

    def createPipeline(self):
        self.gnlfilesource = gst.element_factory_make("gnlfilesource")
        self.gnlfilesource.props.location = self.arguments["uri"]
        self.gnlfilesource.props.start = self._start
        self.gnlfilesource.props.duration = self._duration
        self.gnlfilesource.props.media_start = self._mstart
        self.gnlfilesource.props.media_duration = self._mduration
        self.gnlfilesource.props.caps = self._caps

        self._fakesink = gst.element_factory_make("fakesink")
        self.gnlfilesource.connect("pad-added", self._padAddedCb)
        self._fakesink.get_pad("sink").add_data_probe(self._dataProbeCb)

        p = gst.Pipeline()
        p.add(self.gnlfilesource, self._fakesink)

        return p

    def _padAddedCb(self, source, pad):
        source.link(self._fakesink)

    def _dataProbeCb(self, pad, data):
        if isinstance(data, gst.Buffer):
            debug("buffer %s", gst.TIME_ARGS(data.timestamp))
            if not self._gotFirstBuffer:
                self.extraInfo("first-buffer-timestamp", valtime(data.timestamp))
                self.validateStep("correct-initial-buffer", data.timestamp == self._mstart)
                self.validateStep("first-buffer-after-newsegment", self._gotNewSegment)
                self._gotFirstBuffer = True
        elif data.type == gst.EVENT_NEWSEGMENT:
            if not self._gotNewSegment:
                debug("newsegment")
                self.extraInfo("newsegment-values", data.parse_new_segment())
                # make sure the newsegment is valid
                update, rate, format, start, stop, position = data.parse_new_segment()
                self.validateStep("correct-newsegment-format", format == gst.FORMAT_TIME)
                self.validateStep("correct-newsegment-start", start == self._mstart)
                self.validateStep("correct-newsegment-stop",stop == self._mstart + self._mduration)
                self.validateStep("correct-newsegment-position", position == self._start)
                if self._gotFirstBuffer:
                    gobject.idle_add(self.stop)
                self._gotNewSegment = True
            else:
                gobject.idle_add(self.stop)
        return True
