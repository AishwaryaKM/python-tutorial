
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

import StringIO
import os
import unittest

from varbindings_test import parse_statement, assert_sets_equal
import tempdir_test
import varbindings
import pycheck


def find_expected_errors(text):
    for index, line in enumerate(text.split("\n")):
        if "FAIL:" in line:
            errors = line.split("FAIL:", 1)[1]
            for error in errors.split(","):
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
        global_vars, all_bindings = varbindings.annotate(tree)
        self.assertEquals(set(global_vars.iterkeys()), set(free_vars))
        logged = pycheck.check(tree, all_bindings)
        assert_sets_equal(sorted([(error, node.lineno)
                                  for error, node in logged]),
                          sorted(find_expected_errors(code_text)))

    def test_check(self):
        self.check(["a"], """
a.b = 1 # FAIL: SetAttr
a._b = 1 # FAIL: SetAttr
a.b
a._b # FAIL: GetAttr
del a.b # FAIL: SetAttr
del a._b # FAIL: SetAttr
a.b += 1 # FAIL: SetAttr
a._b += 1 # FAIL: SetAttr, GetAttr
""")

        self.check(["object", "C", "C2"], """
class C(object):
    def method(self):
        self.a = 1
        self._a = 2
        self.a
        self._a
        self.a += 1
        self._a += 2
        del self.a
        del self._a

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
7 // 2
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
[1,2][0] += 1
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

        self.check(["os", "unlink"], """
# Imports are handled via scope substitution: the interpreter implements
# them via __builtins__.__import__.
import os
from os import unlink

# Reject blanket imports because they hinder analysability.
# They should not be a safety problem because Python only allows them at
# top level, but reject them just to be on the safe side.
from sys import * # FAIL: BlanketImport
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
    def method5(self):
        import self
        self._foo = 1 # FAIL: SetAttr
    def method6(self):
        # This doesn't strictly need to be rejected, but "del" is currently
        # treated as an assignment.
        del self
        self._foo = 1 # FAIL: SetAttr
    def method7(self):
        self += 100
        self._foo = 1 # FAIL: SetAttr
""")

        self.check(["a", "list"], """
# These statements have the same side effect:
a.foo = 2 # FAIL: SetAttr
[1 for a.foo in [2]] # FAIL: SetAttr
list(1 for a.foo in [2]) # FAIL: SetAttr
for a.foo in [2]: # FAIL: SetAttr
    pass
""")

        self.check(["C", "object", "True"], """
class C(object):
    # This is currently rejected but it doesn't need to be.
    if True:
        def method(self):
            return self._private # FAIL: GetAttr
""")

        self.check(["C", "object"], """
class C(object):
    def method(self):
        # These are rejected because the method's function escapes.
        self.attr = 1 # FAIL: SetAttr
        return self._private # FAIL: GetAttr
    sneaky = [method]
""")

        self.check(["C", "object", "method"], """
class C(object):
    def method(self):
        # These are rejected because the method's function escapes via
        # a global declaration.
        self.attr = 1 # FAIL: SetAttr
        return self._private # FAIL: GetAttr
    global method
""")

        self.check([], """
# The backtick syntax is a deprecated and rather pointless shortcut
# for repr().  Allow it for now because it is not harmful, but any
# lint tool should reject it.
`"foo"`
""")

        self.check(["C", "object", "x", "__builtins__", "__mightbespecial__",
                    "func", "__foo", "_foo", "foo_", "foo__",
                    "__foo_", "_foo__"], """
class C(object):
    # Use of __metaclass__ must be blocked because it provides a way
    # to obtain unwrapped method functions.
    __metaclass__ = x # FAIL: SpecialVar
    def __init__(self):
        self._foo = 1

# Assignment to __builtins__ should be blocked because it could give a
# way to provide an unwrapped __import__ function, which is called
# with a local environment dictionary.  It happens that Python caches
# __builtins__ so this assignment is not harmful, but that is an
# implementation detail and it is better if we don't rely on it.
__builtins__ = {"__import__": x} # FAIL: SpecialVar

# Any other variable of the form __X__ should be blocked, to be on the
# safe side, in case Python gives them special meanings.
__mightbespecial__ = x # FAIL: SpecialVar
# This applies to local scopes too:
def func(__mightbespecial2__): # FAIL: SpecialVar
    pass
def func():
    __mightbespecial3__ = x # FAIL: SpecialVar
# But these variable names are OK:
__foo = x
_foo = x
foo_ = x
foo__ = x
__foo_ = x
_foo__ = x
""")

        self.check(["object", "C", "Suspicious", "type", "do_something"], """
class C(object):
    pass
class Suspicious(object):
    def method1(self):
        # Assignments to __class__ allow an object to change its type
        # permanently or temporarily, so we need to block this,
        # because some code can rely on checking types of objects.
        assert type(self) is Suspicious # This starts off as true
        self.__class__ = C # FAIL: SpecialAttr
        assert type(self) is C # This is now true
        do_something(self) # This might check the object's type
        # Change type back
        self.__class__ = Suspicious # FAIL: SpecialAttr
    def method2(self):
        # Also block read and write access to any double-double underscore
        # attribute in case it produces special behaviour.
        self.__mightbespecial__      # FAIL: SpecialAttr
        self.__mightbespecial__ = 1  # FAIL: SpecialAttr
        self.__mightbespecial__ += 1 # FAIL: SpecialAttr, SpecialAttr
        # This includes blocking __init__ and __dict__.  These are not
        # known to be problematic, but we will block them to err on
        # the side of caution until a use case is found.
        self.__init__     # FAIL: SpecialAttr
        self.__init__ = 1 # FAIL: SpecialAttr
        self.__dict__     # FAIL: SpecialAttr
        self.__dict__ = 1 # FAIL: SpecialAttr
""")

        self.check(["expr", "env"], """
exec expr in env # FAIL: Exec
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


def write_file(filename, data):
    fh = open(filename, "w")
    try:
        fh.write(data)
    finally:
        fh.close()


class TestFrontEnd(tempdir_test.TempDirTestCase):

    def test_front_end(self):
        temp_dir = self.make_temp_dir()
        filename = os.path.join(temp_dir, "foo.py")
        write_file(filename, """
x._y = 1
""")
        stream = StringIO.StringIO()
        pycheck.main([filename], stream)
        self.assertEquals(stream.getvalue(),
                          "%s:2: SetAttr\n  x._y = 1\n" % filename)


if __name__ == "__main__":
    unittest.main()
