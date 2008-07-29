
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


class Binding(object):

    def __init__(self, name, is_global):
        self.name = name
        self.is_global = is_global
        self.is_self_var = False

    def __repr__(self):
        return "<Binding 0x%x %r global=%s>" % (
            id(self), self.name, self.is_global)


class Environ(object):

    def __init__(self, env, bindings, global_vars):
        self._env = env
        self._bindings = bindings
        self._global_vars = global_vars

    def lookup(self, name):
        return self._env[name]

    def _get(self, name):
        if name in self._env:
            return self._env[name]
        else:
            if name not in self._global_vars:
                self._global_vars[name] = Binding(name, is_global=True)
            return self._global_vars[name]

    def record(self, node, name):
        node.binding = self._get(name)

    def bind(self, name):
        binding = Binding(name, is_global=False)
        env = self._env.copy()
        env[name] = binding
        self._bindings.append(binding)
        return Environ(env, self._bindings, self._global_vars)

    def set_global(self, name):
        # Could add to global_vars too
        env = self._env.copy()
        del env[name]
        return Environ(env, self._bindings, self._global_vars)


class Node(object):

    def __init__(self, node):
        self._node = node

    def assigned(self, var_set):
        raise NotImplementedError()

    def find_globals(self, var_set):
        raise NotImplementedError()

    # env is the environment that nodes get when evaluated,
    # but cenv is the environment that closures capture.
    # The two are only different in class scope.
    def annotate(self, env, cenv):
        raise NotImplementedError()

    def is_self_var(self):
        return False


class HandleName(Node):

    def assigned(self, var_set):
        pass

    def find_globals(self, var_set):
        pass

    def annotate(self, env, cenv):
        env.record(self._node, self._node.name)

    def is_self_var(self):
        return self._node.binding.is_self_var


class HandleAssName(Node):

    def assigned(self, var_set):
        assert self._node.flags == "OP_ASSIGN"
        var_set.add(self._node.name)

    def find_globals(self, var_set):
        pass

    def annotate(self, env, cenv):
        env.record(self._node, self._node.name)


class HandleAugAssign(Node):

    def assigned(self, var_set):
        assert isinstance(self._node.node, ast.Name)
        var_set.add(self._node.node.name)

    def find_globals(self, var_set):
        pass

    def annotate(self, env, cenv):
        for node in self._node.getChildNodes():
            map_node(node).annotate(env, cenv)


class HandleFunction(Node):

    def assigned(self, var_set):
        var_set.add(self._node.name)
        # Function starts new scope, so assignments in body are hidden

    def find_globals(self, var_set):
        # Function starts new scope, so global decls in body are hidden
        pass

    def annotate(self, env, cenv):
        env.record(self._node, self._node.name)
        for default in self._node.defaults:
            map_node(default).annotate(env, cenv)
        global_vars = find_globals(self._node.code)
        assigned_vars = find_assigned(self._node.code)
        for var in assigned_vars:
            cenv = cenv.bind(var)
        for var in global_vars:
            cenv = cenv.set_global(var)
        # TODO: pattern args
        for var in self._node.argnames:
            assert var not in global_vars
            cenv = cenv.bind(var)
        self._node.code.environ = cenv
        map_node(self._node.code).annotate(cenv, cenv)


class HandleClass(Node):

    def assigned(self, var_set):
        var_set.add(self._node.name)
        # No recurse

    def find_globals(self, var_set):
        # No recurse
        pass

    def annotate(self, env, cenv):
        env.record(self._node, self._node.name)
        for base in self._node.bases:
            map_node(base).annotate(env, cenv)
        # Classes have weird-assed scoping rules.
        # Classes do not behave according to lexical scope!
        # Assigned variables are not added to cenv.
        # Assigned variables' values default to those of their namesakes
        # in global (not enclosing) scope.
        env = cenv
        for var in find_assigned(self._node.code):
            # Approximation: introduces a new binding, but its value
            # defaults to the value in the global scope.
            env = env.bind(var)
        for var in find_globals(self._node.code):
            env = env.set_global(var)
        map_node(self._node.code).annotate(env, cenv)


class HandleGlobal(Node):

    def assigned(self, var_set):
        pass

    def find_globals(self, var_set):
        var_set.update(self._node.names)

    def annotate(self, env, cenv):
        pass


# Boring AST nodes are those that do not affect variable binding.
class HandleBoring(Node):

    def assigned(self, var_set):
        for node in self._node.getChildNodes():
            map_node(node).assigned(var_set)

    def find_globals(self, var_set):
        for node in self._node.getChildNodes():
            map_node(node).find_globals(var_set)

    def annotate(self, env, cenv):
        for node in self._node.getChildNodes():
            map_node(node).annotate(env, cenv)


node_types = {
    "Name": HandleName,
    "AssName": HandleAssName,
    "AugAssign": HandleAugAssign,
    "Function": HandleFunction,
    "Class": HandleClass,
    "Global": HandleGlobal,
    }
for ty in ("Stmt", "Assign", "AssTuple", "Const", "AssAttr", "Discard",
           "CallFunc", "Getattr", "Return", "Yield",
           "List", "Tuple", "Dict",
           "If", "While", "Break", "Continue", "Pass",
           "Add", "Sub", "Mul", "Div", "Mod", "Power", "Compare",
           "UnaryAdd", "UnarySub",
           "And", "Or", "Not",
           "Bitand", "Bitor", "Bitxor", "Invert", "LeftShift", "RightShift",
           "Subscript", "Slice",
           "Print", "Printnl"):
    assert ty not in node_types
    node_types[ty] = HandleBoring

# TODO: TryExcept, TryFinally, Lambda, With, For, Assert, comprehensions,
# Backquote, Ellipsis, Exec, FloorDiv, Import, Raise


def map_node(node):
    return node_types[node.__class__.__name__](node)


def find_assigned(node):
    var_set = set()
    map_node(node).assigned(var_set)
    return var_set

def find_globals(node):
    var_set = set()
    map_node(node).find_globals(var_set)
    return var_set


def annotate(node):
    bindings = []
    global_vars = {}
    env = Environ({}, bindings, global_vars)
    map_node(node).annotate(env, env)
    return set(global_vars.iterkeys())


def iter_nodes(node):
    yield node
    for subnode in node.getChildNodes():
        for result in iter_nodes(subnode):
            yield result
