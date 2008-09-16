
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

    # Is it a good idea to include the failed parts of the source code
    # by default?  It might expose source code that is intended to be
    # concealed.
    def __init__(self, log, source_code):
        self._source_code = source_code
        self._log = log

    # TODO: allow a filename to be included in the output.
    def __str__(self):
        parts = []
        # Could use something like linecache here.
        source_lines = self._source_code.split("\n")
        for error, node in self._log:
            line = source_lines[node.lineno - 1].strip()
            parts.append("\nline %i: %s\n  %s" % (node.lineno, error, line))
        return "".join(parts)


class Environment(object):

    # We cannot let untrusted code provide its own __builtins__ object
    # directly because it could provide its own __import__ function,
    # and Python calls __import__ with locals and globals
    # dictionaries.  We need to wrap __import__.

    def __init__(self):
        # Python allows the __builtins__ object to be a dictionary or
        # a module.  We use a module in order to make it read-only to
        # CapPython code.
        self._module = types.ModuleType("__safe_eval_builtins__")

    def bind(self, name, value):
        assert type(name) is str
        assert not name.startswith("_")
        self._module.__dict__[name] = value

    def set_importer(self, func):
        def import_wrapper(name, globals=None, locals=None, fromlist=None):
            return func(name, fromlist)
        self._module.__dict__["__import__"] = import_wrapper


class Evaluator(object):

    # This allows two unsafe modes:
    # - use_filename: This is unsafe because it allows an arbitrary
    #   filename to be attached to a Python code object, and the
    #   interpreter will open the named file when formatting a
    #   traceback.
    # - warn_only: This converts the checks' errors to warnings.
    def __init__(self, use_filename, warn_only):
        self._use_filename = use_filename
        self._warn_only = warn_only

    def exec_code(self, source_code, builtins, filename=None):
        if not self._use_filename or filename is None:
            filename = "<string>"
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
        assert type(builtins) is Environment
        module = types.ModuleType("__safe_eval_module__")
        module.__dict__["__builtins__"] = builtins._module
        tree = compiler.parse(source_code)
        global_vars, bindings = varbindings.annotate(tree)
        log = pycheck.check(tree, bindings)
        if len(log) > 0:
            if self._warn_only:
                print VerifyError(log, source_code)
            else:
                raise VerifyError(log, source_code)
        code = compile(source_code, filename, "exec")
        exec code in module.__dict__
        return module


safe_eval = Evaluator(use_filename=False, warn_only=False).exec_code


def read_file(filename):
    fh = open(filename, "r")
    try:
        return fh.read()
    finally:
        fh.close()


class ModuleLoader(object):

    def __init__(self, source_dir, eval_func=safe_eval):
        self._modules = {}
        self._dir = source_dir
        self._eval_func = eval_func
        self._env = Environment()
        self._env.set_importer(self._import_module)

    def add_module(self, name, module):
        # We don't handle compound module names yet.
        assert "." not in name
        self._modules[name] = (module, module)

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

    def _import_module(self, name, fromlist=None):
        assert type(name) is str
        path = name.split(".")
        module, top_module = self._import_path(path)
        if fromlist is None:
            return top_module
        else:
            assert type(fromlist) is tuple
            for name in fromlist:
                assert type(name) is str
                if not hasattr(module, name):
                    self._import_path(path + [name])
            return module

    def load_file(self, filename):
        return self.eval(read_file(filename), filename)

    def eval(self, source, filename=None):
        return self._eval_func(source, self._env, filename)
