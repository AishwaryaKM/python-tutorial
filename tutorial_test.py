import os
import sys
import subprocess
import unittest
import parser
import symbol
import token
import tempfile
import shutil
from pprint import pformat
from StringIO import StringIO
import safeeval2 as safeeval

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
        write_file(os.path.join(temp, "actual"), actual)
        write_file(os.path.join(temp, "expected"), expected)
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
                meld(pformat(namify(actual)), pformat(namify(expected)))
                raise


def run_with_emulated_print(code):
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


def run_with_real_print(code):
    child = subprocess.Popen([sys.executable, "-c", code], 
                             stdout=subprocess.PIPE)
    stdout, stderr = child.communicate()
    assert child.returncode == 0
    return stdout
    


class TestEmulatePrint(unittest.TestCase):

    def test(self):
        cases = [
"""\
print "hello, world"
""",
]
        for case in cases:
            actual = run_with_emulated_print(case)
            expected = run_with_real_print(case)
            self.assertEquals(actual, expected)


if __name__ == "__main__":
    unittest.main()
