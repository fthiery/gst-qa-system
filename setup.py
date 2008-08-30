#!/usr/bin/python

import sys
import os
import os.path

import distutils.cmd
from distutils.core import setup
from distutils.command.clean import clean
from distutils.command.build import build
from distutils.command.sdist import sdist
from distutils.command.install_scripts import install_scripts
from distutils.errors import *

class clean_custom (clean):

    def remove_file (self, path):

        if os.path.exists (path):
            print "removing '%s'" % (path,)
            if not self.dry_run:
                os.unlink (path)

    def remove_directory (self, path):

        from distutils import dir_util

        if os.path.exists (path):
            dir_util.remove_tree (path, dry_run = self.dry_run)

    def run (self):

        clean.run (self)

        if os.path.exists ("MANIFEST.in"):
            # MANIFEST is generated, get rid of it.
            self.remove_file ("MANIFEST")

        self.remove_directory ("build")
        self.remove_directory ("dist")

        for path, dirs, files in os.walk ("."):
            for filename in files:
                if filename.endswith (".pyc") or filename.endswith (".pyo"):
                    file_path = os.path.join (path, filename)
                    self.remove_file (file_path)

class distcheck (sdist):

    # Originally based on code from telepathy-python.

    description = "verify self-containedness of source distribution"

    def run (self):

        from distutils import dir_util
        from distutils.spawn import spawn

        # This creates e.g. dist/package-0.1.tar.gz
        sdist.run (self)

        base_dir = self.distribution.get_fullname ()
        distcheck_dir = os.path.join (self.dist_dir, "distcheck")
        self.mkpath (distcheck_dir)
        self.mkpath (os.path.join (distcheck_dir, "again"))

        cwd = os.getcwd ()
        os.chdir (distcheck_dir)

        if os.path.isdir (base_dir):
            dir_util.remove_tree (base_dir)

        # Unpack tarball into dist/distcheck, creating
        # e.g. dist/distcheck/package-0.1
        for archive in self.archive_files:
            if archive.endswith (".tar.gz"):
                archive_rel = os.path.join (os.pardir, os.pardir, archive)
                spawn (["tar", "-xzf", archive_rel, base_dir])
                break
        else:
            raise ValueError ("no supported archives were created")

        os.chdir (cwd)
        os.chdir (os.path.join (distcheck_dir, base_dir))
        spawn ([sys.executable, "setup.py", "sdist", "--formats", "gztar"])

        # Unpack tarball into dist/distcheck/again.
        os.chdir (cwd)
        os.chdir (os.path.join (distcheck_dir, "again"))
        archive_rel = os.path.join (os.pardir, base_dir, "dist", "%s.tar.gz" % (base_dir,))
        spawn (["tar", "-xzf", archive_rel, base_dir])

        os.chdir (cwd)
        os.chdir (os.path.join (distcheck_dir, base_dir))
        spawn ([sys.executable, "setup.py", "clean"])

        os.chdir (cwd)
        spawn (["diff", "-ru",
                os.path.join (distcheck_dir, base_dir),
                os.path.join (distcheck_dir, "again", base_dir)])

        if not self.keep_temp:
            dir_util.remove_tree (distcheck_dir)

cmdclass = {"clean" : clean_custom,
            "distcheck" : distcheck}

setup (cmdclass = cmdclass,
       packages = ["insanity",
                   "insanity.generators",
                   "insanity.storage",
                   "tests",
                   "tests.scenarios"],
       scripts = ["bin/compare.py",
                  "bin/dumpresults.py",
                  "bin/grouper.py",
                  "bin/gst-media-test",
                  "bin/pythondbusrunner.py"],
       data_files = [("share/insanity", ["bin/gdb.instructions",
                                         "bin/gst.supp"],)],
       name = "insanity",
       version = "0.0",
       description = "",
       long_description = """\
""",
       license = "GNU GPL",
       author = "Edward Hervey",
       author_email = "bilboed@bilboed.com",
       url = "http://git.collabora.co.uk/?p=user/edward/gst-qa-system;a=summary")
