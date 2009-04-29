
# Copyright (C) 2008 Mark Seaborn
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301, USA.

import compiler
import os
import types

import pycheck
import varbindings


class VerifyError(Exception):

    # Is it a good idea to include the failed parts of the source code
    # by default?  It might expose source code that is intended to be
    # concealed.
    def __init__(self, log, tree, source_code, filename):
        self._source_code = source_code
        self._log = log
        self._tree = tree
        self._filename = filename

    def __str__(self):
        # Could use something like linecache here, except it uses filenames.
        lines = self._source_code.split("\n")
        def get_line(lineno):
            return lines[lineno - 1]
        return "".join("\n" + message for message in
                       pycheck.format_log(self._log, self._tree, get_line,
                                          self._filename))


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
            code_filename = "<string>"
        else:
            code_filename = filename
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
                print VerifyError(log, tree, source_code, filename)
            else:
                raise VerifyError(log, tree, source_code, filename)
        for var_name, binding in sorted(global_vars.iteritems()):
            if not binding.is_assigned:
                assert binding.is_read
                if var_name not in builtins._module.__dict__:
                    print code_filename, "unbound:", var_name
        code = compile(source_code, code_filename, "exec")
        exec code in module.__dict__
        return module


safe_eval = Evaluator(use_filename=False, warn_only=False).exec_code


def read_file(filename):
    fh = open(filename, "r")
    try:
        return fh.read()
    finally:
        fh.close()


def safe_hasattr(obj, attrname):
    assert type(attrname) is str
    return not pycheck.is_private_attr(attrname) and hasattr(obj, attrname)

def type_is(obj, ty):
    return type(obj) is ty


def _safesuper(obj, klass, attrname):
    assert type(attrname) is str
    assert (not pycheck.is_special_attr(attrname)
            or attrname == "__init__"), attrname
    # Make sure klass is not a tuple before isinstance check
    assert type(klass) is type or type(klass) is types.ClassType, klass
    assert isinstance(obj, klass)
    method = getattr(klass, attrname)
    def bound_method(*args, **kwargs):
        return method(obj, *args, **kwargs)
    return bound_method


def safe_builtins():
    for name in ("None", "True", "False",
                 "ImportError", "IOError", "NameError", "KeyError",
                 "AttributeError", "TypeError", "IndexError",
                 "StopIteration",
                 "dict", "list", "tuple", "int", "str", "basestring",
                 "chr", "ord",
                 "range", "xrange",
                 "len",
                 "min", "max",
                 "isinstance",
                 "object",
                 ):
        yield name, __builtins__[name]
    yield "hasattr", safe_hasattr
    # non-standard
    yield "type_is", type_is


def safe_environment():
    env = Environment()
    for name, value in safe_builtins():
        env.bind(name, value)
    env.bind("safesuper", _safesuper)
    return env


class ModuleLoader(object):

    def __init__(self, search_path, eval_func=safe_eval):
        self._modules = {}
        self._paths = search_path
        self._eval_func = eval_func
        self._env = safe_environment()
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

        # Python's normal importer is stricter than this.
        filenames = (
            filename
            for search_dir in self._paths
            for filename in (
                os.path.join(search_dir, "/".join(path) + ".py"),
                os.path.join(search_dir, "/".join(path), "__init__.py")))
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
