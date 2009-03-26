# import sys
# from pypy.interpreter.error import OperationError, debug_print
# import pypy.interpreter.pyparser.pythonparse

# from pypy.interpreter.mixedmodule import MixedModule 

# # Forward imports so they run at startup time
# import pypy.module.recparser
# import pypy.interpreter.pyparser.pythonlexer
# import pypy.interpreter.pyparser.pythonparse
# import pypy.interpreter.pycompiler
# import pypy.interpreter.pyparser.test.fakes

# class MyFakeSpace(pypy.interpreter.pyparser.test.fakes.FakeSpace):
#     def newdict(self, track_builtin_shadowing=True):
#         return dict()
#     def setitem(self, d, k, v):
#         d[k] = v
#     def new_interned_str(self, str):
#         return str


# class BringToMySpace(object):

#     def __init__(self, interp_level):
#         self._i = interp_level

#     def __getattr__(self, attr):
#         return BringToMySpace(self._i.get(attr))

#     def __call__(self, *args, **kwargs):
#         print dir(self._i)
#         return BringToMySpace(self._i.call_obj_args(args, kwargs))


# space = MyFakeSpace()
# from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
# space = ObjSpace()
# from pypy.objspace.std import StdObjSpace
# space = StdObjSpace()
# from pypy.objspace.fake import FakeObjSpace
# # space = FakeObjSpace()
# p = pypy.module.recparser.Module(space, space.wrap("parser"))
# from pypy.interpreter.gateway import interp2app, applevel
# # sys.modules["parser"] = BringToMySpace(p)

# print p, dir(p)

# def suite(source):
#     return source
# #     return space.call(p.get("suite"), space.wrap((source,)), space.wrap({}))

# def st2tuple(source, line_info=None):
#     return
# #     return space.unwrap(space.call(p.get("st2tuple", st, {})))

# ast2tuple = st2tuple



import sys
# sys.modules["parser"] = NotImplemented
import types
import parser

if True:
#     from pypy.interpreter.pyparser.pythonutil import pypy_parse

    from pypy.interpreter.pyparser.pythonparse import PythonParser, make_pyparser
    from pypy.interpreter.pyparser.tuplebuilder import TupleBuilder
    parser = make_pyparser('2.5')
    import symbol
    import token
#     print parser.tokens ; import sys ; sys.exit(1)
    symbol_lookup = dict((num, getattr(symbol, name)) 
                         for name, num in parser.symbols.iteritems()
                         if not name.startswith(":"))
#     assert set(symbol.sym_name.keys()) == set(symbol_lookup.values())
    tokens_by_name = dict((name, value) for value, name 
                          in token.tok_name.iteritems())
    token_lookup = dict((num, tokens_by_name[name]) 
                        for name, num in parser.tokens.iteritems()
                        if name not in ("NULLTOKEN",))
#     print set(token.tok_name.keys())
#     print set(token_lookup.values())
#     print set(token.tok_name.keys()) - set(token_lookup.values())
#     print set(token_lookup.values()) - set(token.tok_name.keys())
#     print list(token.tok_name[x] for x in set(token.tok_name.keys()) - set(token_lookup.values()))
#     assert set(token.tok_name.keys()) == set(token_lookup.values())

    def pypy_parse(source, mode='exec', lineno=False):
        # parser = build_parser_for_version("2.4", PythonParser())
#         parser = make_pyparser('stable')
        builder = TupleBuilder(parser)
        parser.parse_source(source, mode, builder)
        return builder.stack[-1].as_tuple(lineno)

    int_map = {}
    int_map.update(symbol_lookup)
    int_map.update(token_lookup)
#     int_map = {
#         56: 267,
#         58: 257,
#         59: 266,
#         61: 326,
#         73: 268,
#         74: 269,
#         71: 303,
#         96: 309,
#         105: 304,
#         108: 305,
#         109: 306,
#         110: 307,
#         112: 310,
#         113: 311,
#         114: 312,
#         115: 313,
#         116: 314,
#         117: 315,
#         118: 316,
#         119: 317,
#         120: 321,
#         }

    def suite(source):
        return source

    def _renumber(a):
        return int_map[a]
#         if a <= 23:
#             return a
#         else:
#             return int_map[a]
    
    def _renumber_tree(a):
        mapped = _renumber(a[0])
        # It looks like pypy's parser does not yet support yield as an
        # expression.
        if type(a[1]) is tuple:
            rest = list(_renumber_tree(x) for x in a[1:])
        else:
            rest = list(a[1:])
        if symbol.sym_name.get(mapped) == "yield_stmt":
            if symbol.sym_name.get(rest[0][0]) != "yield_expr":
                rest = [tuple([symbol.yield_expr] + rest)]
        return tuple([mapped] + rest)
#         return tuple([int_map.get(a[0], a[0])] + list(map(_renumber, a[1:])))

    def ast2tuple(source, line_info=False):
        r = pypy_parse(source, lineno=line_info)
#         print r
        r2 = _renumber_tree(r)
#         print r2
        return r2

else:
    def suite(source):
        r = parser.suite(source)
        return r

    def ast2tuple(source, line_info=False):
        r = parser.ast2tuple(source, line_info)
#         print r
        return r
