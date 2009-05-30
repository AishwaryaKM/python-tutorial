from pythonparse2 import make_pyparser
from tuplebuilder2 import TupleBuilder
import symbol
import token

parser = make_pyparser("native")
symbol_lookup = dict((num, getattr(symbol, name)) 
                     for name, num in parser.symbols.iteritems()
                     if not name.startswith(":"))
token_lookup = dict((num, getattr(token, name)) 
                    for name, num in parser.tokens.iteritems()
                    if name not in ("NULLTOKEN", "COMMENT", "NL"))

def pypy_parse(source, mode='exec', lineno=False):
    builder = TupleBuilder(parser)
    parser.parse_source(source, mode, builder)
    return builder.stack[-1].as_tuple(lineno)

int_map = {}
int_map.update(symbol_lookup)
int_map.update(token_lookup)

def suite(source):
    return source

def _renumber(a):
    return int_map[a]

def _renumber_tree(a):
    # The parser from pypy seems to allocate different integer
    # constants to the different node types.  Look up the correct
    # numbers (expected by the compiler package) by name.
    mapped = _renumber(a[0])
    if type(a[1]) is tuple:
        rest = list(_renumber_tree(x) for x in a[1:])
    else:
        rest = list(a[1:])
    # It looks like the pypy parser has trouble with yield as an
    # expression at the moment.  This part of the grammar file differs
    # from the cpython one and changing it back causes a SyntaxError.
    # Since the return value from yield is rarely used anyway, for now
    # we just add in the extra level to the tree to conform to the
    # compiler package's expectations.
    if symbol.sym_name.get(mapped) == "yield_stmt":
        if symbol.sym_name.get(rest[0][0]) != "yield_expr":
            rest = [tuple([symbol.yield_expr] + rest)]
    return tuple([mapped] + rest)

def ast2tuple(source, line_info=False):
    r = pypy_parse(source, lineno=line_info)
    r2 = _renumber_tree(r)
    return r2
