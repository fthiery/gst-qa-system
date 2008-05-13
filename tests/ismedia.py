# GStreamer QA system
#
#       tests/ismedia.py
#
# Copyright (c) 2008, Edward Hervey <bilboed@bilboed.com>
##
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
Tests to detect if file is a valid media-file that can be handled by GStreamer
"""

from insanity.test import GStreamerTest
from insanity.log import critical, error, warning, debug, info
import gst

class IsMediaTest(GStreamerTest):

    __test_name__ = "is-media-test"
    __test_description__ = """Checks if uri is a format usable by GStreamer"""
    __test_arguments__ = {
        "uri" : ( "URI to test", None, None)
        }
    __test_checklist__ = {
        "is-valid-uri-format" : "The URI format is valid",
        "is-recognized-media" : "The media type can be handled by GStreamer"
        }
    __test_extra_infos__ = {
        "mime-type" : "GStreamer MIME type of the uri"
        }

    __pipeline_initial_state__ = gst.STATE_PAUSED

    @classmethod
    def get_file(self):
        import os.path
        return os.path.abspath(__file__)

    def createPipeline(self):
        # uri source
        uri = self.arguments["uri"]
        if not gst.uri_is_valid(uri):
            self.validateStep("is-valid-uri-format", False)
            return None

        self.validateStep("is-valid-uri-format")
        src = gst.element_make_from_uri(gst.URI_SRC, uri, "uri-src")

        typefind = gst.element_factory_make("typefind")
        fakesink = gst.element_factory_make("fakesink")

        p = gst.Pipeline()
        p.add(src, typefind, fakesink)
        gst.element_link_many(src,typefind,fakesink)
        # connect signals

        typefind.connect("have-type", self._typefindHaveTypeCb)

        return p

    def _typefindHaveTypeCb(self, typefind, prob, caps):
        debug("prob:%d, caps:%s", prob, caps.to_string())
        self.validateStep("is-recognized-media")
        self.remoteExtraInfoSignal("mime-type", caps.to_string())
