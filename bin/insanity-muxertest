#!/bin/env python

import sys
from optparse import OptionParser
from insanity.client import CommandLineTesterClient
from insanity.generators.elements import EncoderMuxerGenerator
from insanity.testrun import TestRun
from insanity.monitor import GstDebugLogMonitor
from tests.encoder import EncoderMuxerTest

class EncoderMuxerClient(CommandLineTesterClient):

    __software_name__ = """encoder-muxer-client"""

    def __init__(self, muxer=None, aenc=None, venc=None,
                 maxnbtests=1):
        CommandLineTesterClient.__init__(self,
                                         singlerun=True)
        gen = EncoderMuxerGenerator(muxer=muxer,
                                    audio_encoder=aenc,
                                    video_encoder=venc)
        monitors = [(GstDebugLogMonitor, {"debug-level":"3",
                                          "compress-logs":False})]

        testrun = TestRun(maxnbtests=maxnbtests)
        testrun.addTest(EncoderMuxerTest,
                        arguments = { "audio-encoder-factory,video-encoder-factory,muxer-factory" : gen,
                                      "encode-video" : True,
                                      "encode-audio" : True },
                        monitors=monitors)
        self.addTestRun(testrun)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-v", "--video", dest="video",
                      default=None,
                      help="Name of the video encoder factory")
    parser.add_option("-a", "--audio", dest="audio",
                      default=None,
                      help="Name of the audio encoder factory")
    parser.add_option("-m", "--muxer", dest="muxer",
                      default=None,
                      help="Name of the muxer encoder factory")
    parser.add_option("-S", "--simultaneous", dest="maxnbtests",
                      type="int", default=2,
                      help="Maximum number of simultaneous tests (default:1)")
    (options, args) = parser.parse_args(sys.argv[1:])
    cl = EncoderMuxerClient(options.muxer, options.audio,
                            options.video, options.maxnbtests)
    cl.run()
    
