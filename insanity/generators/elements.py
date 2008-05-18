# GStreamer QA system
#
#       generators/elements.py
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
GstElement-related generators
"""

import string
from insanity.generator import Generator
from insanity.log import critical, error, warning, debug, info

class ElementGenerator(Generator):
    """
    Expands to a list of gst.ElementFactory
    """

    __args__ = {
        "class":"list of Class to filter against"
        }

    def _generate(self):
        def list_compat(a,b):
            for x in a:
                if not x in b:
                    return False
            return True

        res = []
        classes = self.kwargs.get("class", [])
        all = gst.registry_get_default().get_feature_list(gst.TYPE_ELEMENT_FACTORY)
        # filter by class
        for fact in all:
            if list_compat(classes, string.split(fact.get_klass(), '/')):
                res.append(fact)
        return res

class MuxerGenerator(ElementGenerator):
    """
    Expands to a list of muxers
    """

    def __init__(self, *args, **kwargs):
        kwargs["class"] = ["Codec", "Muxer"]
        ElementGenerator.__init__(self, *args, **kwargs)

class AudioEncoderGenerator(ElementGenerator):
    """
    Expands to a list of audio encoder factories
    """

    def __init__(self, *args, **kwargs):
        kwargs["class"] = ["Codec", "Encoder", "Audio"]
        ElementGenerator.__init__(self, *args, **kwargs)

class VideoEncoderGenerator(ElementGenerator):
    """
    Expands to a list of video encoder factories
    """

    def __init__(self, *args, **kwargs):
        kwargs["class"] = ["Codec", "Encoder"]
        ElementGenerator.__init__(self, *args, **kwargs)

    def _generate(self):
        res = []
        facts = ElementGenerator._generate(self)
        # filter those which have Video or Image
        for fact in facts:
            klasses = string.split(fact.get_klass(), '/')
            if "Video" in klasses or "audio" in klasses:
                res.append(fact)
        return res

class EncoderMuxerGenerator(Generator):
    """
    Expand to a list of all possible combinations of:
    (
      * audio encoder
      * video encoder
      * muxer
    )
    for a given audio encoder and/or video encoder and/or
    muxer.

    If one (or all) factory is not specified, then it will
    use all available factories of that class on the given
    system.

    The contents of the tuple are gst.ElementFactory.

    If the muxer can handle raw formats, the adequate encoder
    field it will contain the 'identity' gst.ElementFactory.

    If the 'single_streams' argument is set to True, then the
    returned list will also contain combinations with only one
    encoder, in which case that field will contain 'None'.
    """

    __args__ = {
        "muxer":"Name of the Muxer to filter the results against",
        "audio_encoder":"Name of the Audio Encoder to filter the results against",
        "video_encoder":"Name of the Video Encoder to filter the results against",
        "single_streams":"Also returns single-encoder combinations if True"
        }

    def _generate(self):
        muxername = self.kwargs.get("muxer", None)
        aencname = self.kwargs.get("audio_encoder", None)
        vencname = self.kwargs.get("video_encoder", None)
        singlestreams = self.kwargs.get("single_streams", False)

        muxer = gst.element_factory_find(muxername)
        aenc = gst.element_factory_find(aencname)
        venc = gst.element_factory_find(vencname)

        if muxer:
            allmuxers = [muxer]
        else:
            allmuxers = MuxerGenerator().generate()

        if aenc:
            allaencs = [aenc]
        else:
            allaencs = AudioEncoderGenerator().generate()

        if venc:
            allvencs = [venc]
        else:
            allvencs = VideoEncoderGenerator().generate()

        def can_sink_caps(muxer, ocaps):
            sinkcaps = [x.get_caps() for x in muxer.get_static_pad_templates() if x.direction == gst.PAD_SINK]
            for x in sinkcaps:
                if not x.intersect(ocaps).is_empty():
                    return True
            return False

        def encoders_muxer_compatible(encoders, muxer):
            res = []
            for encoder in encoders:
                for caps in [x.get_caps() for x in encoder.get_static_pad_templates() if x.direction == gst.PAD_SRC]:
                    if my_can_sink_caps(muxer, caps):
                        res.append(encoder)
                        break
            return res


        res = []
        for mux in allmuxers:
            # get the compatible encoders, without forgetting the
            # raw pads
            compatvenc = encoders_muxer_compatible(allvencs, mux)
            compataenc = encoders_muxer_compatible(allaencs, mux)
            if can_sink_caps(mux, gst.Caps("audio/x-raw-int;audio/x-raw-float")):
                compataenc.append(gst.element_factory_find("identity"))
            if can_sink_caps(mux, gst.Caps("video/x-raw-rgb;video/x-raw-yuv")):
                compatvenc.append(gst.element_factory_find("identity"))

            # and now produce the tuples
            for venc in compatvenc:
                for aenc in compataenc:
                    res.append((aenc, venc, mux))

            if singlestreams:
                for venc in compatvenc:
                    res.append((None, venc, mux))
                for aenc in compataenc:
                    res.append((aenc, None, mux))

        return res
