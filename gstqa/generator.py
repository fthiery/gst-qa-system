# GStreamer QA system
#
#       generator.py
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

# TODO
#  introspection
#  python iterator-interface ?
#
# We should be able to do something like:
# * chaining generators output
#   i.e. pass the output of FileSystemGenerator to PlaylistGenerator

import os.path
from fnmatch import fnmatch
from log import critical, error, warning, debug, info

class Generator:
    """
    Expands some arguments into a list of arguments
    """

    __args__ = {}

    def __init__(self, *args, **kwargs):
        """Subclasses should call their parent __init__ will ALL arguments"""
        self.args = args
        self.kwargs = kwargs
        self.generated = []

    def copy(self):
        return self.__class__(*self.args, **self.kwargs)

    def generate(self):
        """ Returns the full list of results """
        if not self.generated:
            self.generated = self._generate()
        return self.generated

    def _generate(self):
        """
        Return the full list of results
        to be implemented by subclasses
        """
        raise NotImplementedError

    def __iter__(self):
        return self.generate()[:]

    def __len__(self):
        return len(self.generate())

    def __getitem__(self, idx):
        return self.generate()[idx]

class PlaylistGenerator(Generator):
    """
    Takes a list of playlist file location
    Returns a full list of URIs contained in those files
    """
    pass

class FileSystemGenerator(Generator):
    """
    Arguments:
    * list of paths/files
    * recursive option (default : True)
    * matching option (default : [])
    * reject option (default : [])

    Returns:
    * URI
    """

    def __init__(self, paths=[], recursive=True,
                 matching=[], reject=[], *args,
                 **kwargs):
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
        for p in self.paths:
            fullpath = os.path.abspath(p)
            if os.path.isfile(fullpath) and self._is_valid_file(fullpath):
                res.append(fullpath)
            else:
                res.extend(self._get_files(fullpath))
        info("Returning %d files" % len(res))
        return res

class URIFileSystemGenerator(FileSystemGenerator):

    def _generate(self):
        return ["file://%s" % x for x in FileSystemGenerator._generate(self)]

class CapsGenerator(Generator):
    """
    """
    pass
