#!/usr/bin/env python
#
# Copyright (c) 2008 Nokia Corporation
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
#
# Authors: Rene Stadler <rene.stadler@nokia.com>
#

import sys
import os
import os.path
import time

import pygtk
pygtk.require("2.0")
del pygtk

import gobject
import gtk

import insanity
import insanity.utils

from insanity.client import TesterClient
from insanity.scenario import Scenario
from insanity.testrun import TestRun
from tests.scenarios.gstmediatest import GstMediaTestScenario

class GtkTesterClient(TesterClient):

    __software_name__ = "GTK client"

    def __init__(self, runner):

        TesterClient.__init__(self, singlerun = True)

        self.runner = runner

    def test_run_start(self, testrun):

        testrun.connect("single-test-start", self.handle_single_test_start)
        testrun.connect("single-test-done", self.handle_single_test_done)

    def handle_single_test_start(self, testrun, test):

        self.runner.handle_test_started(test)
        test.connect("check", self.handle_test_check)

    def handle_single_test_done(self, testrun, test):

        self.runner.handle_test_complete(test)

    def handle_test_check(self, test, checkitem, validated):

        self.runner.handle_test_check(test, checkitem, validated)

class GtkTestRunner(object):

    def __init__(self, window):

        self.window = window

        self.client = GtkTesterClient(self)
        self.run = None

        self.scenario_class = None
        self.test_class = None
        self.path = None

    def get_test_names(self):

        return [t[0] for t in insanity.utils.list_available_tests()]

    def get_scenario_names(self):

        return [s[0] for s in insanity.utils.list_available_scenarios()]

    def set_scenario(self, scenario_name):

        self.scenario_class = insanity.utils.get_test_class(scenario_name)

    def set_test(self, test_name):

        self.test_class = insanity.utils.get_test_class(test_name)

    def set_folder(self, path):

        self.path = path

    def get_generator(self):

        assert self.path

        from insanity.generators.filesystem import URIFileSystemGenerator

        return URIFileSystemGenerator(paths=[self.path], recursive=True)

    def get_n_files(self):

        generator = self.get_generator()
        return len(generator.generate())

    def start(self):

        assert not self.run
        assert self.scenario_class or self.test_class

        self.run = TestRun(maxnbtests = 1)

        if not self.scenario_class:
            generator = self.get_generator()
            self.run.addTest(self.test_class,
                             arguments = {"uri" : generator})
        else:
            self.run.addTest(self.scenario_class,
                             arguments = {})

        self.client.addTestRun(self.run)
        self.client.run()

    def stop(self):

        self.run = None
        self.client.quit()

    def handle_test_started(self, test):

        self.window.handle_test_started(test)

    def handle_test_check(self, test, checkitem, validated):

        self.window.handle_test_check(test, checkitem, validated)

    def handle_test_complete(self, test):

        self.window.handle_test_complete(test)

class TestStatusWidget(gtk.Frame):

    def __init__(self):

        gtk.Frame.__init__(self)

        self.labels = {}
        self.box = gtk.HBox(True, 2)
        self.add(self.box)

        self.box.show()

    @staticmethod
    def _check_shortname(n):
        parts = n.split("-")
        return "".join([p[:1] for p in parts]).upper()

    def set_checklist(self, checks):

        for label in self.labels.itervalues():
            label.destroy()
        self.labels.clear()

        for check in checks.keys():
            label_text = self._check_shortname(check)
            label = gtk.Label()
            label.props.use_markup = True
            label.props.label = label_text # FIXME escape
            self.labels[check] = label
            self.box.pack_start(label)
            label.show()

    def reset_status(self):

        for check, label in self.labels.iteritems():
            label_text = self._check_shortname(check)
            label.props.label = label_text # FIXME: escape

    def update_status(self, check, status):

        label = self.labels[check]
        if status:
            color = "green"
        else:
            color = "red"

        label_text = self._check_shortname(check)
        label.props.label = "<span background='%s'>%s</span>" % (color, label_text,) # FIXME: escape

class Window(object):

    def __init__ (self):

        self.started = False
        self.update_id = None
        self.runner = GtkTestRunner(self)

        insanity.utils.scan_for_tests()
        tests = self.runner.get_test_names()
        scenarios = self.runner.get_scenario_names()

        self.gtk_window = gtk.Window()
        self.gtk_window.connect("delete-event", self.handle_gtk_window_delete_event)
        self.gtk_window.props.title = "Insanity"
        self.gtk_window.show()

        window_box = gtk.VBox()
        window_box.props.border_width = 6

        table = gtk.Table(7, 4, False)
        size_group1 = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        size_group2 = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        label = gtk.Label("Scenario:")
        label.props.xalign = 0.
        size_group1.add_widget(label)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, (), 0, 0)

        combo = gtk.combo_box_new_text()
        combo.append_text("(no scenario)")
        for scenario in scenarios:
            combo.append_text(scenario)
        size_group2.add_widget(combo)
        combo.set_active(0)
        table.attach(combo, 1, 2, 0, 1, gtk.FILL, (), 3, 0)
        self.scenario_combo = combo

        label = gtk.Label("Test:")
        label.props.xalign = 0.
        size_group1.add_widget(label)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, (), 0, 0)

        combo = gtk.combo_box_new_text()
        for test in tests:
            combo.append_text(test)
        size_group2.add_widget(combo)
        combo.set_active(0)
        table.attach(combo, 1, 2, 1, 2, gtk.FILL, (), 3, 0)
        self.test_combo = combo

        label = gtk.Label("Folder:")
        label.props.xalign = 0.
        size_group1.add_widget(label)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, (), 0, 0)

        button = gtk.FileChooserButton("Select directory")
        button.props.action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER
        size_group2.add_widget(button)
        table.attach(button, 1, 2, 2, 3, (), gtk.FILL, 3, 0)
        self.folder_chooser = button

        button = gtk.Button("Start testrun")
        button.connect("clicked", self.handle_start_testrun_button_clicked)
        table.attach(button, 2, 3, 2, 3, (), gtk.FILL, 3, 0)
        self.start_testrun_button = button

        label = gtk.Label("Run time:")
        label.props.xalign = 0.
        size_group1.add_widget(label)
        table.attach(label, 0, 1, 3, 4, gtk.FILL, (), 0, 0)

        label = gtk.Label("")
        label.props.xalign = 0.
        size_group1.add_widget(label)
        table.attach(label, 1, 2, 3, 4, gtk.FILL, (), 3, 0)
        self.run_time_label = label

        label = gtk.Label("Progress:")
        label.props.xalign = 0.
        size_group1.add_widget(label)
        table.attach(label, 0, 1, 4, 5, gtk.FILL, (), 0, 0)

        progress = gtk.ProgressBar()
        table.attach(progress, 1, 2, 4, 5, gtk.FILL, (), 3, 0)
        self.progress = progress

        label = gtk.Label("")
        label.props.xalign = 0.
        #table.attach(label, 0, 4, 5, 6, gtk.FILL, (), 3, 3)
        window_box.pack_end(label)
        self.current_uri_label = label

        progress = gtk.ProgressBar()
        window_box.pack_end(progress)
        self.test_progress = progress

        status = TestStatusWidget()
        window_box.pack_end(status)
        self.test_status = status

        window_box.pack_start(table, True, True, 0)
        self.gtk_window.add(window_box)
        self.gtk_window.show_all()

        self.size_groups = [size_group1, size_group2]

    def handle_gtk_window_delete_event(self, gtk_window, event):

        self.stop_test()

        gtk.main_quit()

    def handle_start_testrun_button_clicked(self, button):

        if self.started:
            self.stop_test()
        else:
            self.start_test()

    def start_test(self):

        self.started = True
        self.start_testrun_button.props.label = "Stop test"

        if not os.access(os.getcwd(), os.W_OK):
            print >> sys.stderr, "insanity-gtk: Current directory %s not writable, changing to ~" % (os.getcwd(),)
            os.chdir(os.path.expanduser("~"))

        scenario = self.scenario_combo.get_active_text()
        if scenario != "(no scenario)":
            self.runner.set_scenario(scenario)

        test = self.test_combo.get_active_text()
        self.runner.set_test(test)
        test_class = self.runner.test_class
        self.test_status.set_checklist(test_class.getFullCheckList())

        folder = self.folder_chooser.get_filename()
        self.runner.set_folder(folder)

        self.start_time = time.time()
        self.n_files = self.runner.get_n_files()
        self.n_completed = 0

        def update():
            self.update_run_time()
            return True
        self.update_id = gobject.timeout_add(1000, update)

        self.runner.start()

    def stop_test(self):

        if not self.started:
            return

        if self.update_id is not None:
            gobject.source_remove(self.update_id)
            self.update_id = None

        self.started = False
        self.start_testrun_button.props.label = "Start test"

        self.runner.stop()

    def update_run_time(self):

        def time_args (secs):
            return "%02i:%02i:%02i" % (secs // 60**2,
                                       secs // 60 % 60,
                                       secs % 60,)

        run_time = time.time() - self.start_time
        self.run_time_label.props.label = time_args(run_time)

    def handle_test_started(self, test):

        uri = test.arguments.get("uri")

        if uri:
            text = uri
        else:
            text = ""

        self.current_uri_label.props.label = text

    def handle_test_check(self, test, checkitem, validated):

        ## self.current_check.props.label = checkitem
        self.test_progress.props.fraction = test.getSuccessPercentage() / 100.
        if validated:
            status_text = "validated"
        else:
            status_text = "failed"
        self.test_progress.props.text = "%s %s" % (checkitem, status_text,)
        self.test_status.update_status(checkitem, validated)

    def handle_test_complete(self, test):

        self.n_completed += 1

        self.progress.props.fraction = float(self.n_completed) / float(self.n_files)
        self.test_status.reset_status()

def main():

    w = Window()
    gtk.main()

if __name__ == "__main__":
    main()
