
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

import os
import unittest

import safeeval
import tempdir_test
import traceback


def write_file(filename, data):
    fh = open(filename, "w")
    try:
        fh.write(data)
    finally:
        fh.close()


def visible_dict(dictionary):
    return dict((key, value) for key, value in dictionary.iteritems()
                if not key.startswith("_"))


class TestAssumptionsAboutPython(unittest.TestCase):

    def test_exec(self):
        # Python's "exec" fills out __builtins__ by default, but
        # hopefully nothing else.
        env = {}
        exec "" in env
        self.assertEquals(env.keys(), ["__builtins__"])

    def test_import(self):
        got = []
        def my_import(*args):
            got.append(args)
        env = {"__builtins__": {"__import__": my_import}}
        exec "import foo.bar" in env
        self.assertEquals(len(got), 1)
        name, imp_globals, imp_locals, fromlist = got[0]
        self.assertEquals(name, "foo.bar")
        self.assertEquals(fromlist, None)
        assert imp_globals is env
        assert imp_locals is env


class EvalTest(unittest.TestCase):

    def test_default_module_attributes(self):
        env = safeeval.Environment()
        module = safeeval.safe_eval("", env)
        # Checks that Python is not adding extra attributes to the
        # module or to its __builtins__ object.
        self.assertEquals(sorted(module.__dict__.keys()),
                          ["__builtins__", "__doc__", "__name__"])
        self.assertEquals(sorted(env._module.__dict__.keys()),
                          ["__doc__", "__name__"])

    def test_assignment_to_local(self):
        module = safeeval.safe_eval("a = 42", safeeval.Environment())
        self.assertEquals(visible_dict(module.__dict__), {"a": 42})

    def test_assignment_to_global(self):
        module = safeeval.safe_eval("""
global a
a = 42
""", safeeval.Environment())
        self.assertEquals(visible_dict(module.__dict__), {"a": 42})

    def test_no_access_to_builtins(self):
        self.assertRaises(
            NameError,
            lambda: safeeval.safe_eval("open", safeeval.Environment()))

    def test_rejecting_bad_code(self):
        self.assertRaises(
            safeeval.VerifyError,
            lambda: safeeval.safe_eval("x._y", safeeval.Environment()))

    def test_initial_environment(self):
        env = safeeval.Environment()
        env.bind("x", 123)
        env_copy = dict(env._module.__dict__)
        module = safeeval.safe_eval("""
y = x
x = 456
""", env)
        # The __builtins__ dictionary should be unchanged despite the
        # assignment to "x".
        self.assertEquals(env._module.x, 123)
        self.assertEquals(env._module.__dict__, env_copy)
        self.assertEquals(visible_dict(module.__dict__), {"y": 123, "x": 456})

    def test_import_failing(self):
        try:
            safeeval.safe_eval("import foo", safeeval.Environment())
        except ImportError, exn:
            self.assertEquals(str(exn), "__import__ not found")
        else:
            self.fail("Expected import to fail")

    def test_informative_error(self):
        try:
            safeeval.safe_eval("""
def func():
    x.y = 1
""", safeeval.Environment())
        except safeeval.VerifyError, exn:
            self.assertEquals(str(exn), """
line 3: SetAttr, in func
  x.y = 1\
""")
        else:
            self.fail("Expected exception")

    def test_exploit_via_import(self):
        # This demonstrates how untamed use of __import__ could
        # capture a local environment dictionary which can be used to
        # capture a method function out of a class scope.
        def exploit():
            captured = []
            def my_import(name, globals, locals, fromlist):
                captured.append(locals["method"])
            safeeval.safe_eval("""
class C:
    def method(self):
        self._private = "dangerous"
    import bob
""", {"__import__": my_import})
            self.assertEquals(len(captured), 1)
            class UnrelatedObject(object):
                pass
            obj = UnrelatedObject()
            captured[0](obj)
            self.assertEquals(obj._private, "dangerous1")

        self.assertRaises(AssertionError, exploit)

    def test_restrictions_on_builtins(self):
        env = safeeval.Environment()
        # __import__ cannot be defined directly.
        self.assertRaises(AssertionError,
                          lambda: env.bind("__import__", lambda *args: None))
        self.assertRaises(AssertionError,
                          lambda: env.bind("_mightbespecial", 1))

    def test_import_wrapping(self):
        # Check that the import function is not passed locals or
        # globals dictionaries.
        class Example(object):
            baz = 1
            bazz = 2
        got = []
        def my_import(*args):
            got.append(args)
            return Example()
        env = safeeval.Environment()
        env.set_importer(my_import)
        safeeval.safe_eval("""
import foo.bar1
from foo.bar2 import baz as quux, bazz as quuux
""", env)
        self.assertEquals(got, [("foo.bar1", None),
                                ("foo.bar2", ("baz", "bazz"))])

    def test_builtins_object_is_readonly(self):
        # If __builtins__ is accessible, it should be read-only, so
        # that it can be shared between mutually distrusting modules,
        # and so that __import__ cannot be assigned (because it
        # exposes the "locals" dict).
        # We don't make the __builtins__ object accessible though.
        # This test uses a trick of passing in "globals", which is not
        # a safe function, so that we can test an object that is not
        # normally accessible.
        code = 'globals()["__builtins__"]["__import__"] = 1'
        env = safeeval.Environment()
        env.bind("globals", globals)
        try:
            safeeval.safe_eval(code, env)
        except TypeError, exn:
            self.assertEquals(
                str(exn), "'module' object does not support item assignment")
        else:
            self.fail("Expected TypeError")

    def test_safesuper(self):
        code = """
class C(object):
    def _method(self, arg):
        return "foo%i" % arg
    def f(self):
        return self._method(1)

class D(C):
    def _method(self, arg):
        return safesuper(self, C, "_method")(arg + 1) + "bar"

x = D().f()
"""
        m = safeeval.safe_eval(code, safeeval.safe_environment())
        self.assertEquals(m.x, "foo2bar")


class ModuleLoaderTest(tempdir_test.TempDirTestCase):

    def test_simple_import(self):
        temp_dir = self.make_temp_dir()
        loader = safeeval.ModuleLoader([temp_dir])
        write_file(os.path.join(temp_dir, "foo.py"), "a = 123")
        module = loader.eval("""
import foo
x = foo.a

from foo import a
from foo import a as y
""")
        self.assertEquals(module.x, 123)
        self.assertEquals(module.a, 123)
        self.assertEquals(module.y, 123)
        self.assertRaises(ImportError, lambda: loader.eval("from foo import z"))

    def test_nested_import(self):
        temp_dir = self.make_temp_dir()
        os.mkdir(os.path.join(temp_dir, "foo"))
        write_file(os.path.join(temp_dir, "foo", "__init__.py"), "")
        write_file(os.path.join(temp_dir, "foo", "bar.py"), "a = 123")

        loader = safeeval.ModuleLoader([temp_dir])
        module = loader.eval("""
import foo.bar
x = foo.bar.a
""")
        self.assertEquals(module.x, 123)

        loader = safeeval.ModuleLoader([temp_dir])
        module = loader.eval("""
from foo import bar
x = bar.a
""")
        self.assertEquals(module.x, 123)

        loader = safeeval.ModuleLoader([temp_dir])
        module = loader.eval("""
from foo.bar import a as x
""")
        self.assertEquals(module.x, 123)

    def test_deeper_nested_import(self):
        temp_dir = self.make_temp_dir()
        os.mkdir(os.path.join(temp_dir, "foo"))
        write_file(os.path.join(temp_dir, "foo", "__init__.py"), "")
        os.mkdir(os.path.join(temp_dir, "foo", "qux"))
        write_file(os.path.join(temp_dir, "foo", "qux", "__init__.py"), "")
        write_file(os.path.join(temp_dir, "foo", "qux", "bar.py"), "a = 123")

        loader = safeeval.ModuleLoader([temp_dir])
        module = loader.eval("""
import foo.qux.bar
x = foo.qux.bar.a
""")
        self.assertEquals(module.x, 123)

        loader = safeeval.ModuleLoader([temp_dir])
        module = loader.eval("""
from foo.qux import bar
x = bar.a
""")
        self.assertEquals(module.x, 123)

        loader = safeeval.ModuleLoader([temp_dir])
        module = loader.eval("""
from foo.qux.bar import a as x
""")
        self.assertEquals(module.x, 123)

    def test_search_path(self):
        temp_dir1 = self.make_temp_dir()
        temp_dir2 = self.make_temp_dir()
        write_file(os.path.join(temp_dir1, "foo.py"), "a = 123")
        write_file(os.path.join(temp_dir1, "bar.py"), "b = 456")
        loader = safeeval.ModuleLoader([temp_dir1, temp_dir2])
        module = loader.eval("""
from foo import a
from bar import b
""")
        self.assertEquals(module.a, 123)
        self.assertEquals(module.b, 456)

    def test_missing_import(self):
        loader = safeeval.ModuleLoader([self.make_temp_dir()])
        self.assertRaises(ImportError, lambda: loader.eval("import foo"))

    def test_add_module(self):
        class Module(object):
            foo = 123
        loader = safeeval.ModuleLoader(None)
        loader.add_module("baz", Module())
        module = loader.eval("from baz import foo")
        self.assertEquals(module.foo, 123)
        # The interface is not complete yet:
        self.assertRaises(AssertionError,
                          lambda: loader.add_module("foo.bar", Module()))

    def test_using_filename(self):
        for use_filename in (False, True):
            execfunc = safeeval.Evaluator(use_filename=use_filename,
                                          warn_only=False).exec_code
            loader = safeeval.ModuleLoader(None, eval_func=execfunc)
            filename = os.path.join(self.make_temp_dir(), "foo.py")
            write_file(filename, "raise Exception()")
            try:
                loader.load_file(filename)
            except:
                trace = traceback.format_exc()
                expected = 'File "%s", line 1,' % filename
                self.assertEquals(expected in trace, use_filename)
            else:
                self.fail("Expected an exception")


if __name__ == "__main__":
    unittest.main()
