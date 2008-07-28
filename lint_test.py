
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

from compiler import ast
import compiler
import unittest

import lint


def parse_statement(string):
    tree = compiler.parse(string)
    assert isinstance(tree, ast.Module)
    return tree.node


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


class LintTest(unittest.TestCase):

    def test_find_assigned(self):
        tree = parse_statement("""
x = foo1
y = foo2
a, b = foo3
c += foo3
d = e = foo4
def func(arg):
    f = foo5
""")
        self.assertEquals(lint.find_assigned(tree),
                          set(["x", "y", "a", "b", "c", "d", "e", "func"]))

    def test_find_globals(self):
        tree = parse_statement("""
global a
global b, c
def func(arg):
    global d
""")
        self.assertEquals(lint.find_globals(tree),
                          set(["a", "b", "c"]))
        # Check that find_globals() corresponds to Python's scoping behaviour.
        eval(compiler.compile("""
x = 1
def func():
    x = "not seen"
func()
assert x == 1, x

def func():
    x = 2
    global x
func()
assert x == 2, x

x = 1
def func():
    def func2():
        # This declaration does not escape to affect func().
        global x
    x = "not seen"
func()
assert x == 1, x

def func():
    global x
    def func2():
        x = 3
    func2()
func()
assert x == 1, x

def func():
    # This declaration does not leak into func2().
    global x
    def func2():
        x = 3
    func2()
func()
assert x == 1, x

def func(x):
    def func2():
        global x
        def func3():
            assert x == 1
        func3()
    func2()
func(100)
assert x == 1, x

def func():
    global x
    def func2(x):
        assert x == 100
    func2(100)
func()
""", "filename", "exec"), {})

    def test_free_vars(self):
        def free_vars(text):
            return lint.annotate(parse_statement(text))
        text = """
f(a.attr)
def func(v):
    f(v)
    v2 = 1
    f(v2)
    f(b)
    global c
    c = 1
d = 2
"""
        self.assertEquals(free_vars(text),
                          set(["f", "a", "b", "c", "d", "func"]))
        text = """
class C(object):
    x = 0
    def f(self):
        return x # global var
    y = 0
    z = y # from class scope
    k = k # from global scope into class scope
"""
        # TODO: k should be considered a FV
        self.assertEquals(free_vars(text), set(["object", "x", "C"]))

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
        logged = lint.check(tree, free_vars)
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


if __name__ == "__main__":
    unittest.main()
