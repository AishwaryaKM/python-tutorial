
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

import unittest

from lint_test import parse_statement
import lint
import pycheck


def find_expected_errors(text):
    for index, line in enumerate(text.split("\n")):
        if "FAIL:" in line:
            error = line.split("FAIL:", 1)[1]
            yield error.strip(), index + 1


# Intended to be used as a decorator.
# This inverts the test.  We do not expect the test to pass.
def TODO_test(method):
    def wrapper(self):
        self.assertRaises(AssertionError, lambda: method(self))
    wrapper.__name__ = method.__name__
    return wrapper


class CheckerTests(unittest.TestCase):

    def test_error_comments(self):
        # Expected errors can be embedded in comments for the purposes
        # of this test suite.
        code = """
blah # FAIL: FooError
blahh # FAIL: InsufficientCheeseError
"""
        self.assertEquals(list(find_expected_errors(code)),
                          [("FooError", 2), ("InsufficientCheeseError", 3)])

    def check(self, free_vars, code_text):
        tree = parse_statement(code_text)
        global_vars = lint.annotate(tree)
        self.assertEquals(global_vars, set(free_vars))
        logged = pycheck.check(tree)
        self.assertEquals(sorted([(error, node.lineno)
                                  for error, node in logged]),
                          sorted(find_expected_errors(code_text)))

    def test_check(self):
        self.check(["a"], """
a.b = 1 # FAIL: SetAttr
a._b = 1 # FAIL: SetAttr
a.b
a._b # FAIL: GetAttr
""")

        self.check(["object", "C", "C2"], """
class C(object):
    def method(self):
        self.a = 1
        self._a = 2
        self.a
        self._a

class C2(object):
    # self variables don't have to be called "self".
    def method(badger):
        badger.a = 1
        badger._a = 2
        badger.a
        badger._a
""")

        self.check(["object", "C", "func"], """
class C(object):
    @staticmethod
    def method(self):
        # self is not really a self variable here, because of the decorator.
        self.a = 1 # FAIL: SetAttr
        self._a = 2 # FAIL: SetAttr
        self.a
        self._a # FAIL: GetAttr

def func(self, arg1, arg2):
    # self is not really a self variable here either.
    self.a = 1 # FAIL: SetAttr
    self._a = 2 # FAIL: SetAttr
    self.a
    self._a # FAIL: GetAttr
""")

        self.check(["object", "C"], """
class C(object):
    def method(self):
        # Assigning to a variable disqualifies it from being a self var.
        self = object()
        self.a = 1 # FAIL: SetAttr
        self._a = 2 # FAIL: SetAttr
        self.a
        self._a # FAIL: GetAttr
    # Only the first argument is a self var.
    def method2(self, arg):
        arg.a = 2 # FAIL: SetAttr
        arg._a # FAIL: GetAttr
    # It's possible, but not useful, to not have a self var.
    def method3():
        pass
""")

        self.check(["func", "generator", "C", "object"], """
# Some attributes are special even though they don't start with "_".
def func():
    pass
func.func_globals # FAIL: GetAttr

def generator():
    yield 1
generator().gi_frame # FAIL: GetAttr

class C(object):
    def method(self):
        pass
C().im_func # FAIL: GetAttr
C().im_self # FAIL: GetAttr
""")

        self.check(["True", "False", "func", "Exception", "exn"], """
# Control flow constructs are boring.
while True:
    break
while False:
    continue
def func():
    pass
def func():
    yield 100
if True:
    func()

try:
    func("try")
finally:
    func("done")

try:
    func("try")
except Exception, exn:
    func(exn)

try:
    func("try")
except Exception:
    func(exn)

try:
    func("try")
except:
    func("failed")

# These operators are boring.
1 + 1
1 - 1
2 * 2
2 / 2
7 % 2
2 ** 32
0xff & 0xff
0 | 0
1 ^ 2
~0
+1
-1
1 << 32
100 >> 1
True and False
False or True
not True
"o" in "foo"
"i" not in "team"
[1,2][0]
[1,2][:]
# Comparisons can expose non-determinism, but let's ignore that for now.
1 < 1
# Built-in constructors.
(1, 2)
[1, 2]
{"a": 1, "b": 2}
# Keyword arguments to functions.
func(x=1, y=2)
# Anything else.
assert False
""")

        self.check([], """
print "foo" # FAIL: Print
print "foo", # FAIL: Print
""")

        self.check([], """
# Reject all imports for the time being.
import os # FAIL: Import
from os import unlink # FAIL: Import
# Blanket imports should definitely be prevented because they hinder
# analysability.
from sys import * # FAIL: Import
""")

        self.check(["C", "object", "list"], """
class C(object):
    def method1(self):
        # This list comprehension has the side effect of assigning to self.
        [self for self in (1,2)]
        self._foo = 1 # FAIL: SetAttr
    def method2(self):
        # But the generator is fine.
        list(self for self in (1,2))
        self._foo = 1
    def method3(self):
        # Assignments can escape from some parts of generators.
        list(x for x in [self for self in (1,2)])
        self._foo = 1 # FAIL: SetAttr
    def method4(self):
        # But not from other parts of generators.
        list(x for x in (1,2)
               for y in [self for self in (1,2)])
        self._foo = 1
""")

        self.check(["a", "list"], """
# These statements have the same side effect:
a.foo = 2 # FAIL: SetAttr
[1 for a.foo in [2]] # FAIL: SetAttr
list(1 for a.foo in [2]) # FAIL: SetAttr
for a.foo in [2]: # FAIL: SetAttr
    pass
""")

    @TODO_test
    def test_check_2(self):
        self.check(["C", "object"], """
class C(object):
    def method(self):
        self._private
    # This should be rejected because it allows the method's function to
    # escape the class definition.
    global f
    f = method # FAIL: MethodEscapes
    lst = [method] # FAIL: MethodEscapes
""")

    @TODO_test
    def test_check_3(self):
        self.check(["Exception", "object"], """
# Raise will need checking to make sure it doesn't leak authority
raise Exception(object()) # FAIL: Raise
""")

    def test_private_attributes_of_functions(self):
        def example_function():
            pass
        example_lambda = lambda: None

        for obj in (example_function, example_lambda):
            self.assertEquals(
                [attr for attr in sorted(dir(obj))
                 if not attr.startswith("_")],
                ["func_closure", "func_code", "func_defaults",
                 "func_dict", "func_doc", "func_globals", "func_name"])
            for attr in dir(obj):
                assert pycheck.is_private_attr(attr), attr

    def test_private_attributes_of_bound_methods(self):
        class C(object):
            def method(self):
                pass
        example_method = C().method
        self.assertEquals(
            [attr for attr in sorted(dir(example_method))
             if not attr.startswith("_")],
            ["im_class", "im_func", "im_self"])
        for attr in dir(example_method):
            assert pycheck.is_private_attr(attr), attr

    def test_private_attributes_of_generators(self):
        def generator_func():
            yield 1
        generators = (generator_func(), (x + 1 for x in range(10)))

        allowed_attrs = ["next", "send", "throw", "close"]
        for obj in generators:
            self.assertEquals(
                [attr for attr in sorted(dir(obj))
                 if not attr.startswith("_")],
                sorted(["gi_frame", "gi_running"] + allowed_attrs))
            for attr in dir(obj):
                assert (pycheck.is_private_attr(attr) or
                        attr in allowed_attrs), attr


if __name__ == "__main__":
    unittest.main()
