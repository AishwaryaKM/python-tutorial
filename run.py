#!/usr/bin/env python

"""\
%prog [options] ACTION

Action "dev" builds the system and runs the development webserver
Action "push" builds the system and pushes it to the Google App Engine servers
"""

import optparse
import os
import shutil
import subprocess
import sys
import tempfile

def format(template, *args, **kwargs):
    assert len(args) == 0 or len(kwargs) == 0, (args, kwargs)
    if len(args) > 0:
        return template % args
    return template % kwargs

def _build(target_dir):
    assert not os.path.exists(target_dir), target_dir
    source_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(target_dir)

def run_development_server(sdk_path):
    temp_dir = tempfile.mkdtemp(prefix="python-tutorial.tmp.")
    try:
        target_dir = os.path.join(temp_dir, "python-tutorial")
        _build(target_dir)
        try:
            subprocess.check_call(["python", os.path.join(sdk_path, 
                                                          "dev_appserver.py"),
                                   target_dir])
        except Exception:
            raise
        except:
            pass
    finally:
        shutil.rmtree(temp_dir)

def deploy_live(sdk_path):
    raise NotImplementedError(deploy_live)

def main(prog, argv):
    parser = optparse.OptionParser(__doc__, prog=prog)
    parser.add_option("--sdk", dest="sdk")
    options, args = parser.parse_args(argv)
    if len(args) == 0:
        parser.error("Missing: ACTION")
    action = args.pop(0)
    if len(args) > 0:
        parser.error(format("Unexpected: %r", args))
    actions = {"dev": run_development_server,
               "push": deploy_live}
    if options.sdk is None:
        sdk_path = os.path.join(os.path.expanduser("~"), "Desktop",
                                "google_appengine")
    else:
        sdk_path = options.sdk
    func = actions.get(action)
    if func is None:
        parser.error(format("Action %r not in %r", action, 
                            list(sorted(actions.keys()))))
    return func(sdk_path)

if __name__ == "__main__":
    sys.exit(main(sys.argv[0], sys.argv[1:]))
