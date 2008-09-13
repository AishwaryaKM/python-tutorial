
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


def get_only(lst):
    assert len(lst) == 1, lst
    return lst[0]


class VariableReference(object):

    def __init__(self, node, is_assignment, is_read):
        self.node = node
        self.is_assignment = is_assignment
        self.is_read = is_read


class Binding(object):

    def __init__(self, name, is_global):
        assert type(name) == str, name
        self.name = name
        self.is_global = is_global
        self.references = []
        self.is_self_var = False

    @property
    def is_assigned(self):
        return any(ref.is_assignment for ref in self.references)

    @property
    def is_read(self):
        return any(ref.is_read for ref in self.references)

    def __repr__(self):
        return "<Binding 0x%x %r global=%s>" % (
            id(self), self.name, self.is_global)


# An environment is a mapping from variable names to bindings.
class Environ(object):

    def __init__(self, env, global_vars, all_bindings):
        self._env = env
        self._global_vars = global_vars
        self._all_bindings = all_bindings

    def lookup(self, name):
        return self._env[name]

    def _get(self, name):
        if name in self._env:
            return self._env[name]
        else:
            if name not in self._global_vars:
                binding = Binding(name, is_global=True)
                self._global_vars[name] = binding
                self._all_bindings.append(binding)
            return self._global_vars[name]

    def record(self, node, name, assigns, reads):
        if not hasattr(node, "bindings"):
            node.bindings = []
        binding = self._get(name)
        node.bindings.append(binding)
        var_ref = VariableReference(node, is_assignment=assigns, is_read=reads)
        binding.references.append(var_ref)

    def bind(self, name):
        binding = Binding(name, is_global=False)
        self._all_bindings.append(binding)
        env = self._env.copy()
        env[name] = binding
        return Environ(env, self._global_vars, self._all_bindings)

    def set_global(self, name):
        # Could add to global_vars too
        env = self._env.copy()
        env.pop(name, None)
        return Environ(env, self._global_vars, self._all_bindings)


class Scope(object):

    # A Python scope consists of two environments.  Usually the
    # environments are the same, but they are different for class
    # scopes.
    # local_env is used for variable references and assignments.
    # next_env is what any new, nested scopes are based on.
    def __init__(self, local_env, next_env):
        self.local_env = local_env
        self.next_env = next_env

def make_normal_scope(env):
    return Scope(env, env)


class Node(object):

    def __init__(self, node):
        self._node = node

    def assigned(self, var_set):
        raise NotImplementedError()

    def find_globals(self, var_set):
        raise NotImplementedError()

    def annotate(self, scope):
        raise NotImplementedError()

    def is_self_var(self):
        return False


class HandleName(Node):

    def assigned(self, var_set):
        pass

    def find_globals(self, var_set):
        pass

    def annotate(self, scope):
        scope.local_env.record(self._node, self._node.name, assigns=False,
                               reads=True)

    def is_self_var(self):
        return get_only(self._node.bindings).is_self_var


class HandleAssName(Node):

    def assigned(self, var_set):
        assert self._node.flags in ("OP_ASSIGN", "OP_DELETE")
        var_set.add(self._node.name)

    def find_globals(self, var_set):
        pass

    def annotate(self, scope):
        scope.local_env.record(self._node, self._node.name, assigns=True,
                               reads=False)


class HandleAugAssignVariable(Node):

    def assigned(self, var_set):
        assert isinstance(self._node.node, ast.Name)
        var_set.add(self._node.node.name)

    def find_globals(self, var_set):
        pass

    def annotate(self, scope):
        assert isinstance(self._node.node, ast.Name)
        scope.local_env.record(self._node, self._node.node.name, assigns=True,
                               reads=True)
        for node in self._node.getChildNodes():
            map_node(node).annotate(scope)


def HandleAugAssign(node):
    if isinstance(node.node, ast.Name):
        return HandleAugAssignVariable(node)
    else:
        assert isinstance(node.node, (ast.Getattr, ast.Subscript))
        return HandleBoring(node)


# Flattens tuple-pattern arguments into a list of variable names.
def get_argument_variables(args):
    if isinstance(args, str):
        yield args
    else:
        assert isinstance(args, (tuple, list))
        for arg in args:
            for result in get_argument_variables(arg):
                yield result


def annotate_function(node, scope):
    for default in node.defaults:
        map_node(default).annotate(scope)
    global_vars = find_globals(node.code)
    assigned_vars = find_assigned(node.code)
    new_env = scope.next_env
    for var in assigned_vars:
        new_env = new_env.bind(var)
    for var in global_vars:
        new_env = new_env.set_global(var)
    for var in get_argument_variables(node.argnames):
        assert var not in global_vars
        new_env = new_env.bind(var)
        # Record the argument binding as a reference so that the line
        # number can be reported.
        new_env.lookup(var).references.append(
            VariableReference(node, is_assignment=False, is_read=False))
    node.code.environ = new_env
    map_node(node.code).annotate(make_normal_scope(new_env))


class HandleLambda(Node):

    # Even though lambdas can only contain expressions, not
    # statements, they can contain assignments, because list
    # comprehensions contain assignments rather than bindings.

    def assigned(self, var_set):
        # Function starts new scope, so assignments in body are hidden
        pass

    def find_globals(self, var_set):
        assert find_globals(self._node.code) == set()

    def annotate(self, scope):
        annotate_function(self._node, scope)


class HandleFunction(Node):

    def assigned(self, var_set):
        var_set.add(self._node.name)
        # Function starts new scope, so assignments in body are hidden

    def find_globals(self, var_set):
        # Function starts new scope, so global decls in body are hidden
        pass

    def annotate(self, scope):
        scope.local_env.record(self._node, self._node.name, assigns=True,
                               reads=False)
        annotate_function(self._node, scope)


class HandleClass(Node):

    def assigned(self, var_set):
        var_set.add(self._node.name)
        # No recurse

    def find_globals(self, var_set):
        # No recurse
        pass

    def annotate(self, scope):
        scope.local_env.record(self._node, self._node.name, assigns=True,
                               reads=False)
        for base in self._node.bases:
            map_node(base).annotate(scope)
        # Classes have weird-assed scoping rules.
        # Classes do not behave according to lexical scope!
        # Assigned variables are not inherited by any nested scopes
        # that appear within the class scope.
        # Assigned variables' values default to those of their namesakes
        # in global (not enclosing) scope.
        new_env = scope.next_env
        for var in find_assigned(self._node.code):
            # Approximation: introduces a new binding, but its value
            # defaults to the value in the global scope.
            new_env = new_env.bind(var)
        for var in find_globals(self._node.code):
            new_env = new_env.set_global(var)
        map_node(self._node.code).annotate(Scope(new_env, scope.next_env))


# Helper wrapper that introduces a new scope.
class HandleNewScopeExpr(Node):

    def __init__(self, node_handler):
        self._node_handler = node_handler

    def assigned(self, var_set):
        # Assigned variables do not escape the new scope.
        pass

    def find_globals(self, var_set):
        assert find_globals_from_handler(self._node_handler) == set()

    def annotate(self, scope):
        new_env = scope.next_env
        for var in find_assigned_from_handler(self._node_handler):
            new_env = new_env.bind(var)
        self._node_handler.annotate(make_normal_scope(new_env))


# Helper wrapper.  TODO: merge with HandleBoring
class HandleCompoundExpr(Node):

    def __init__(self, node_handlers):
        self._node_handlers = node_handlers

    def assigned(self, var_set):
        for node_handler in self._node_handlers:
            node_handler.assigned(var_set)

    def find_globals(self, var_set):
        for node_handler in self._node_handlers:
            node_handler.find_globals(var_set)

    def annotate(self, scope):
        for node_handler in self._node_handlers:
            node_handler.annotate(scope)


# Generators have odd scoping behaviour.  Unlike list comprehensions
# and "for" loops, it introduces new scopes.  Unlike "lambda", it does
# not necessarily bind a variable; it assigns to lvalues, which
# introduces a binding as per the normal rules *if* the lvalue is a
# variable.  Consider this generator expression:
#   (E for x in sequence1
#      if f(x)
#      for y in sequence2)
# This is logically structured like this:
#   iterate_over sequence1 {assign x:
#       if f(x):
#           iterate_over sequence2 {assign y:
#               yield E}}
# where {...} indicates a new scope, and "iterate_over Y assign X" is
# a different way of saying "for X in Y".  Note that the scopes are
# not syntactically contiguous in the original: E has to be moved from
# the start to the end to keep the scope together.  This is why we
# rejig the contents of the generator using some simpler node wrappers
# here.
def HandleGenExprInner(node):
    handler = map_node(node.expr)
    for qual in reversed(node.quals):
        assert isinstance(qual, ast.GenExprFor)
        for if_qual in qual.ifs:
            assert isinstance(if_qual, ast.GenExprIf)
            handler = HandleCompoundExpr([handler, map_node(if_qual.test)])
        handler = HandleCompoundExpr([handler, map_node(qual.assign)])
        handler = HandleNewScopeExpr(handler)
        handler = HandleCompoundExpr([handler, map_node(qual.iter)])
        # What is qual.is_outmost for?
    return handler


class HandleGlobal(Node):

    def assigned(self, var_set):
        pass

    def find_globals(self, var_set):
        var_set.update(self._node.names)

    def annotate(self, scope):
        pass


class HandleImport(Node):

    def _get_assigned(self):
        for module_path, as_name in self._node.names:
            if as_name is None:
                components = module_path.split(".")
                yield components[0]
            else:
                yield as_name

    def assigned(self, var_set):
        var_set.update(self._get_assigned())

    def find_globals(self, var_set):
        assert self._node.getChildNodes() == ()

    def annotate(self, scope):
        for var_name in self._get_assigned():
            scope.local_env.record(self._node, var_name, assigns=True,
                                   reads=False)


class HandleFromImport(Node):

    def _get_assigned(self):
        for attr_name, as_name in self._node.names:
            # Cannot track assignments when "from X import *" is used.
            if attr_name != "*":
                if as_name is None:
                    yield attr_name
                else:
                    yield as_name

    def assigned(self, var_set):
        var_set.update(self._get_assigned())

    def find_globals(self, var_set):
        assert self._node.getChildNodes() == ()

    def annotate(self, scope):
        for var_name in self._get_assigned():
            scope.local_env.record(self._node, var_name, assigns=True,
                                   reads=False)


# Boring AST nodes are those that do not affect variable binding.
class HandleBoring(Node):

    def assigned(self, var_set):
        for node in self._node.getChildNodes():
            map_node(node).assigned(var_set)

    def find_globals(self, var_set):
        for node in self._node.getChildNodes():
            map_node(node).find_globals(var_set)

    def annotate(self, scope):
        for node in self._node.getChildNodes():
            map_node(node).annotate(scope)


node_types = {
    "Name": HandleName,
    "AssName": HandleAssName,
    "AugAssign": HandleAugAssign,
    "Lambda": HandleLambda,
    "Function": HandleFunction,
    "Class": HandleClass,
    "GenExprInner": HandleGenExprInner,
    "Global": HandleGlobal,
    "Import": HandleImport,
    "From": HandleFromImport,
    }
for ty in ("Stmt", "Assign", "AssTuple", "AssList", "AssAttr",
           "Const", "Discard",
           "CallFunc", "Getattr", "Return", "Yield",
           "List", "Tuple", "Dict",
           "If", "While", "Break", "Continue", "Pass",
           "TryExcept", "TryFinally",
           "Add", "Sub", "Mul", "Div", "FloorDiv", "Mod", "Power", "Compare",
           "UnaryAdd", "UnarySub",
           "And", "Or", "Not",
           "Bitand", "Bitor", "Bitxor", "Invert", "LeftShift", "RightShift",
           "Subscript", "Slice",
           "Backquote",
           "Print", "Printnl",
           "Assert", "Raise",
           "Keyword", # Keyword arguments to functions.
           "Module", # Provides a place to put the top-level docstring.
           # "for" assigns but it contains an AssName node.
           # The same applies to list comprehensions.
           "For", "ListComp", "ListCompFor", "ListCompIf",
           # This is a wrapper node that does nothing.
           # GenExprInner is the interesting one, and looks like ListComp.
           "GenExpr"):
    assert ty not in node_types
    node_types[ty] = HandleBoring

# TODO: With, Ellipsis, Exec


def map_node(node):
    return node_types[node.__class__.__name__](node)


def find_assigned_from_handler(handler):
    var_set = set()
    handler.assigned(var_set)
    return var_set

def find_globals_from_handler(handler):
    var_set = set()
    handler.find_globals(var_set)
    return var_set

def find_assigned(node):
    return find_assigned_from_handler(map_node(node))

def find_globals(node):
    return find_globals_from_handler(map_node(node))


def annotate(node):
    global_vars = {}
    all_bindings = []
    env = Environ({}, global_vars, all_bindings)
    map_node(node).annotate(make_normal_scope(env))
    return global_vars, all_bindings


def iter_nodes(node):
    yield node
    for subnode in node.getChildNodes():
        for result in iter_nodes(subnode):
            yield result
