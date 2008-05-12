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

from gstqa.test import GStreamerTest
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
                       gst.caps_new_any(),
                       None),
        "audio-caps": ("caps to use when generating the raw audio stream to be encoded",
                       gst.caps_new_any(),
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
        self._outFD, self._outPath = self.testrun.get_temp_file(nameid="encodmux-file")
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
            muxer = gst.element_factory_make(self._muxerFact, "muxer")
        else:
            muxer = gst.element_factory_make("identity", "muxer")
        filesink = gst.element_factory_make("filesink")
        filesink.props.location = self._outPath
        p.add(muxer, filesink)
        muxer.link(filesink)

        # audio source + capsfilter + encoder
        if self._encodeAudio:
            audiosrc = make_audio_test_source(duration=self._mediaDuration)
            enc = gst.element_factory_make(self._videoFact)
            vq = gst.element_factory_make("queue", "videoqueue")
            p.add(audiosrc, enc, vq)
            if self._audioCaps:
                audiosrc.link(enc, gst.Caps(self._audioCaps))
            else:
                audiosrc.link(enc)
            gst.element_link_many(enc, vq, muxer)

        # video source + capsfilter + encoder
        if self._encodeVideo:
            videosrc = make_video_test_source(duration=self._mediaDuration)
            enc = gst.element_factory_make(self._videoFact)
            vq = gst.element_factory_make("queue", "videoqueue")
            p.add(videosrc, enc, vq)
            if self._videoCaps:
                videosrc.link(enc, gst.Caps(self._videoCaps))
            else:
                videosrc.link(enc)
            gst.element_link_many(enc, vq, muxer)

        return p

    def remoteTearDown(self):
        if not GStreamerTest.remoteTearDown(self):
            return False
        # if output file is non-empty, validate it !
        if self._outFD:
            os.close(self._outFD)
        if not os.path.getsize(self._outPath):
            warning("output file is empty, not signaling")
            os.remove(self._outPath)
        else:
            self.setOutputFile("encoded-muxed-file",
                               self._outPath)
        return True

    def pipelineReachedInitialState(self):
        return False
