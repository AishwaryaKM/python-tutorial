
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
    "__name__", "__all__", "__version__",
    ])

def is_special_var(name):
    return (name not in allowed_vars and
            name.startswith("__") and name.endswith("__"))


def is_special_attr(name):
    return name.startswith("__") and name.endswith("__")


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
    return log


def main(args, stdout):
    for filename in args:
        tree = compiler.parseFile(filename)
        global_vars, bindings = varbindings.annotate(tree)
        log = check(tree, bindings)
        for error, node in log:
            line = linecache.getline(filename, node.lineno).strip()
            stdout.write("%s:%i: %s\n  %s\n"
                         % (filename, node.lineno, error, line))


if __name__ == "__main__":
    main(sys.argv[1:], sys.stdout)
