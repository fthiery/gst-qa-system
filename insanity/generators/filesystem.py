# GStreamer QA system
#
#       generators/filesystem.py
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

"""
File system related generators
"""

import os.path
from fnmatch import fnmatch

from insanity.generator import Generator
from insanity.log import debug, info

class FileSystemGenerator(Generator):
    """
    Arguments:
    * list of paths/files
    * recursive option (default : True)
    * matching option (default : [])
    * reject option (default : [])

    Returns:
    * file system path
    """

    __args__ = {
        "paths":"List of paths or files",
        "recursive":"If True, go down in subdirectories (default:True)",
        "matching":"List of masks for files to be taken into account",
        "reject":"List of masks for files to NOT be taken into account"
        }

    __produces__ = "paths"

    def __init__(self, paths=[], recursive=True,
                 matching=[], reject=[], *args,
                 **kwargs):
        """
        paths : list of paths and/or files
        recursive : go down in subdirectories
        matching : will only return files matching the given masks
        reject : will not return files matching the given masks
        """
        Generator.__init__(self, paths=paths, recursive=recursive,
                           matching=matching, reject=reject,
                           *args, **kwargs)
        self.paths = paths
        self.recursive = recursive
        self.matching = matching
        self.reject = reject
        info("paths:%r, recursive:%r, matching:%r, reject:%r" % (paths, recursive, matching, reject))

    def _is_valid_file(self, filename):
        """ returns True if the given filename is valid """
        if self.matching:
            # try against the positive matches
            for match in self.matching:
                if fnmatch(filename, match):
                    return True
            return False

        if self.reject:
            # try against the negative matches
            for match in self.reject:
                if fnmatch(filename, match):
                    return False
        # if there's no matching exceptions, it's valid
        return True

    def _get_files(self, directory):
        res = []
        for dirpath, dirnames, filenames in os.walk(directory):
            res.extend([os.path.join(dirpath, fn) for fn in filenames if self._is_valid_file(fn)])
            if not self.recursive:
                break
        res.sort()
        return res

    def _generate(self):
        res = []
        for path in self.paths:
            fullpath = os.path.abspath(path)
            if os.path.isfile(fullpath) and self._is_valid_file(fullpath):
                res.append(fullpath)
            else:
                res.extend(self._get_files(fullpath))
        info("Returning %d files" % len(res))
        return res

class URIFileSystemGenerator(FileSystemGenerator):
    """
    Same as FileSystemGenerator, excepts that it returns URIs instead
    of file system paths.
    """

    __produces__ = "URI"

    def _generate(self):
        return ["file://%s" % x for x in FileSystemGenerator._generate(self)]

