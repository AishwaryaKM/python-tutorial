
import safeeval

evalfunc = safeeval.Evaluator(use_filename=True, warn_only=True).exec_code
loader = safeeval.ModuleLoader(["stdlib", "/usr/lib/python2.5"],
                               eval_func=evalfunc)
for name in ("sys", "time", "socket", "os", "tempfile", "dummy_thread",
             "SocketServer", "re", "string", "urlparse", "types",
             "traceback", "StringIO"):
    loader.add_module(name, __import__(name))
loader.load_file("example.py")
