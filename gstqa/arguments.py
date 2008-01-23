# GStreamer QA system
#
#       arguments.py
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

"""
from log import critical, error, warning, debug, info
from generator import Generator

class Arguments:
    # Need some iterable interface !
    # to return a dictionnary of argument at each iteration

    def __init__(self, *args, **kwargs):
        self.args = kwargs
        # split out static args from generators
        # generators : (generator, curidx, length)
        self.generators = {}
        self.statics = {}
        for key, value in self.args.iteritems():
            info("key:%s, type:%r" % (key, value))
            if isinstance(value, Generator):
                self.generators[key] = [value, 0, 0]
            else:
                self.statics[key] = value
        self.genlist = self.generators.keys()
        self._initialized = False
        self.combinations = 1
        self.globalidx = 0

    ## Iterable interface
    def __iter__(self):
        # return a copy
        return Arguments(**self.args)

    def next(self):
        if not self._initialized:
            self._initialize()
        if not self.globalidx < self.combinations:
            raise StopIteration
        # return the next dict of arguments
        # contains a copy of all static arguments
        # plus the next combination of generators
        res = self.statics.copy()
        if self.generators:
            info("we have generators")
            # extend with current generator values
            for key in self.genlist:
                info("key")
                gen, idx, length = self.generators[key]
                res[key] = gen[idx]
            # update values
            self.updateGeneratorsPosition()
        # update global idx
        self.globalidx += 1
        return res

    def updateGeneratorsPosition(self):
        for key in self.genlist:
            gen, idx, length = self.generators[key]
            # update the position of this generator
            self.generators[key][1] = (self.generators[key][1] + 1) % self.generators[key][2]
            # if we didn't go over, break, else continue to update next one
            if self.generators[key][1]:
                break

    def _initialize(self):
        # figure out the length of all generators
        debug("initializing")
        cpy = {}
        for key, value in self.generators.iteritems():
            gen, idx, nb = value
            nb = len(gen)
            if nb:
                self.combinations *= nb
            cpy[key] = [gen, idx, nb]
        debug("self.combinations: %d" % self.combinations)
        self.generators = cpy
        self._initialized = True

    ## EXTRA METHODS
    ## NOT IMPLEMENTED YET

    def isValidWithTest(self, testclass):
        """ Checks if all arguments are valid with given test """
        raise NotImplementedError
