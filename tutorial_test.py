import os
import subprocess
import unittest
import parser
import symbol
import token
import tempfile
import shutil
from pprint import pformat

import tutorial

to_name = {}
to_name.update(symbol.sym_name)
to_name.update(token.tok_name)


def namify(tree):
    if type(tree) is tuple:
        return tuple([to_name[tree[0]]] + list(namify(x) for x in tree[1:]))
    else:
        return tree

def write_file(path, data):
    fh = open(path, "w")
    try:
        fh.write(data)
    finally:
        fh.close()


def meld(actual, expected):
    temp = tempfile.mkdtemp(prefix="tutorial-test--")
    try:
        write_file(os.path.join(temp, "actual"), pformat(namify(actual)))
        write_file(os.path.join(temp, "expected"), pformat(namify(expected)))
        subprocess.check_call(["meld", "actual", "expected"], cwd=temp)
    finally:
        shutil.rmtree(temp)
    

class TestTransformPrintStatement(unittest.TestCase):

    def test(self):
        cases = [("""\
print
""", """\
__print__()
"""),
("""\
print ''
""", """\
__print__('')
"""),
("""\
print '',
""", """\
__print_comma__('')
"""),
("""\
print 'hello'
""", """\
__print__('hello')
"""),
("""\
print>>fh, 'hello'
""", """\
__print_file__(fh, 'hello')
"""),
("""\
print>>fh, 'comma',
""", """\
__print_file_comma__(fh, 'comma')
"""),
("""\
print a
""", """\
__print__(a)
"""),
("""\
print a, 1, repr(z)
""", """\
__print__(a, 1, repr(z))
"""),
                 ]
        for before, after in cases:
            before_parsed = parser.ast2tuple(parser.suite(before))
            expected = parser.ast2tuple(parser.suite(after))
            actual = tutorial.convert_print_statments(before_parsed)
            try:
                self.assertEquals(actual, expected)
            except:
                print "BEFORE", before.strip()
                print "TEMPLATE", tutorial.EXPR_TEMPLATE
                print "AFTER", after.strip()
                print "PARSED", before_parsed
                print "EXPECTED", expected
                print "ACTUAL", actual
                meld(actual, expected)
                raise


if __name__ == "__main__":
    unittest.main()
