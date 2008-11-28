import unittest
import doctest
import inspect
import textwrap

OPTIONFLAGS = (doctest.ELLIPSIS |
               doctest.NORMALIZE_WHITESPACE)

from compiler import ast
from compiler import parse
from compiler import pycodegen

from sourcecodegen.generation import ModuleSourceCodeGenerator

def fix_tree(node):
    if isinstance(node, (
        ast.Module, ast.Class, ast.Function, ast.GenExpr, ast.Lambda)):
        node.filename = '<string>' # workaround for bug in pycodegen
    map(fix_tree, node.getChildNodes())
    return node

def verify_source(source):
    tree = fix_tree(parse(source, 'exec'))
    code = pycodegen.ModuleCodeGenerator(tree).getCode()
    generator = ModuleSourceCodeGenerator(tree)
    source = generator.getSourceCode()
    tree = fix_tree(parse(source, 'exec'))
    if code.co_code != pycodegen.ModuleCodeGenerator(tree).getCode().co_code:
        return source

def verify(func):
    return lambda suite: suite.assertEqual(verify_source(
        textwrap.dedent("\n".join(
        inspect.getsource(func).split('\n')[2:]))), None)

class TestSourceCodeGeneration(unittest.TestCase):
    """The ``verify`` decorator is used to create a test-case out of
    simple functions. The objective is to verify correct source-code
    generation, not actual evaluation."""

    @verify
    def testModule(self):
        """Module doc-string."""
        
    @verify
    def testAssignment(self):
        foo = bar
        foo = bar = moo
        foo, bar = bar
        foo, bar = foo, bar
        foo, (bar, moo) = foo
        ((foo, bar), foo) = moo

    @verify
    def testArithmeticAssignment(self):
        foo -= bar
        foo += bar
        foo %= bar
        foo /= bar
        foo **= bar
                
    @verify
    def testConditions(self):
        if foo and bar:
            pass
        elif boo:
            pass
        else:
            pass

    @verify
    def testFunctions(self):
        def foo(bar):
            pass

        def foo(bar, *args):
            pass

        def foo(bar, *args, **kwargs):
            pass

        def foo(foo=None):
            pass

        def foo(bar, foo=None, *args, **kwargs):
            pass

        def foo(bar, boo, foo=None, moo=42, *args, **kwargs):
            pass

    @verify
    def testDecorators(self):
        @foo
        @bar(boo)
        def bar(foo):
            pass

    @verify
    def testCallFunc(self):
        foo(bar)
        foo(bar=None)
        foo(bar, moo=None)
        foo(boo, *args)
        foo(boo, *args, **kwargs)

    @verify
    def testDel(self):
        del foo
        del foo, bar

    @verify
    def testListComprehensions(self):
        [x for x in xs]
        [x for x in xs if x]
        [x for x in xs if x == y]
        [x*y for x in xs for y in ys]
        
    @verify
    def testGeneratorComprehensions(self):
        (x for x in xs)
        (x for x in xs if x)
        (x for x in xs if x == y)
        (x*y for x in xs for x in xs for y in ys)

    @verify
    def testImports(self):
        import foo
        import foo.bar
        from foo import bar
        from foo.bar import foo, bar

    @verify
    def testReturn(self):
        return foo, bar

    @verify
    def testWhile(self):
        while True: # don't try this at home
            pass
        while False:
            pass
        else:
            pass

    @verify
    def testTryExcept(self):
        try:
            pass
        except Exception, e:
            pass
        except:
            pass

    @verify
    def testTryFinally(self):
        try:
            pass
        except:
            pass
        else:
            pass
        finally:
            pass

    @verify
    def testClasses(self):
        class foo:
            pass

        class foo(moo, boo):
            pass

        class foo(moo, boo):
            """this is foo."""

    @verify
    def testLambda(self):
        foo = lambda: bar
        bar = lambda foo: bar
        bar = lambda foo, bar: bar
        bar = lambda (foo, bar): bar

    @verify
    def testGetAttr(self):
        foo.bar

    @verify
    def testGetItem(self):
        foo['bar']

    @verify
    def testSetAttr(self):
        foo.bar = moo

    @verify
    def testSetItem(self):
        foo['bar'] = moo

    @verify
    def testSlicing(self):
        foo[:]
        foo[1:]
        foo[:2]
        foo[1:2:3]

    @verify
    def testAssert(self):
        assert foo
        
    @verify
    def testExec(self):
        exec foo
        exec foo in bar
        exec foo in foo, bar

    @verify
    def testSemicolon(self):
        foo; bar

    @verify
    def testPrint(self):
        print foo
        print foo, bar
        print "Hello %s" % bar
        print >> foo, bar
        
    @verify
    def testRaise(self):
        raise foo            

    @verify
    def testArithmetic(self):
        bar + foo
        bar - foo
        bar * foo
        bar ** foo
        bar % foo
        bar / foo
        bar << foo
        bar >> foo

    @verify
    def testTuples(self):
        (a, b, c)

    @verify
    def testLists(self):
        [a, b, c]

    @verify
    def testDicts(self):
        {'a': a, 'b': b, 'c': c}

    @verify
    def testComparisons(self):
        foo < bar
        foo > bar
        foo == bar
        foo != bar
        foo >= bar
        foo <= bar

    @verify
    def testLogicalOperators(self):
        foo | bar & bar ^ foo
        ~ bar
        ~ (foo or bar)
    @verify
    def testOperators(self):
        not foo
        bar or foo
        not (foo or bar)
        
    @verify
    def testFormatString(self):
        foo % (bar, moo)
        foo % (bar or foo)
        foo % (bar and foo)
        
    @verify
    def testLoop(self):
        for foo in bar:
            pass
        else:
            pass
        for foo, (bar, moo) in boo:
            pass

    @verify
    def testYield(self):
        yield foo

    @verify
    def testUnary(self):
        +foo
        -bar
        
