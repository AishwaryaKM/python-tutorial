
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
import unittest

import varbindings


def assert_sets_equal(actual, expected):
    if sorted(actual) != sorted(expected):
        missing = [x for x in expected if x not in actual]
        excess = [x for x in actual if x not in expected]
        raise AssertionError("Sets don't match:\nexpected: %r\nactual: %r\n\n"
                             "missing: %r\nexcess: %r" %
                             (expected, actual, missing, excess))


parse_statement = compiler.parse


def find_expected_bindings(source_text):
    for index, line in enumerate(source_text.split("\n")):
        line_vars = {}
        if "VAR:" in line:
            bindings = line.split("VAR:", 1)[1]
            for binding in bindings.split(","):
                var_name, var_id = binding.strip().split(":", 1)
                assert var_name not in line_vars
                line_vars[var_name] = var_id
        yield line_vars


def find_actual_bindings(tree):
    for node in varbindings.iter_nodes(tree):
        if hasattr(node, "bindings"):
            for binding in node.bindings:
                yield (binding, node.lineno)


class LintTest(unittest.TestCase):

    def check_find_assigned(self, expected_assigned_vars, code_text):
        tree = parse_statement(code_text)
        assert_sets_equal(varbindings.find_assigned(tree),
                          set(expected_assigned_vars))
        global_vars = varbindings.annotate(tree)
        assigned_vars = set(var_name
                            for var_name, binding in global_vars.iteritems()
                            if binding.is_assigned)
        assert_sets_equal(assigned_vars, set(expected_assigned_vars))

    def test_find_assigned(self):
        self.check_find_assigned(["x", "y", "a", "b", "a2", "b2", "c", "d", "e",
                                  "func", "Class", "element", "exn"], """
x = foo1
y = foo2
a, b = foo3
[a2, b2] = foo3
c += foo3
d = e = foo4
def func(arg):
    f = foo5
class Class(object):
    method = foo6
for element in [1, 2, 3]:
    print element

try:
    pass
except Exception, exn:
    pass
""")

        self.check_find_assigned(["x", "y"], """
del x, y
""")

        self.check_find_assigned([], """
lambda x: x + 1
""")

        self.check_find_assigned(["foo1", "foo2", "foo3",
                                  "a1", "a2", "a3", "a4",
                                  "name1", "name2", "name3", "name4"], """
import foo1
import foo2.bar
import bar.baz as foo3
# These can also be combined into a single import statement.
import blah1 as a1, blah2 as a2, a3.bar, a4

from bar.baz import name1, name2
from bar.baz import qux as name3, quux as name4
from other_module import *
""")

        self.check_find_assigned(["x", "y", "z1", "z2"], """
# Assigned variables in list comprehensions escape, for no good reason
# that I can see.  There's a good reason for the assigned variable to
# escape from a "for" loop, but not for a list comprehension.
# Why can't the variable be bound, as with a lambda?
# The Python Reference Manual says "this behavior is deprecated, and
# relying on it will not work once this bug is fixed in a future release".
# (http://docs.python.org/ref/lists.html)
[x+1 for x, y in enumerate(range(100))]
[None for z1 in range(10)
      for z2 in range(10) if z1 % 2 == 0]
""")

        # Generators have different binding rules: they introduce new
        # scopes.
        self.check_find_assigned([], """
list(x+1 for x, y in enumerate(range(100)))
list(None for z1 in range(10)
          for z2 in range(10) if z1 % 2 == 0)
""")

    def test_read_variables(self):
        source = """
print read1
w1 = 1
readwrite += 1
del w2
def w3():
    return read2
class w4:
    pass
import w5
from xx import w6
"""
        global_vars = varbindings.annotate(parse_statement(source))
        assert_sets_equal(sorted(global_vars.iterkeys()),
                          ["read1", "read2", "readwrite",
                           "w1", "w2", "w3", "w4", "w5", "w6"])
        assert_sets_equal([var for var, binding in global_vars.iteritems()
                           if binding.is_assigned],
                          ["readwrite", "w1", "w2", "w3", "w4", "w5", "w6"])
        assert_sets_equal([var for var, binding in global_vars.iteritems()
                           if binding.is_read],
                          ["readwrite", "read1", "read2"])

    def test_find_globals(self):
        tree = parse_statement("""
global a
global b, c
if False:
    global d
while False:
    global e
for x in y:
    global f
def func(arg):
    global hidden1
class C:
    global hidden2
""")
        self.assertEquals(varbindings.find_globals(tree),
                          set(["a", "b", "c", "d", "e", "f"]))
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
            global_vars = varbindings.annotate(parse_statement(text))
            return set(global_vars.iterkeys())
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
lambda x: x
lambda x: freevar
"""
        self.assertEquals(free_vars(text), set(["freevar"]))

        text = """
[x for x in (1,2)] # Variable escapes
(y for y in (1,2)) # Variable does not escape
"""
        self.assertEquals(free_vars(text), set(["x"]))

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

    def check_isomorphism(self, relation):
        mapping1 = {}
        mapping2 = {}
        for x, y in relation:
            mapping1.setdefault(x, set()).add(y)
            mapping2.setdefault(y, set()).add(x)
        for x, ys in mapping1.iteritems():
            assert len(ys) == 1, (x, ys)
        for y, xs in mapping2.iteritems():
            assert len(xs) == 1, (y, xs)

    def match_up_bindings(self, source):
        tree = parse_statement(source)
        varbindings.annotate(tree)
        got_vars = list(find_actual_bindings(tree))
        expected = list(find_expected_bindings(source))
        # Check that lines refer to the expected variable names.
        expected_var_lines = [(var_name, line_index + 1)
                              for line_index, var_map in enumerate(expected)
                              for var_name in var_map.keys()]
        actual_var_lines = [(binding.name, lineno)
                            for binding, lineno in got_vars]
        assert_sets_equal(sorted(set(actual_var_lines)),
                          sorted(set(expected_var_lines)))
        # Check 1-1 mapping.
        relation = []
        for binding, lineno in got_vars:
            var_id = expected[lineno - 1][binding.name]
            relation.append((var_id, binding))
        self.check_isomorphism(relation)

    def test_scoping(self):
        bad_source = """
# Annotations wrongly say they refer to different variables.
x = 1 # VAR: x:one_var
x + x # VAR: x:another_var
"""
        self.assertRaises(AssertionError,
                          lambda: self.match_up_bindings(bad_source))

        bad_source = """
# Annotations wrongly say they refer to the same variable.
x = 1 # VAR: x:foo
def f(x):
    return x # VAR: x:foo
"""
        self.assertRaises(AssertionError,
                          lambda: self.match_up_bindings(bad_source))

        source = """
x = 1 # VAR: x:global_x
x + x # VAR: x:global_x
y = 1 # VAR: y:global_y
def f(x): # VAR: f:func
    y # VAR: y:global_y
    return x # VAR: x:local_x
"""
        self.match_up_bindings(source)

        source = """
g = 1 # VAR: g:1
def f(): # VAR: f:func
    global g
    g = 2 # VAR: g:1

def f2(): # VAR: f2:f2
    # This global declaration has no effect, because the variable is not
    # assigned and so would be global anyway.
    global g
    return g # VAR: g:1
"""
        self.match_up_bindings(source)

        source = """
x = 1 # VAR: x:global_x
y = 2 # VAR: y:global_y
def f(): # VAR: f:func
    x = 1 # VAR: x:local_x
    return (x, y) # VAR: x:local_x, y:global_y
"""
        self.match_up_bindings(source)

        source = """
def f(): # VAR: f:f
    x = "x1" # VAR: x:x1
    y = "y1" # VAR: y:y1
    class C: # VAR: C:C
        print x # VAR: x:x1
        print y # VAR: y:y2
        y = "y2" # VAR: y:y2
"""
        self.match_up_bindings(source)

        source = """
x = 1 # VAR: x:x
class C: # VAR: C:C
    global x
    x = 2 # VAR: x:x
"""
        self.match_up_bindings(source)

        source = """
x = 1 # VAR: x:globalx
class C: # VAR: C:C
    x = 2 # VAR: x:classx
    y = 99 # VAR: y:classy
    print x # VAR: x:classx
    def f(): # VAR: f:f
        print x # VAR: x:globalx
    class D: # VAR: D:D
        print x # VAR: x:globalx
    f = ( # VAR: f:f
      lambda: x) # VAR: x:globalx
    print [x for y in ()] # VAR: x:classx, y:classy
    print (x for y in ()) # VAR: x:globalx, y:localy
"""
        self.match_up_bindings(source)

        source = """
# Test handling of default arguments and *args/**kwargs
a = 1 # VAR: a:global1
b = 2 # VAR: b:global2
args = 1 # VAR: args:global3
kwargs = 2 # VAR: kwargs:global4
def f(x=a, y=b, *args, **kwargs): # VAR: f:f, a:global1, b:global2
    print x # VAR: x:local1
    print y # VAR: y:local2
    print args # VAR: args:local3
    print kwargs # VAR: kwargs:local4
"""
        self.match_up_bindings(source)

        source = """
# Test handling of tuple-pattern arguments
x = 1 # VAR: x:global1
y = 1 # VAR: y:global2
def f((x, (y, z))): # VAR: f:f
    print x # VAR: x:local1
    print y # VAR: y:local2
    print z # VAR: z:local3
f = (lambda (x, (y, z)): # VAR: f:f
       x + y + z) # VAR: x:local4, y:local5, z:local6
"""
        self.match_up_bindings(source)

        source = """
x = 2 # VAR: x:globalx
del x # VAR: x:globalx
def f(): # VAR: f:f
    del x # VAR: x:localx
"""
        self.match_up_bindings(source)

        source = """
x = 1 # VAR: x:globalx
def f(): # VAR: f:f
    for x in []: # VAR: x:localx
        print x # VAR: x:localx
"""
        self.match_up_bindings(source)

        source = """
sys = 1 # VAR: sys:globalvar
def f(): # VAR: f:f
    import sys # VAR: sys:localvar
    sys.stdout.write("hello") # VAR: sys:localvar
"""
        self.match_up_bindings(source)

        # List comprehensions
        source = """
x = 1 # VAR: x:globalx
def f(): # VAR: f:f
    x = 2 # VAR: x:localx
    [x + 1 # VAR: x:localx
       for x in (1,2,3)] # VAR: x:localx
    return x # VAR: x:localx

def f(): # VAR: f:f
    global x
    [x + 1 # VAR: x:globalx
       for x in (1,2,3)] # VAR: x:globalx
"""
        self.match_up_bindings(source)

        source = """
x = 1 # VAR: x:globalx
(x + 1 # VAR: x:bound
   for x in (1,2,3)) # VAR: x:bound
"""
        self.match_up_bindings(source)

        source = """
x = 1 # VAR: x:globalx
(lambda x:
   lambda y:
     x) # VAR: x:localx
"""
        self.match_up_bindings(source)

        source = """
exn = 1 # VAR: exn:exn
try:
    f() # VAR: f:f
except Exception, exn: # VAR: Exception:Exception, exn:exn
    print exn # VAR: exn:exn

try:
    f() # VAR: f:f
except Exception: # VAR: Exception:Exception
    pass

try:
    f() # VAR: f:f
except:
    print "got exception"

def func(): # VAR: func:func
    try:
        print exn # VAR: exn:localexn
    except Exception, exn: # VAR: Exception:Exception, exn:localexn
        print exn # VAR: exn:localexn

try:
    print x # VAR: x:x
except Exception, x: # VAR: Exception:Exception, x:x
    print x # VAR: x:x
else:
    print x # VAR: x:x
finally:
    print x # VAR: x:x
"""
        self.match_up_bindings(source)


if __name__ == "__main__":
    unittest.main()
