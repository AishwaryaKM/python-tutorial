
import os
import sys
import unittest

base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.join(base, "cappython"))
sys.path.insert(1, os.path.join(base, "pypy-dist"))

import parser
real_parser = parser
import myparser
sys.modules["parser"] = myparser
parser = myparser

from test_all import *

class ParserYieldTest(unittest.TestCase):

    def FAILING_test(self):
        cases = ["""\
def foo():
    yield
""", """\
def bar():
    yield 1
""", """\
def baz():
    yield 1, 2
"""]
        for snippet in cases:
            self.assertEquals(myparser.ast2tuple(myparser.suite(snippet)),
                              real_parser.ast2tuple(real_parser.suite(snippet)))
        
        

if __name__ == "__main__":
    import unittest
    unittest.main()
