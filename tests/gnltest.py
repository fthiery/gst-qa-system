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

class GnlFullFileSourceTest(GnlFileSourceTest):

    __test_name__ = "full-gnlfilesource-test"

    __test_description__ = ""

    __test_arguments__ = {}

    __test_checklist__ = {
        "correct-last-buffer" : "The last buffer ends at stop"
        }

    __test_extra_infos__ = {
        "last-buffer-timestamp" : "The timestamp of the last buffer",
        "last-buffer-duration" : "The duration of the last buffer",
        "last-buffer-diff" : "Difference between end of last buffer and expected"
        }

    __pipeline_initial_state__ = gst.STATE_PLAYING

    @classmethod
    def get_file(self):
        import os.path
        return os.path.abspath(__file__)

    def remoteSetUp(self):
        self._lastBuffer = None
        GnlFileSourceTest.remoteSetUp(self)

    def _dataProbeCb(self, pad, data):
        if isinstance(data, gst.Buffer):
            gst.warning("Saw buffer %s (dur:%s) => %s" % (gst.TIME_ARGS(data.timestamp),
                                                          gst.TIME_ARGS(data.duration),
                                                          gst.TIME_ARGS(data.timestamp+data.duration)))
            self._lastBuffer = data
        return GnlFileSourceTest._dataProbeCb(self, pad, data)

    def createPipeline(self):
        db = SingleDecodeBin(caps=gst.Caps(self._caps),
                             uri=self.arguments["uri"])
        self.gnlfilesource = gst.element_factory_make("gnlsource")
        self.gnlfilesource.props.start = self._start
        self.gnlfilesource.props.duration = self._duration
        self.gnlfilesource.props.media_start = self._mstart
        self.gnlfilesource.props.media_duration = self._mduration
        self.gnlfilesource.add(db)

        self._fakesink = gst.element_factory_make("fakesink")
        self.gnlfilesource.connect("pad-added", self._padAddedCb)
        self._fakesink.get_pad("sink").add_data_probe(self._dataProbeCb)

        p = gst.Pipeline()
        p.add(self.gnlfilesource, self._fakesink)

        return p
    def pipelineReachedInitialState(self):
        return False

    def handleBusMessage(self, message):
        if message.type == gst.MESSAGE_SEGMENT_DONE:
            debug("Segment done")
            self._analyze()
            self.stop()

    def _analyze(self):
        if self._lastBuffer:
            self.extraInfo("last-buffer-timestamp",
                           self._lastBuffer.timestamp)
            self.extraInfo("last-buffer-duration",
                           self._lastBuffer.duration)
            self.extraInfo("last-buffer-diff",
                           (self._lastBuffer.timestamp+self._lastBuffer.duration) - (self._mstart+self._mduration))
            self.validateStep("correct-last-buffer",
                              self._lastBuffer.timestamp+self._lastBuffer.duration==self._mstart+self._mduration)



import gobject
import gst

def is_raw(caps):
    """ returns True if the caps are RAW """
    rep = caps.to_string()
    valid = ["video/x-raw", "audio/x-raw", "text/plain", "text/x-pango-markup"]
    for val in valid:
        if rep.startswith(val):
            return True
    return False

class SingleDecodeBin(gst.Bin):
    """
    A variant of decodebin.

    * Only outputs one stream
    * Doesn't contain any internal queue
    """

    __gsttemplates__ = (
        gst.PadTemplate ("sinkpadtemplate",
                         gst.PAD_SINK,
                         gst.PAD_ALWAYS,
                         gst.caps_new_any()),
        gst.PadTemplate ("srcpadtemplate",
                         gst.PAD_SRC,
                         gst.PAD_SOMETIMES,
                         gst.caps_new_any())
        )
    def __init__(self, caps=None, uri=None, *args, **kwargs):
        gst.Bin.__init__(self, *args, **kwargs)
        if not caps:
            caps = gst.caps_new_any()
        self.caps = caps
        self.typefind = gst.element_factory_make("typefind", "internal-typefind")
        self.add(self.typefind)

        self.uri = uri
        if self.uri and gst.uri_is_valid(self.uri):
            self.urisrc = gst.element_make_from_uri(gst.URI_SRC, uri, "urisrc")
            self.log("created urisrc %s / %r" % (self.urisrc.get_name(),
                                                 self.urisrc))
            self.add(self.urisrc)
            self.urisrc.link(self.typefind)
        else:
            self._sinkpad = gst.GhostPad("sink", self.typefind.get_pad("sink"))
            self._sinkpad.set_active(True)
            self.add_pad(self._sinkpad)

        self.typefind.connect("have_type", self._typefindHaveTypeCb)

        self._srcpad = None

        self._dynamics = []

        self._validelements = [] #added elements

        self._factories = self._getSortedFactoryList()


    ## internal methods

    def _controlDynamicElement(self, element):
        self.log("element:%s" % element.get_name())
        self._dynamics.append(element)
        element.connect("pad-added", self._dynamicPadAddedCb)
        element.connect("no-more-pads", self._dynamicNoMorePadsCb)

    def _getSortedFactoryList(self):
        """
        Returns the list of demuxers, decoders and parsers available, sorted
        by rank
        """
        def _myfilter(fact):
            if fact.get_rank() < 64 :
                return False
            klass = fact.get_klass()
            if not ("Demuxer" in klass or "Decoder" in klass or "Parse" in klass):
                return False
            return True
        reg = gst.registry_get_default()
        res = [x for x in reg.get_feature_list(gst.ElementFactory) if _myfilter(x)]
        res.sort(lambda a, b: int(b.get_rank() - a.get_rank()))
        return res

    def _findCompatibleFactory(self, caps):
        """
        Returns a list of factories (sorted by rank) which can take caps as
        input. Returns empty list if none are compatible
        """
        self.debug("caps:%s" % caps.to_string())
        res = []
        for factory in self._factories:
            for template in factory.get_static_pad_templates():
                if template.direction == gst.PAD_SINK:
                    intersect = caps.intersect(template.static_caps.get())
                    if not intersect.is_empty():
                        res.append(factory)
                        break
        self.debug("returning %r" % res)
        return res

    def _closeLink(self, element):
        """
        Inspects element and tries to connect something on the srcpads.
        If there are dynamic pads, it sets up a signal handler to
        continue autoplugging when they become available.
        """
        to_connect = []
        dynamic = False
        templates = element.get_pad_template_list()
        for template in templates:
            if not template.direction == gst.PAD_SRC:
                continue
            if template.presence == gst.PAD_ALWAYS:
                pad = element.get_pad(template.name_template)
                to_connect.append(pad)
            elif template.presence == gst.PAD_SOMETIMES:
                pad = element.get_pad(template.name_template)
                if pad:
                    to_connect.append(pad)
                else:
                    dynamic = True
            else:
                self.log("Template %s is a request pad, ignoring" % pad.name_template)

        if dynamic:
            self.debug("%s is a dynamic element" % element.get_name())
            self._controlDynamicElement(element)

        for pad in to_connect:
            self._closePadLink(element, pad, pad.get_caps())

    def _tryToLink1(self, source, pad, factories):
        """
        Tries to link one of the factories' element to the given pad.

        Returns the element that was successfully linked to the pad.
        """
        self.debug("source:%s, pad:%s , factories:%r" % (source.get_name(),
                                                         pad.get_name(),
                                                         factories))
        result = None
        for factory in factories:
            element = factory.create()
            if not element:
                self.warning("weren't able to create element from %r" % factory)
                continue

            sinkpad = element.get_pad("sink")
            if not sinkpad:
                continue

            self.add(element)
            element.set_state(gst.STATE_READY)
            try:
                pad.link(sinkpad)
            except:
                element.set_state(gst.STATE_NULL)
                self.remove(element)
                continue

            self._closeLink(element)
            element.set_state(gst.STATE_PAUSED)

            result = element
            break

        return result

    def _closePadLink(self, element, pad, caps):
        """
        Finds the list of elements that could connect to the pad.
        If the pad has the desired caps, it will create a ghostpad.
        If no compatible elements could be found, the search will stop.
        """
        self.debug("element:%s, pad:%s, caps:%s" % (element.get_name(),
                                                    pad.get_name(),
                                                    caps.to_string()))
        if caps.is_empty():
            self.log("unknown type")
            return
        if caps.is_any():
            self.log("type is not know yet, waiting")
            return
        if caps.intersect(self.caps):
            # This is the desired caps
            if not self._srcpad:
                self._wrapUp(element, pad)
        elif is_raw(caps):
            self.log("We hit a raw caps which isn't the wanted one")
            # FIXME : recursively remove everything until demux/typefind

        else:
            # Find something
            if len(caps) > 1:
                self.log("many possible types, delaying")
                return
            facts = self._findCompatibleFactory(caps)
            if not facts:
                self.log("unknown type")
                return
            self._tryToLink1(element, pad, facts)

    def _wrapUp(self, element, pad):
        """
        Ghost the given pad of element.
        Remove non-used elements.
        """

        if self._srcpad:
            return
        self._markValidElements(element)
        self._removeUnusedElements(self.typefind)
        self.log("ghosting pad %s" % pad.get_name())
        self._srcpad = gst.GhostPad("src", pad)
        self._srcpad.set_active(True)
        self.add_pad(self._srcpad)
        self.post_message(gst.message_new_state_dirty(self))

    def _markValidElements(self, element):
        """
        Mark this element and upstreams as valid
        """
        self.log("element:%s" % element.get_name())
        if element == self.typefind:
            return
        self._validelements.append(element)
        # find upstream element
        pad = list(element.sink_pads())[0]
        parent = pad.get_peer().get_parent()
        self._markValidElements(parent)

    def _removeUnusedElements(self, element):
        """
        Remove unused elements connected to srcpad(s) of element
        """
        self.log("element:%r" % element)
        for pad in element.src_pads():
            if pad.is_linked():
                peer = pad.get_peer().get_parent()
                self._removeUnusedElements(peer)
                if not peer in self._validelements:
                    self.log("removing %s" % peer.get_name())
                    pad.unlink(pad.get_peer())
                    peer.set_state(gst.STATE_NULL)
                    self.remove(peer)

    def _cleanUp(self):
        self.log("")
        if self._srcpad:
            self.remove_pad(self._srcpad)
        self._srcpad = None
        for element in self._validelements:
            element.set_state(gst.STATE_NULL)
            self.remove(element)
        self._validelements = []

    ## Overrides

    def do_change_state(self, transition):
        self.debug("transition:%r" % transition)
        res = gst.Bin.do_change_state(self, transition)
        if transition == gst.STATE_CHANGE_PAUSED_TO_READY:
            self._cleanUp()
        return res

    ## Signal callbacks

    def _typefindHaveTypeCb(self, typefind, probability, caps):
        self.debug("probability:%d, caps:%s" % (probability, caps.to_string()))
        self._closePadLink(typefind, typefind.get_pad("src"), caps)

    ## Dynamic element Callbacks

    def _dynamicPadAddedCb(self, element, pad):
        self.log("element:%s, pad:%s" % (element.get_name(), pad.get_name()))
        if not self._srcpad:
            self._closePadLink(element, pad, pad.get_caps())

    def _dynamicNoMorePadsCb(self, element):
        self.log("element:%s" % element.get_name())

gobject.type_register(SingleDecodeBin)
