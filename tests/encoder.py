# GStreamer QA system
#
#       tests/encoder.py
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
Series of tests to test encoder behaviour
"""

from insanity.test import GStreamerTest
from insanity.log import critical, error, warning, debug, info, exception
import gst
import os
import os.path

##
## PUT THIS IN SOME COMMON FILE !!!


def make_gnl_source(source, start=0, media_start=0, duration=20*gst.SECOND):
    gnl = gst.element_factory_make("gnlsource")
    gnl.add(source)
    gnl.props.duration = duration
    gnl.props.media_duration = duration
    gnl.props.start = start
    gnl.props.media_start = media_start
    comp = gst.element_factory_make("gnlcomposition")
    comp.add(gnl)
    return comp

def make_video_test_source(pattern=0, *args, **kwargs):
    vsrc = gst.element_factory_make("videotestsrc")
    vsrc.props.pattern = pattern
    return make_gnl_source(vsrc, *args, **kwargs)

def make_audio_test_source(*args, **kwargs):
    asrc = gst.element_factory_make("audiotestsrc")
    return make_gnl_source(asrc, *args, **kwargs)


##
## TODO / FIXME
##
## check all steps of the pipeline creation


class EncoderMuxerTest(GStreamerTest):

    __test_description__ = """
    Encodes raw audio and/or video using the specified encoder(s) and muxer.
    """
    __test_name__ = "encoder-muxer-test"
    __test_arguments__ = {
        "encode-video": ("Should video be generated and encoded",
                         False,
                         None),
        "encode-audio": ("Should audio be generated and encoded",
                         False,
                         None),
        "video-caps": ("caps to use when generating the raw video stream to be encoded",
                       "ANY",
                       None),
        "audio-caps": ("caps to use when generating the raw audio stream to be encoded",
                       "ANY",
                       None),
        "video-encoder-factory": ("Name of the gst.ElementFactory to use to encode the video stream",
                                  None,
                                  None),
        "audio-encoder-factory": ("Name of the gst.ElementFactory to use to encode the audio stream",
                                  None,
                                  None),
        "muxer-factory": ( "Name of the gst.ElementFactory to use to contain the streams",
                           None,
                           None ),
        "media-duration": ( "Duration of the media to generate (in nanoseconds)",
                            20 * gst.SECOND,
                            None ),
        "media-offset": ( "Initial buffer timestamp",
                          0,
                          None )
        }

    __test_output_files__ = {
        "encoded-muxed-file":"Output of the encoding/muxer combination"
        }

    @classmethod
    def get_file(self):
        import os.path
        return os.path.abspath(__file__)

    def remoteSetUp(self):
        # first check if we have enough arguments to create a valid pipeline
        self._encodeVideo = self.arguments.get("encode-video", False)
        self._encodeAudio = self.arguments.get("encode-audio", False)
        self._videoFact = self.arguments.get("video-encoder-factory")
        self._audioFact = self.arguments.get("audio-encoder-factory")
        self._videoCaps = self.arguments.get("video-caps")
        self._audioCaps = self.arguments.get("audio-caps")
        self._muxerFact = self.arguments.get("muxer-factory")
        self._mediaDuration = self.arguments.get("media-duration", 20 * gst.SECOND)
        self._audioSource = None
        self._videoSource = None
        self._audioEncoder = None
        self._videoEncoder = None
        self._muxer = None
        debug("about to get outputfile")
        self._outPath = self._outputfiles["encoded-muxed-file"]
        debug("got outputfile %s", self._outPath)
        GStreamerTest.remoteSetUp(self)

    def createPipeline(self):
        if self._encodeVideo == False and self._encodeAudio == False:
            warning("NO audio and NO video ??")
            return None

        if (self._encodeVideo and self._encodeAudio) and not self._muxerFact:
            warning("NO muxer but we have two tracks ??")
            return None

        p = gst.Pipeline()

        # muxer and filesink
        if self._muxerFact:
            self._muxer = gst.element_factory_make(self._muxerFact, "muxer")
        else:
            self._muxer = gst.element_factory_make("identity", "muxer")
        filesink = gst.element_factory_make("filesink")
        filesink.props.location = self._outPath
        p.add(self._muxer, filesink)
        self._muxer.link(filesink)

        # FIXME : source ! encoder needs to be linked asynchronously because
        # the composition/source will create the source pad dynamically
        # audio source + capsfilter + encoder
        if self._encodeAudio:
            self._audioSource = make_audio_test_source(duration=self._mediaDuration)
            self._audioEncoder = gst.element_factory_make(self._audioFact)
            vq = gst.element_factory_make("queue", "audioqueue")
            p.add(self._audioSource, self._audioEncoder, vq)
            gst.element_link_many(self._audioEncoder, vq, self._muxer)
            self._audioSource.connect("pad-added",
                                      self._audioSourcePadAdded)

        # video source + capsfilter + encoder
        if self._encodeVideo:
            self._videoSource = make_video_test_source(duration=self._mediaDuration)
            enc = gst.element_factory_make(self._videoFact)
            self._videoEncoder = gst.element_factory_make("ffmpegcolorspace")
            vq = gst.element_factory_make("queue", "videoqueue")
            p.add(self._videoSource, self._videoEncoder, enc, vq)
            gst.element_link_many(self._videoEncoder, enc, vq, self._muxer)
            self._videoSource.connect("pad-added",
                                      self._videoSourcePadAdded)

        return p

    def _audioSourcePadAdded(self, audioSource, pad):
        debug("pad %r, audioCaps:%r", pad, self._audioCaps)
        try:
            if self._audioCaps:
                self._audioSource.link(self._audioEncoder, gst.Caps(self._audioCaps))
            else:
                self._audioSource.link(self._audioEncoder)
        finally:
            debug("done")

    def _videoSourcePadAdded(self, videoSource, pad):
        debug("pad %r, videoCaps:%r", pad, self._videoCaps)
        try:
            if self._videoCaps:
                self._videoSource.link(self._videoEncoder, gst.Caps(self._videoCaps))
            else:
                self._videoSource.link(self._videoEncoder)
        finally:
            debug("done")

    def pipelineReachedInitialState(self):
        return False
