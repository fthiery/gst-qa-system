# GStreamer QA system
#
#       tests/typefind.py
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
Tests used to search as much information as possible from the given uri
"""

import gobject
gobject.threads_init()
from gstqa.log import critical, error, warning, debug, info
from gstqa.test import GStreamerTest
import dbus
import gst

class Stream:

    def __init__(self, pad, raw=True, length=-1, caps=None):
        debug("pad:%r, raw:%r", pad, raw)
        self.pad = pad
        self.raw = raw
        self.length = length
        self.caps = caps

    def serialize_dict(self):
        if self.pad.get_negotiated_caps():
            rescaps = self.pad.get_negotiated_caps().to_string()
        else:
            rescaps = self.pad.get_caps().to_string()
        return {"padname":self.pad.get_name(),
                "length":time_to_string(self.length),
                "caps":rescaps}

class TypeFindTest(GStreamerTest):
    __test_name__ = "typefind-test"
    __test_description__ = """
    Tests the multimedia play-ability of a given uri with GStreamer
    """
    __test_arguments__ = {
        "uri" : "URI to test"
        }
    __test_checklist__ = {
        "known-mime-type" : "The mimetype of the URI was recognized by GStreamer",
        "is-media-type" : "The URI contains a multimedia format",
        "available-demuxer" : "We have an element capable of handling the container mimetype",
        "all-streams-decodable" : "We have decoders for all streams contained within the media",
        "all-fixed-caps-streams" : "We could get fixed caps for all raw streams",
        "duration-available" : "The duration of the file is available",
        "stream-duration-identical" : "The duration of all streams are identical"
        }

    __test_extra_infos__ = {
        "mimetype" : "The mimetype of the URI",
        "redirection-uri" : "A redirection URI",
        "total-uri-duration" : "The total duration of the URI",
        "unknown-mime-type" : "Mimetype of formats we don't know how to handle",
        "unhandled-formats" : "List of formats GStreamer can not handle",
        "streams" : "List of stream information (padname, length(ns), caps)"
        }

    __pipeline_initial_state__ = gst.STATE_PAUSED

    @classmethod
    def get_file(self):
        import os.path
        return os.path.abspath(__file__)

    def createPipeline(self):
        self._src = gst.element_make_from_uri(gst.URI_SRC, self.arguments.get("uri"))
        try:
            self._dbin = gst.element_factory_make("decodebin2")
        except:
            self._dbin = gst.element_factory_make("decodebin")
        self._typefind = self._dbin.get_by_name("typefind")

        p = gst.Pipeline()
        p.add(self._src, self._dbin)
        self._src.link(self._dbin)

        self._streams = []
        self._mimetype = None

        self._typefind.connect("have-type", self._haveTypeCb)
        self._dbin.connect("unknown-type", self._unknownTypeCb)
        self._dbin.connect("new-decoded-pad", self._newDecodedPadCb)
        self._dbin.connect("no-more-pads", self._noMorePadsCb)

        return p

    def pipelineReachedInitialState(self):
        # do some checks based on what we have
        self._analyzeDecodebin()
        self._validateStreams()
        return True

    def _validateStreams(self):
        length, issimilar = self._getStreamsDuration()
        debug("length:%s, similar:%r", gst.TIME_ARGS(length), issimilar)
        self.validateStep("stream-duration-identical", issimilar)
        self.validateStep("duration-available", not length == -1)
        if not length == -1:
            self.extraInfo("total-uri-duration", length)
        self.validateStep("available-demuxer",
                          not self.mimetype in [s.caps.to_string() for s in self._streams])

        debug("allstreams : %s", [s.pad.get_name() for s in self._streams])
        raws = [s for s in self._streams if s.raw]
        notraws = [s for s in self._streams if not s.raw]
        nonfixedraw = [s for s in raws if not s.caps.is_fixed()]
        self.validateStep("all-fixed-caps-streams",
                          not len([s for s in raws if not s.caps.is_fixed()]))
        self.validateStep("all-streams-decodable", not len(notraws))
        if len(notraws):
            self.extraInfo("unhandled-formats", [s.caps.to_string() for s in notraws])
        xs = [(s.pad.get_name(), s.length, s.caps.to_string()) for s in self._streams]
        self.extraInfo("streams", dbus.Array(xs, signature="(sxs)"))


    def _analyzeDecodebin(self):
        debug("Querying length")
        for stream in self._streams:
            debug("pad %r / raw:%r", stream.pad, stream.raw)
            if stream.raw:
                stream.caps = stream.pad.get_negotiated_caps()
                if not stream.caps:
                    stream.caps = stream.pad.get_caps()
                try:
                    length,format = stream.pad.query_duration(gst.FORMAT_TIME)
                except:
                    warning("duration query failed")
                    length = -1
                stream.length = length
                debug("stream length %s", gst.TIME_ARGS(stream.length))

    def _getStreamsDuration(self):
        # returns duration, issimilar
        # if streams duration differ by more than 20%, issimilar is False
        vstreams = [s for s in self._streams if (s.raw)]
        if not vstreams:
            return (-1, False)
        if len(vstreams) == 1:
            return (vstreams[0].length, True)
        l = vstreams[0].length
        for s in vstreams[1:]:
            debug("length:%s", gst.TIME_ARGS(s.length))
            diff = abs(s.length - l)
            if diff > (l / 5):
                warning("length different by more than 20%%")
                return (l, False)
        return (l, True)

    def _haveTypeCb(self, pipeline, probability, caps):
        mt = caps.to_string()
        self.mimetype = mt
        debug("mimetype:%s", mt)
        self.extraInfo("mimetype", mt)
        self.validateStep("known-mime-type")
        if mt in ["application/x-executable",
                  "text/plain",
                  "text/uri-list",
                  "text/x-pango-markup",
                  "application/x-bzip",
                  "application/zip",
                  "application/x-gzip"
                  ]:
            debug("not a media type, stopping")
            gobject.idle_add(self.stop)
            self.validateStep("is-media-type", False)
        else:
            self.validateStep("is-media-type")

    def _unknownTypeCb(self, dbin, pad, caps):
        debug("caps:%s", caps.to_string())
        self.extraInfo("unknown-mime-type", caps.to_string())
        self._connectFakesink(pad, dbin)
        self._streams.append(Stream(pad, raw=False, caps=pad.get_caps()))

    def _newDecodedPadCb(self, dbin, pad, is_last):
        debug("pad:%r , caps:%s, is_last:%r", pad, pad.get_caps().to_string(), is_last)
        stream = Stream(pad, caps=pad.get_caps())
        self._connectFakesink(pad, self.pipeline)
        self._streams.append(stream)

    def _noMorePadsCb(self, dbin):
        debug("no more pads")
        if len([stream for stream in self._streams if not stream.raw]):
            debug("we have non-raw streams, stopping")
            # FIXME : add post-checking
            self._analyzeDecodebin()
            self._validateStreams()
            gobject.idle_add(self.stop)

    def _connectFakesink(self, pad, container):
        queue = gst.element_factory_make("queue")
        queue.props.max_size_time = 10 * gst.SECOND
        queue.props.max_size_buffers = 500
        fakesink = gst.element_factory_make("fakesink")
        #fakesink.props.sync = True

        container.add(queue, fakesink)
        fakesink.set_state(gst.STATE_PAUSED)
        queue.set_state(gst.STATE_PAUSED)
        queue.link(fakesink)
        pad.link(queue.get_pad("sink"))

