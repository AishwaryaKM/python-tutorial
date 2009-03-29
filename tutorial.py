
import parser
import token
import symbol


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


EXPR_TEMPLATE = get1(_find_nodes(parser.ast2tuple(parser.suite("""\
__repace_me__(__replace_me_too__)
""")), symbol.expr_stmt))

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
            name_node = (token.NAME, names[(has_file, has_comma)])
            return _replace_node(_replace_node(EXPR_TEMPLATE, token.NAME,
                                               name_node), 
                                 symbol.arglist, arglist)
        return tuple([parsed[0]] + list(convert_print_statments(t, name) 
                                        for t in parsed[1:]))
    else:
        return parsed
