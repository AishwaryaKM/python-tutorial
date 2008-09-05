
# Copyright (C) 2008 Mark Seaborn
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA.

import compiler
import os
import types

import pycheck
import varbindings


class VerifyError(Exception):

    pass


def safe_eval(source_code, builtins):
    # The Reference Manual for Python 2.5 says:
    # "As a side effect, an implementation may insert additional keys
    # into the dictionaries given besides those corresponding to
    # variable names set by the executed code. For example, the
    # current implementation may add a reference to the dictionary of
    # the built-in module __builtin__ under the key __builtins__ (!)."
    # - http://docs.python.org/ref/exec.html
    # This means we cannot let the caller provide its own environment
    # dictionary, because it might leave the __builtins__ slot empty
    # and Python would fill it out with the default, giving the caller
    # access to all the real builtins.
    assert type(source_code) is str
    module = types.ModuleType("__safe_eval_module__")
    module.__dict__["__builtins__"] = builtins
    tree = compiler.parse(source_code)
    varbindings.annotate(tree)
    log = pycheck.check(tree)
    if len(log) > 0:
        raise VerifyError(log)
    exec source_code in module.__dict__
    return module


def read_file(filename):
    fh = open(filename, "r")
    try:
        return fh.read()
    finally:
        fh.close()


class ModuleLoader(object):

    def __init__(self, source_dir):
        self._modules = {}
        self._dir = source_dir

    def _import_path(self, path):
        assert len(path) > 0
        name = ".".join(path)
        if name in self._modules:
            return self._modules[name]

        if len(path) > 1:
            parent_module, top_module = self._import_path(path[:len(path)-1])
        else:
            parent_module = None
            top_module = None

        filenames = (os.path.join(self._dir, "/".join(path) + ".py"),
                     os.path.join(self._dir, "/".join(path), "__init__.py"))
        for filename in filenames:
            if os.path.exists(filename):
                module = self.load_file(filename)
                if parent_module is not None:
                    setattr(parent_module, path[-1], module)
                else:
                    top_module = module
                self._modules[name] = (module, top_module)
                return module, top_module
        raise ImportError("No module named %s" % name)

    def _import_module(self, name, globals=None, locals=None, fromlist=None):
        assert type(name) is str
        path = name.split(".")
        module, top_module = self._import_path(path)
        if fromlist is not None:
            assert type(fromlist) is tuple
            for name in fromlist:
                assert type(name) is str
                if not hasattr(module, name):
                    self._import_path(path + [name])
        return top_module

    def load_file(self, filename):
        return self.eval(read_file(filename))

    def eval(self, source):
        return safe_eval(source, {"__import__": self._import_module})
