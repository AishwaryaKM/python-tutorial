
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
        module = safeeval.safe_eval("", {})
        self.assertEquals(sorted(module.__dict__.keys()),
                          ["__builtins__", "__doc__", "__name__"])

    def test_assignment_to_local(self):
        module = safeeval.safe_eval("a = 42", {})
        self.assertEquals(visible_dict(module.__dict__), {"a": 42})

    def test_assignment_to_global(self):
        module = safeeval.safe_eval("""
global a
a = 42
""", {})
        self.assertEquals(visible_dict(module.__dict__), {"a": 42})

    def test_no_access_to_builtins(self):
        self.assertRaises(NameError,
                          lambda: safeeval.safe_eval("open", {}))

    def test_rejecting_bad_code(self):
        self.assertRaises(safeeval.VerifyError,
                          lambda: safeeval.safe_eval("x._y", {}))

    def test_initial_environment(self):
        env = {"x": 123}
        module = safeeval.safe_eval("""
y = x
x = 456
""", env)
        self.assertEquals(env, {"x": 123})
        self.assertEquals(visible_dict(module.__dict__), {"y": 123, "x": 456})

    def test_import_failing(self):
        try:
            safeeval.safe_eval("import foo", {})
        except ImportError, exn:
            self.assertEquals(str(exn), "__import__ not found")
        else:
            self.fail("Expected import to fail")


class ModuleLoaderTest(tempdir_test.TempDirTestCase):

    def test_simple_import(self):
        temp_dir = self.make_temp_dir()
        loader = safeeval.ModuleLoader(temp_dir)
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

        loader = safeeval.ModuleLoader(temp_dir)
        module = loader.eval("""
import foo.bar
x = foo.bar.a
""")
        self.assertEquals(module.x, 123)

        loader = safeeval.ModuleLoader(temp_dir)
        module = loader.eval("""
from foo import bar
x = bar.a
""")
        self.assertEquals(module.x, 123)

    def test_missing_import(self):
        loader = safeeval.ModuleLoader(self.make_temp_dir())
        self.assertRaises(ImportError, lambda: loader.eval("import foo"))


if __name__ == "__main__":
    unittest.main()
