
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

from compiler import ast
import compiler
import linecache
import sys

import varbindings


def find_all(node, node_type):
    got = []

    def recurse(node):
        if isinstance(node, node_type):
            got.append(node)
        for subnode in node.getChildNodes():
            recurse(subnode)

    recurse(node)
    return got


def find_attribute_assignments(tree):
    for node in find_all(tree, ast.AssAttr):
        yield node, node.expr, node.attrname
    for node in find_all(tree, ast.AugAssign):
        # In this lvalue context, Getattr is really Getattr + Setattr.
        if isinstance(node.node, ast.Getattr):
            yield node, node.node.expr, node.node.attrname


def is_private_attr(name):
    return (name.startswith("_") or
            name.startswith("func_") or
            name.startswith("im_") or
            name.startswith("gi_"))


allowed_vars = frozenset([
    # Method names
    "__init__",
    "__getitem__", "__setitem__", "__delitem__",
    "__contains__", "__len__", "__iter__",
    "__str__", "__repr__",
    "__add__", "__sub__", "__iadd__", "__isub__",
    # Global variables
    "__name__", "__all__", "__version__", "__debug__",
    ])

def is_special_var(name):
    return (name not in allowed_vars and
            name.startswith("__") and name.endswith("__"))


def is_special_attr(name):
    return name.startswith("__") and name.endswith("__")


def check_safesuper(tree, bindings, log):
    acceptable_uses = set()
    for call in find_all(tree, ast.CallFunc):
        if isinstance(call.node, ast.Name):
            binding = varbindings.get_only(call.node.bindings)
            if (binding.is_global and
                binding.name == "safesuper" and
                len(call.args) >= 1 and
                varbindings.map_node(call.args[0]).is_self_var()):
                acceptable_uses.add(call.node)
    for node in find_all(tree, ast.Name):
        binding = varbindings.get_only(node.bindings)
        if binding.name == "safesuper":
            if binding.is_global:
                if node not in acceptable_uses:
                    log.append(("Super", node))
            else:
                # Shadowing is not allowed.
                log.append(("SuperShadowed", node))


def check(tree, bindings):
    log = []
    for class_node in find_all(tree, ast.Class):
        for defn in class_node.code.nodes:
            if isinstance(defn, ast.Function):
                method_binding = varbindings.get_only(defn.bindings)
                if (defn.decorators is None and
                    not method_binding.is_read and
                    not method_binding.is_global and
                    len(defn.argnames) >= 1):
                    binding = defn.code.environ.lookup(defn.argnames[0])
                    if not binding.is_assigned:
                        binding.is_self_var = True
    for node, expr_node, attr_name in find_attribute_assignments(tree):
        if not varbindings.map_node(expr_node).is_self_var():
            log.append(("SetAttr", node))
        elif is_special_attr(attr_name):
            log.append(("SpecialAttr", node))
    for node in find_all(tree, ast.Getattr):
        if (not varbindings.map_node(node.expr).is_self_var() and
            is_private_attr(node.attrname)):
            log.append(("GetAttr", node))
        elif is_special_attr(node.attrname):
            log.append(("SpecialAttr", node))
    for node in find_all(tree, (ast.Print, ast.Printnl)):
        log.append(("Print", node))
    for node in find_all(tree, ast.Exec):
        log.append(("Exec", node))
    for node in find_all(tree, ast.From):
        for attr_name, as_name in node.names:
            if attr_name == "*":
                log.append(("BlanketImport", node))
    for binding in bindings:
        if is_special_var(binding.name):
            assert len(binding.references) > 0
            for var_ref in binding.references:
                log.append(("SpecialVar", var_ref.node))
    check_safesuper(tree, bindings, log)
    return log


class ContextFinder(object):

    def __init__(self, tree):
        self._tree = tree
        self._parents = None

    def _make_parent_map(self):
        parents = {}
        def recurse(node, parent):
            parents[node] = parent
            for subnode in node.getChildNodes():
                recurse(subnode, node)
        recurse(self._tree, None)
        return parents

    def get_context_names(self, node):
        if self._parents is None:
            self._parents = self._make_parent_map()
        while node is not None:
            if isinstance(node, (ast.Function, ast.Class)):
                yield node.name
            node = self._parents[node]

    def get_context_string(self, node):
        names = list(self.get_context_names(node))
        if len(names) == 0:
            # <module> is what Python tracebacks contain.
            return "<module>"
        else:
            # "." is not pedantically correct for naming nested functions.
            return ".".join(reversed(names))


def format_log(log, tree, get_source_line, filename):
    context = ContextFinder(tree)
    if filename is None:
        prefix = "line "
    else:
        prefix = filename + ":"
    for error, node in sorted(log, key=lambda (error, node): node.lineno):
        line = get_source_line(node.lineno).strip()
        where = context.get_context_string(node)
        yield "%s%i: %s, in %s\n  %s" % (prefix, node.lineno, error,
                                         where, line)


def main(args, stdout):
    for filename in args:
        tree = compiler.parseFile(filename)
        global_vars, bindings = varbindings.annotate(tree)
        log = check(tree, bindings)
        def get_line(lineno):
            return linecache.getline(filename, lineno)
        for message in format_log(log, tree, get_line, filename):
            stdout.write(message + "\n")


if __name__ == "__main__":
    main(sys.argv[1:], sys.stdout)
