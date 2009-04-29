
import types

import safeeval


evalfunc = safeeval.Evaluator(use_filename=True, warn_only=False).exec_code
loader = safeeval.ModuleLoader(["stdlib", "/usr/lib/python2.5"],
                               eval_func=evalfunc)

def tame(module, attrs):
    m = types.ModuleType("__module__")
    for attr in attrs:
        setattr(m, attr, getattr(module, attr))
    return m

taming = {
    "os": ["name", "environ"],
    "re": ["compile"],
    "string": [],
    "sys": ["version", "platform", "stdout", "stderr", "exc_info"],
    "tempfile": [],
    "time": ["time", "localtime", "gmtime"],
    "types": ["IntType", "LongType", "FloatType", "BooleanType",
              "StringType", "TupleType", "ListType", "DictType"],
    }

for module_name, attrs in taming.iteritems():
    loader.add_module(module_name, tame(__import__(module_name), attrs))
for name in ("socket", "dummy_thread", "SocketServer", "urlparse", "traceback"):
    loader.add_module(name, __import__(name))
loader.load_file("example.py")
