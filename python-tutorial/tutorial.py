
from StringIO import StringIO
import cappython.safeeval as safeeval
import fakeparser as parser
import functools
import pypybits.transformer as transformer
import sourcecodegen
import symbol
import token
import traceback


def _replace_node(pattern, node_type, replacement):
    if pattern[0] == node_type:
        return replacement
    if type(pattern[1]) is tuple:
        replacements = list(_replace_node(t, node_type, replacement) 
                            for t in pattern[1:])
        # replacement of None requests that the node is dropped
        return tuple([pattern[0]] + list(r for r in replacements
                                         if r is not None))
    else:
        return pattern


def _find_nodes(tree, node_type):
    if tree[0] == node_type:
        yield tree
    if type(tree[1]) is tuple:
        for child in tree[1:]:
            for result in _find_nodes(child, node_type):
                yield result


def get1(items):
    items = list(items)
    assert len(items) == 1, items
    return items[0]


#TODO: Fix line_info in template
EXPR_TEMPLATE = get1(_find_nodes(parser.ast2tuple(parser.suite("""\
__repace_me__(__replace_me_too__)
"""), line_info=1), symbol.expr_stmt))


def convert_print_statments(parsed, name="__print__",
                            file="__print_file__",
                            comma="__print_comma__",
                            file_comma="__print_file_comma__"):
    func_name = name
    if type(parsed[1]) is tuple:
        if parsed[0] == symbol.print_stmt:
            names = {(False, False): name,
                     (True, False): file,
                     (False, True): comma,
                     (True, True): file_comma}
            if len(parsed) > 2 and parsed[2][0] == token.RIGHTSHIFT:
                has_file = True
                children = parsed[3:]
            else:
                has_file = False
                children = parsed[2:]
            args = []
            for index, child in enumerate(children):
                if index % 2 == 0:
                    args.append((symbol.argument, child))
                else:
                    assert child[0] == token.COMMA, child[0]
                    args.append(child)
            if len(args) == 0:
                has_comma = False
                arglist = None
            else:
                if len(args) % 2 == 0:
                    has_comma = True
                    args = args[:-1]
                else:
                    has_comma = False
                arglist = tuple([symbol.arglist] + args)
            name_node = (token.NAME, names[(has_file, has_comma)], 1)
            return _replace_node(_replace_node(EXPR_TEMPLATE, token.NAME,
                                               name_node), 
                                 symbol.arglist, arglist)
        return tuple([parsed[0]] + list(convert_print_statments(t, name) 
                                        for t in parsed[1:]))
    else:
        return parsed



def no_imports(name, fromlist):
    raise ImportError("You are not yet allowed to import anything: " + name)


def crazy_print(get_default_fh, fh, extra_comma, *args):
    # TODO: Not crazy enough yet
    assert fh is None, fh
    assert not extra_comma
    fh = get_default_fh()
    fh.write(" ".join(unicode(a).encode("utf-8") for a in args) + "\n")


def transforming_parser(code):
    assert type(code) is str
    print_stmt_tree = parser.ast2tuple(parser.suite(code), line_info=1)
    print_func_tree = convert_print_statments(print_stmt_tree)
    return transformer.Transformer().transform(print_func_tree)


def run_with_emulated_print(code):
    data = StringIO()
    env = safeeval.safe_environment()
    env.set_importer(no_imports)
    printer = functools.partial(crazy_print, lambda: data)
    env.bind("__print__", lambda *a: printer(None, False, *a))
    env.bind("__print_file__", lambda f, *a: printer(f, False, *a))
    env.bind("__print_comma__", lambda *a: printer(None, True, *a))
    env.bind("__print_file_comma__", lambda f, *a: printer(f, True, *a))
    parsed = transforming_parser(code)
    generated_code = sourcecodegen.generate_code(parsed)
    safeeval.safe_eval(generated_code, env)
    return data.getvalue().decode("utf-8")


def run_straight_cappython(code):
    data = StringIO()
    env = safeeval.safe_environment()
    env.set_importer(no_imports)
    def safe_write(string):
        data.write(unicode(string, encoding="ascii").encode("utf-8"))
    env.bind("write", safe_write)
    try:
        safeeval.safe_eval(code.encode("utf-8") + "\n", env)
    except Exception, e:
        return unicode(traceback.format_exc())
    return data.getvalue().decode("utf-8")

