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
import ConfigParser

import pygtk
pygtk.require("2.0")
del pygtk

import gobject
import gtk

import insanity
import insanity.utils

from insanity.client import TesterClient
from insanity.testrun import TestRun

class GtkTesterClient(TesterClient):

    __software_name__ = "GTK client"

    def __init__(self, runner):

        TesterClient.__init__(self, singlerun = True)

        self.runner = runner

    def test_run_start(self, testrun):

        testrun.connect("single-test-start", self.handle_single_test_start)
        testrun.connect("single-test-done", self.handle_single_test_done)

    def test_run_done(self, testrun):

        self.runner.handle_testrun_done(testrun)

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

        self.test_class = None
        self.test_arguments = {}

    def get_test_names(self):

        return [t[0] for t in insanity.utils.list_available_tests()]

    def get_scenario_names(self):

        return [s[0] for s in insanity.utils.list_available_scenarios()]

    def set_test(self, test_name):

        self.test_class = insanity.utils.get_test_class(test_name)

    def set_arguments(self, test_args):

        self.test_arguments = test_args.copy()

    def set_folder(self, path):

        self.path = path

    def get_n_tests(self):

        n = 1
        test_args = self.test_arguments
        for arg_name, generator in test_args.iteritems():
             n *= len(generator.generate())

        return n

    def setup_test_run(self):

        run = TestRun(maxnbtests = 1)

        run.addTest(self.test_class, arguments = self.test_arguments)

        return run

    def start(self):

        assert not self.run
        assert self.test_class

        self.run = self.setup_test_run()
        self.client.addTestRun(self.run)
        self.client.run()

    def stop(self):

        self.run = None
        self.client.quit()

    def handle_testrun_done(self, testrun):

        self.stop()
        self.window.handle_testrun_done(testrun)

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

class StateValue(object):

    """Descriptor for binding to the State class."""

    def __init__(self, name, default = None):

        self.name = name
        self.default = default

    def __get__(self, state, state_class = None):

        if state is None:
            return self

        try:
            return state.parser.get("state", self.name)
        except ConfigParser.NoOptionError:
            return self.default

    def __set__(self, state, value):

        state.parser.set("state", self.name, value)

class State(object):

    test_name = StateValue("test-name")
    uri_gen = StateValue("uri-generator", "folder")
    uri_folder = StateValue("uri-folder")
    uri_file = StateValue("uri-file")
    uri_playlist = StateValue("uri-playlist")

    @classmethod
    def get_filename(cls):

        return os.path.expanduser("~/.config/insanity-gtk")

    def __init__(self):

        self.parser = ConfigParser.RawConfigParser()

        self.parser.read([self.get_filename()])

        try:
            self.parser.add_section("state")
        except ConfigParser.DuplicateSectionError:
            pass

    def save(self):

        tmpname = "%s.tmp" % (self.get_filename(),)

        dirname = os.path.dirname(tmpname)
        try:
            os.makedirs(dirname)
        except OSError:
            pass

        fp = None
        try:
            fp = file(tmpname, "wt")
            self.parser.write(fp)
        finally:
            if fp:
                fp.close()
                os.rename(tmpname, self.get_filename())

class Window(object):

    def __init__ (self):

        self.state = State()

        self.started = False
        self.update_id = None
        self.runner = GtkTestRunner(self)

        insanity.utils.scan_for_tests()
        tests = self.runner.get_test_names() + self.runner.get_scenario_names()

        self.gtk_window = gtk.Window()
        self.gtk_window.connect("delete-event", self.handle_gtk_window_delete_event)
        self.gtk_window.props.title = "Insanity"
        self.gtk_window.show()

        self.uri_generator_widgets = {}
        self.uri_generator_all_widgets = []

        window_box = gtk.VBox()
        window_box.props.border_width = 6

        table = gtk.Table(7, 4, False)
        size_group1 = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        size_group2 = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        label = gtk.Label("Test:")
        label.props.xalign = 0.
        size_group1.add_widget(label)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, (), 0, 0)

        combo = gtk.combo_box_new_text()
        for test in tests:
            combo.append_text(test)
        size_group2.add_widget(combo)
        combo.connect("changed", self.handle_test_combo_changed)
        table.attach(combo, 1, 2, 1, 2, gtk.FILL, (), 3, 0)
        self.test_combo = combo

        label = gtk.Label("URI:")
        label.props.xalign = 0.
        size_group1.add_widget(label)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, (), 0, 0)
        self.uri_generator_all_widgets.append(label)

        hbox = gtk.HBox()

        combo = gtk.combo_box_new_text()
        combo.append_text("Folder")
        combo.append_text("File")
        combo.append_text("Playlist")
        hbox.pack_start(combo, False, False)
        self.uri_generator_combo = combo
        self.uri_generator_all_widgets.append(combo)

        notebook = gtk.Notebook()
        notebook.props.show_tabs = False
        notebook.props.show_border = False
        hbox.pack_start(notebook, True, True)
        self.uri_generator_notebook = notebook

        button = gtk.FileChooserButton("Select directory")
        button.props.action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER
        button.connect("current-folder-changed", self.handle_uri_folder_button_changed)
        self.uri_generator_widgets["Folder"] = button
        self.uri_generator_all_widgets.append(button)
        notebook.append_page(button, None)
        if self.state.uri_folder:
            button.set_current_folder_uri(self.state.uri_folder)

        button = gtk.FileChooserButton("Select file")
        button.props.action = gtk.FILE_CHOOSER_ACTION_OPEN
        button.connect("current-folder-changed", self.handle_uri_file_button_changed)
        self.uri_generator_widgets["File"] = button
        self.uri_generator_all_widgets.append(button)
        notebook.append_page(button, None)
        if self.state.uri_file:
            button.set_uri(self.state.uri_file)

        button = gtk.FileChooserButton("Select playlist")
        button.props.action = gtk.FILE_CHOOSER_ACTION_OPEN
        button.connect("current-folder-changed", self.handle_uri_playlist_button_changed)
        self.uri_generator_widgets["Playlist"] = button
        self.uri_generator_all_widgets.append(button)
        notebook.append_page(button, None)
        if self.state.uri_playlist:
            button.set_uri(self.state.uri_playlist)

        size_group2.add_widget(hbox)
        table.attach(hbox, 1, 2, 2, 3, (), gtk.FILL, 3, 0)
        combo.connect("changed", self.handle_uri_generator_combo_changed)

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

        default_test_name = self.state.test_name
        if default_test_name in tests:
            self.test_combo.props.active = tests.index(default_test_name)
        else:
            self.test_combo.props.active = 0

        default_uri_gen = self.state.uri_gen
        uri_gen_list = ["folder", "file", "playlist"]
        if not default_uri_gen in uri_gen_list:
            combo.set_active(0)
        else:
            combo.set_active(uri_gen_list.index(default_uri_gen))

    def handle_gtk_window_delete_event(self, gtk_window, event):

        self.stop_test()

        gtk.main_quit()

    def handle_start_testrun_button_clicked(self, button):

        if self.started:
            self.stop_test()
        else:
            self.start_test()

    def handle_test_combo_changed(self, combo):

        test = self.test_combo.get_active_text()
        self.runner.set_test(test)
        test_class = self.runner.test_class
        self.test_status.set_checklist(test_class.getFullCheckList())

        test_args = test_class.getFullArgumentList()
        if "uri" in test_args:
            uri_arg = True
        else:
            uri_arg = False
        for widget in self.uri_generator_all_widgets:
            widget.props.sensitive = uri_arg

        self.state.test_name = test
        self.state.save()

    def handle_uri_generator_combo_changed(self, combo):

        notebook = self.uri_generator_notebook

        text = combo.get_active_text()
        widget = self.uri_generator_widgets[text]
        page_num = notebook.page_num(widget)
        notebook.props.page = page_num

        self.state.uri_gen = text.lower()
        self.state.save()

    def handle_uri_folder_button_changed(self, chooser_button):

        uri = chooser_button.get_current_folder_uri()
        if uri:
            self.state.uri_folder = uri
            self.state.save()

    def handle_uri_file_button_changed(self, chooser_button):

        uri = chooser_button.get_uri()
        if uri:
            self.state.uri_file = uri
            self.state.save()

    def handle_uri_playlist_button_changed(self, chooser_button):

        uri = chooser_button.get_uri()
        if uri:
            self.state.uri_playlist = uri
            self.state.save()

    def build_test_arguments(self):

        test_args = {}

        if self.uri_generator_combo.props.sensitive:
            uri_gen = self.uri_generator_combo.get_active_text()
            uri_widget = self.uri_generator_widgets[uri_gen]
            if uri_gen == "Folder":
                from insanity.generators.filesystem import URIFileSystemGenerator
                folder = uri_widget.get_filename()
                test_args["uri"] = URIFileSystemGenerator(paths=[folder], recursive=True)
            elif uri_gen == "File":
                from insanity.generators.filesystem import URIFileSystemGenerator
                filename = uri_widget.get_filename()
                test_args["uri"] = URIFileSystemGenerator(paths=[filename], recursive=False)
            elif uri_gen == "Playlist":
                from insanity.generators.playlist import PlaylistGenerator
                filename = uri_widget.get_filename()
                test_args["uri"] = PlaylistGenerator(location=filename)
            else:
                assert False

        return test_args

    def start_test(self):

        self.started = True
        self.start_testrun_button.props.label = "Stop test"

        if not os.access(os.getcwd(), os.W_OK):
            print >> sys.stderr, "insanity-gtk: Current directory %s not writable, changing to ~" % (os.getcwd(),)
            os.chdir(os.path.expanduser("~"))

        test_args = self.build_test_arguments()
        self.runner.set_arguments(test_args)

        self.start_time = time.time()
        self.n_tests = self.runner.get_n_tests()
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

        self.progress.props.fraction = float(self.n_completed) / float(self.n_tests)
        self.test_status.reset_status()

    def handle_testrun_done(self, testrun):

        self.stop_test()

def main():

    w = Window()
    gtk.main()

if __name__ == "__main__":
    main()
