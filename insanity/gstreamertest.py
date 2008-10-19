# GStreamer QA system
#
#       gstreamertest.py
#
# Copyright (c) 2007, Edward Hervey <bilboed@bilboed.com>
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

import sys
import os

from insanity.log import error, warning, debug, info, exception
from insanity.test import PythonDBusTest

import dbus
import gobject
gobject.threads_init()

import gst

if gst.pygst_version < (0, 10, 9):
    # pygst before 0.10.9 has atexit(gst_deinit), causing segfaults.  Let's
    # replace sys.exit with something that overrides atexit processing:
    def exi(status=0):
        os._exit(status)
    sys.exit = exi

class GStreamerTestBase(PythonDBusTest):
    """
    Tests that specifically run a GStreamer pipeline
    """
    __test_name__ = """gstreamer-test-base"""
    __test_description__ = """Base class for GStreamer tests"""
    __test_checklist__ = {
        "valid-pipeline" : "The test pipeline was properly created",
        "pipeline-change-state" : "The initial state_change happened succesfully",
        "reached-initial-state" : "The pipeline reached the initial GstElementState",
        "no-errors-seen" : "No errors were emitted from the pipeline"
        }

    __test_extra_infos__ = {
        "errors" : "List of errors emitted by the pipeline",
        "tags" : "List of tags emitted by the pipeline",
        "elements-used" : "List of elements used as (name,factoryname,parentname)"
        }
    # Initial pipeline state, subclasses can override this
    __pipeline_initial_state__ = gst.STATE_PLAYING

    def __init__(self, env=None, *args, **kwargs):
        # We don't want the tests to update the registry because:
        # * it will make the tests start up faster
        # * the tests accros testrun should be using the same registry/plugins
        #
        # This feature is only available since 0.10.19.1 (24th April 2008) in
        # GStreamer core
        if env:
            env["GST_REGISTRY_UPDATE"] = "no"
        self.pipeline = None
        self.bus = None
        self._errors = []
        self._tags = {}
        self._elements = []
        self._reachedInitialState = False
        self._waitcb = None
        PythonDBusTest.__init__(self, env=env, *args, **kwargs)

    def setUp(self):
        # default gst debug output to NOTHING
        self._environ["GST_DEBUG"] = "0"
        return PythonDBusTest.setUp(self)

    def remoteSetUp(self):
        debug("%s", self.uuid)
        gst.log("%s" % self.uuid)
        # local variables

        # create the pipeline
        try:
            self.pipeline = self.createPipeline()
        except:
            exception("Error while creating pipeline")
            self.pipeline = None
        finally:
            self.validateStep("valid-pipeline", not self.pipeline == None)
            if self.pipeline == None:
                self.remoteStop()
                return

        self._elements = [(self.pipeline.get_name(),
                           self.pipeline.get_factory().get_name(),
                           "")] #name,factoryname,parentname
        self._watchContainer(self.pipeline)

        # connect to bus
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._busMessageHandlerCb)
        PythonDBusTest.remoteSetUp(self)

    def remoteTearDown(self):
        if not PythonDBusTest.remoteTearDown(self):
            return False
        gst.log("Tearing Down")
        # unref pipeline and so forth
        if self._waitcb:
            gobject.source_remove(self._waitcb)
            self._waitcb = None
        if self.pipeline:
            self.pipeline.set_state(gst.STATE_NULL)
        self.validateStep("no-errors-seen", self._errors == [])
        if not self._errors == []:
            self.extraInfo("errors", self._errors)

        if not self._tags == {}:
            debug("Got tags %r", self._tags)
            for key, val in self._tags.iteritems():
                if isinstance(val, int):
                    # make sure that only values < 2**31 (MAX_INT32) are ints
                    # TODO : this is gonna screw up MASSIVELY with values > 2**63
                    if val >= 2**31:
                        self._tags[key] = long(val)
            # FIXME : if the value is a list, the dbus python bindings screw up
            #
            # For the time being we remove the values of type list, but this is REALLY
            # bad.
            listval = [x for x in self._tags.keys() if type(self._tags[x]) == list]
            if listval:
                warning("Removing this from the taglist since they're list:%r", listval)
                for val in listval:
                    del self._tags[val]
            self.extraInfo("tags", dbus.Dictionary(self._tags, signature="sv"))
        if not self._elements == []:
            self.extraInfo("elements-used", self._elements)
        return True

    def remoteTest(self):
        # kickstart pipeline to initial state
        PythonDBusTest.remoteTest(self)
        debug("Setting pipeline to initial state %r", self.__pipeline_initial_state__)
        gst.log("Setting pipeline to initial state %r" % self.__pipeline_initial_state__)
        res = self.pipeline.set_state(self.__pipeline_initial_state__)
        debug("set_state returned %r", res)
        gst.log("set_state() returned %r" % res)
        self.validateStep("pipeline-change-state", not res == gst.STATE_CHANGE_FAILURE)
        if res == gst.STATE_CHANGE_FAILURE:
            warning("Setting pipeline to initial state failed, stopping test")
            gst.warning("State change failed, stopping")
            self.stop()

    def _busMessageHandlerCb(self, bus, message):
        debug("%s from %r message:%r", self.uuid, message.src, message)
        gst.log("%s from %r message:%r" % (self.uuid, message.src, message))
        # let's pass it on to subclass to see if they want us to ignore that message
        if self.handleBusMessage(message) == False:
            debug("ignoring message")
            return
        # handle common types
        if message.type == gst.MESSAGE_ERROR:
            gerror, dbg = message.parse_error()
            self._errors.append((gerror.code, gerror.domain, gerror.message, dbg))
            debug("Got an error on the bus, stopping")
            self.stop()
        elif message.type == gst.MESSAGE_TAG:
            self._gotTags(message.parse_tag())
        elif message.src == self.pipeline:
            if message.type == gst.MESSAGE_EOS:
                # it's not 100% sure we want to stop here, because of the
                # race between the final state-change message and the eos message
                # arriving on the bus.
                debug("Saw EOS, stopping")
                if self._reachedInitialState:
                    self.stop()
                else:
                    self._waitcb = gobject.timeout_add(1000, self._waitForInitialState)
            elif message.type == gst.MESSAGE_STATE_CHANGED:
                prev, cur, pending = message.parse_state_changed()
                if cur == self.__pipeline_initial_state__ and pending == gst.STATE_VOID_PENDING:
                    gst.log("Reached initial state")
                    self.validateStep("reached-initial-state")
                    self._reachedInitialState = True
                    if self.pipelineReachedInitialState():
                        debug("Stopping test because we reached initial state")
                        gst.log("Stopping test because we reached initial state")
                        self.stop()

    def _waitForInitialState(self):
        debug("We were waiting for the initial state... in vain")
        self.stop()

    def _gotTags(self, tags):
        for key in tags.keys():
            value = tags[key]
            if isinstance(value, gobject.GBoxed):
                value = repr(value)
            elif isinstance(value, gst.MiniObject):
                value = repr(value)
            self._tags[key] = value

    def _watchContainer(self, container):
        # add all elements currently preset
        for elt in container:
            self._elements.append((elt.get_name(),
                                   elt.get_factory().get_name(),
                                   container.get_name()))
            if isinstance(elt, gst.Bin):
                self._watchContainer(elt)
        container.connect("element-added", self._elementAddedCb)
        # connect to signal

    def _elementAddedCb(self, container, element):
        debug("New element %r in container %r", element, container)
        factory = element.get_factory()
        factory_name = ""
        if not factory is None:
            factory_name = factory.get_name()
        # add himself
        self._elements.append((element.get_name(),
                               factory_name,
                               container.get_name()))
        # if bin, add current and connect signal
        if isinstance(element, gst.Bin):
            self._watchContainer(element)

    def stop(self):
        gst.log("Stopping...")
        PythonDBusTest.stop(self)

    ## Methods that can be overridden by subclasses

    def pipelineReachedInitialState(self):
        """
        Override this method to implement some behaviour once your pipeline
        has reached the initial state.

        Return True if you want the test to stop (default behaviour).
        Return False if you want the test to carry on (most likely because you
        wish to do other actions/testing).
        """
        return True

    def handleBusMessage(self, message):
        """
        Override this method if you want to be able to handle messages from the
        bus.

        Return False if you don't want the base class to handle it (because you
        have been handling the Error messages or EOS messages and you don't
        want the base class to do the default handling.
        Else return True.
        """
        return True

    def getPipelineString(self):
        """
        Return the pipeline string for the given test.
        This method should be implemented in tests that don't create the
        pipeline manually, but instead can just return a parse-launch syntax
        string representation of the pipeline.
        """
        raise NotImplementedError

    def createPipeline(self):
        """
        Construct and return the pipeline for the given test

        Return a gst.Pipeline if creation was successful.
        Return None if an error occured.
        """
        # default implementation : ask for parse-launch syntax
        pipestring = self.getPipelineString()
        debug("%s Got pipeline string %s", self.uuid, pipestring)
        try:
            pip = gst.parse_launch(pipestring)
        except:
            exception("error while creating pipeline")
            pip = None
        return pip
