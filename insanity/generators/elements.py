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

import gst
from insanity.generator import Generator
from insanity.log import critical, error, warning, debug, info

class ElementGenerator(Generator):
    """
    Expands to a list of gst.ElementFactory names that
    match the given list of Class.

    If no list of Class is specified, then all available
    gst.ElementFactory available on the system is returned.
    """

    __args__ = {
        "classes":"list of Class to filter against",
        "factories":"If set to True, will return objects and not strings"
        }

    def _generate(self):
        def list_compat(a, b):
            for x in a:
                if not x in b:
                    return False
            return True

        res = []
        classes = self.kwargs.get("classes", [])
        retfact = self.kwargs.get("factories", False)
        allf = gst.registry_get_default().get_feature_list(gst.TYPE_ELEMENT_FACTORY)
        # filter by class
        for fact in allf:
            if list_compat(classes, fact.get_klass().split('/')):
                if retfact:
                    res.append(fact)
                else:
                    res.append(fact.get_name())
        return res

class MuxerGenerator(ElementGenerator):
    """
    Expands to a list of muxers
    """

    def __init__(self, *args, **kwargs):
        kwargs["classes"] = ["Codec", "Muxer"]
        ElementGenerator.__init__(self, *args, **kwargs)

class AudioEncoderGenerator(ElementGenerator):
    """
    Expands to a list of audio encoder factories
    """

    def __init__(self, *args, **kwargs):
        kwargs["classes"] = ["Codec", "Encoder", "Audio"]
        ElementGenerator.__init__(self, *args, **kwargs)

class VideoEncoderGenerator(ElementGenerator):
    """
    Expands to a list of video encoder factories
    """

    def __init__(self, *args, **kwargs):
        kwargs["classes"] = ["Codec", "Encoder"]
        ElementGenerator.__init__(self, *args, **kwargs)

    def _generate(self):
        res = []
        facts = ElementGenerator._generate(self)
        # filter those which have Video or Image
        for fact in facts:
            klasses = fact.get_klass().split('/')
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
    field will contain 'identity'.

    If the 'single_streams' argument is set to True, then the
    returned list will also contain combinations with only one
    encoder, in which case that field will contain 'None'.
    """

    __args__ = {
        "muxer":"Name of the Muxer to filter the results against",
        "audio_encoder":"Name of the Audio Encoder to filter the results against",
        "video_encoder":"Name of the Video Encoder to filter the results against",
        "single_streams":"Also returns single-encoder combinations if True",
        "factories":"Returns object and not names if set to True"
        }

    def _generate(self):
        muxername = self.kwargs.get("muxer", None)
        aencname = self.kwargs.get("audio_encoder", None)
        vencname = self.kwargs.get("video_encoder", None)
        singlestreams = self.kwargs.get("single_streams", False)
        retfact = self.kwargs.get("factories", False)

        muxer = muxername and gst.element_factory_find(muxername)
        aenc = aencname and gst.element_factory_find(aencname)
        venc = vencname and gst.element_factory_find(vencname)

        if muxer:
            allmuxers = [muxer]
        else:
            allmuxers = MuxerGenerator(factories=True).generate()

        if aenc:
            allaencs = [aenc]
        else:
            allaencs = AudioEncoderGenerator(factories=True).generate()

        if venc:
            allvencs = [venc]
        else:
            allvencs = VideoEncoderGenerator(factories=True).generate()

        def can_sink_caps(muxer, ocaps):
            sinkcaps = [x.get_caps() for x in muxer.get_static_pad_templates() if x.direction == gst.PAD_SINK and not x.get_caps().is_any()]
            for x in sinkcaps:
                if not x.intersect(ocaps).is_empty():
                    return True
            return False

        def encoders_muxer_compatible(encoders, muxer):
            res = []
            for encoder in encoders:
                for caps in [x.get_caps() for x in encoder.get_static_pad_templates() if x.direction == gst.PAD_SRC]:
                    if can_sink_caps(muxer, caps):
                        res.append(encoder)
                        break
            return res

        res = []
        # reduce allmuxers to those intersecting with the encoders
        for mux in allmuxers:
            # get the compatible encoders, without forgetting the
            # raw pads
            compatvenc = encoders_muxer_compatible(allvencs, mux)
            compataenc = encoders_muxer_compatible(allaencs, mux)

            # skip muxers than don't accept the specified encoders
            if vencname and not gst.element_factory_find(vencname) in compatvenc:
                continue
            if aencname and not gst.element_factory_find(aencname) in compataenc:
                continue

            if not aencname and can_sink_caps(mux, gst.Caps("audio/x-raw-int;audio/x-raw-float")):
                compataenc.append(gst.element_factory_find("identity"))
            if not vencname and can_sink_caps(mux, gst.Caps("video/x-raw-rgb;video/x-raw-yuv")):
                compatvenc.append(gst.element_factory_find("identity"))

            # and now produce the tuples
            for venc in compatvenc:
                for aenc in compataenc:
                    if retfact:
                        res.append((aenc, venc, mux))
                    else:
                        res.append((aenc.get_name(),
                                    venc.get_name(),
                                    mux.get_name()))

            if singlestreams:
                if not aencname:
                    for venc in compatvenc:
                        if retfact:
                            res.append((None, venc, mux))
                        else:
                            res.append((None, venc.get_name(),
                                        mux.get_name()))
                if not vencname:
                    for aenc in compataenc:
                        if retfact:
                            res.append((aenc, None, mux))
                        else:
                            res.append((aenc.get_name(), None,
                                        mux.get_name()))

        return res
