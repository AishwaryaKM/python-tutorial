#!/usr/bin/env python

"""\
%prog [options] ACTION

Action "dev" builds the system and runs the development webserver
Action "push" builds the system and pushes it to the Google App Engine servers
"""

import contextlib
import optparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

def replace(source, destination):
    if not os.path.exists(os.path.dirname(destination)):
        os.makedirs(os.path.dirname(destination))
    if os.path.isdir(source):
        subprocess.check_call(["rsync", "-a", source.rstrip("/") + "/",
                               destination.rstrip("/") + "/"])
    else:
        subprocess.check_call(["rsync", source, destination])

def format(template, *args, **kwargs):
    assert len(args) == 0 or len(kwargs) == 0, (args, kwargs)
    if len(args) > 0:
        return template % args
    return template % kwargs

def _build(target_dir):
    assert not os.path.exists(target_dir), target_dir
    source_dir = os.path.dirname(os.path.abspath(__file__))
    fh = open(os.path.join(source_dir, "renames.py"))
    try:
        rename_data = fh.read()
    finally:
        fh.close()
    for rel_source, rel_dest in eval(rename_data):
        replace(os.path.abspath(os.path.join(source_dir, rel_source)), 
                os.path.abspath(os.path.join(target_dir, rel_dest)))

@contextlib.contextmanager
def mkdtemp(*args, **kwargs):
    temp_dir = tempfile.mkdtemp(*args, **kwargs)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)

@contextlib.contextmanager
def interruptable():
    try:
        yield
    except Exception:
        raise
    except: #KeyboardInterrupt, SystemExit, etc.
        pass

def run_development_server(sdk_path):
    with mkdtemp() as temp_dir:
        stage_dir = os.path.join(temp_dir, "staging")
        target_dir = os.path.join(temp_dir, "running")
        _build(stage_dir)
        subprocess.check_call(["rsync", "-a", stage_dir.rstrip("/") + "/",
                               target_dir.rstrip("/") + "/"])
        child = subprocess.Popen(
            ["python2.5", 
             os.path.join(sdk_path, "dev_appserver.py"),
             target_dir])
        try:
            with interruptable():
                while child.poll() is None:
                    shutil.rmtree(stage_dir)
                    try:
                        _build(stage_dir)
                    except Exception, e:
                        print "Build error.  Transient?", str(e)
                    else:
                        subprocess.check_call(["rsync", "-a", "-i",
                                               stage_dir.rstrip("/") + "/",
                                               target_dir.rstrip("/") + "/"])
                    time.sleep(1)
        finally:
            os.kill(child.pid, signal.SIGKILL)

def deploy_live(sdk_path):
    with mkdtemp() as temp_dir:
        target_dir = os.path.join(temp_dir, "python-tutorial")
        _build(target_dir)
        try:
            subprocess.check_call(["python2.5", 
                                   os.path.join(sdk_path, "appcfg.py"),
                                   "update", target_dir])
        except Exception:
            raise
        except:
            pass

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
