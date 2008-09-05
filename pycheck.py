
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


def is_private_attr(name):
    return (name.startswith("_") or
            name.startswith("func_") or
            name.startswith("im_") or
            name.startswith("gi_"))


def check(tree):
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
    for node in find_all(tree, ast.AssAttr):
        if not varbindings.map_node(node.expr).is_self_var():
            log.append(("SetAttr", node))
    for node in find_all(tree, ast.AugAssign):
        # In this lvalue context, Getattr is really Getattr + Setattr.
        if isinstance(node.node, ast.Getattr):
            if not varbindings.map_node(node.node.expr).is_self_var():
                log.append(("SetAttr", node))
    for node in find_all(tree, ast.Getattr):
        if (not varbindings.map_node(node.expr).is_self_var() and
            is_private_attr(node.attrname)):
            log.append(("GetAttr", node))
    for node in find_all(tree, (ast.Print, ast.Printnl)):
        log.append(("Print", node))
    for node in find_all(tree, ast.From):
        for attr_name, as_name in node.names:
            if attr_name == "*":
                log.append(("BlanketImport", node))
    return log


def main(args, stdout):
    for filename in args:
        tree = compiler.parseFile(filename)
        varbindings.annotate(tree)
        log = check(tree)
        for error, node in log:
            line = linecache.getline(filename, node.lineno).strip()
            stdout.write("%s:%i: %s\n  %s\n"
                         % (filename, node.lineno, error, line))


if __name__ == "__main__":
    main(sys.argv[1:], sys.stdout)
