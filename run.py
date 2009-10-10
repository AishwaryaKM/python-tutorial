#!/usr/bin/env python

"""\
%prog [options] ACTION

Action "dev" builds the system and runs the development webserver
Action "push" builds the system and pushes it to the Google App Engine servers
"""

from lxml import etree
import contextlib
import optparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import yaml

def replace(source, destination):
    if not os.path.exists(os.path.dirname(destination)):
        os.makedirs(os.path.dirname(destination))
    if os.path.isdir(source):
        subprocess.check_call(["rsync", "-q", "-a", source.rstrip("/") + "/",
                               destination.rstrip("/") + "/"])
    else:
        subprocess.check_call(["rsync", "-q", source, destination])

def get1(items):
    items = list(items)
    assert len(items) == 1, items
    return items[0]

def format(template, *args, **kwargs):
    assert len(args) == 0 or len(kwargs) == 0, (args, kwargs)
    if len(args) > 0:
        return template % args
    return template % kwargs

def read_file(path):
    fh = open(path, "rb")
    try:
        return fh.read()
    finally:
        fh.close()

def write_file(path, data):
    fh = open(path, "wb")
    try:
        fh.write(data)
    finally:
        fh.close()

def _build_python(target_dir):
    assert not os.path.exists(target_dir), target_dir
    source_dir = os.path.dirname(os.path.abspath(__file__))
    rename_data = read_file(os.path.join(source_dir, "renames.py"))
    for rel_source, rel_dest in eval(rename_data):
        replace(os.path.abspath(os.path.join(source_dir, rel_source)), 
                os.path.abspath(os.path.join(target_dir, rel_dest)))

def _build_java(target_dir, sdk_path):
    assert not os.path.exists(target_dir), target_dir
    with mkdtemp() as temp_dir:
        python_build_dir = os.path.join(temp_dir, "python_build")
        _build_python(python_build_dir)
        source_dir = os.path.dirname(os.path.abspath(__file__))
        app_yaml = get1(
            yaml.load_all(
                read_file(os.path.join(python_build_dir, "app.yaml"))))
        java_dir = os.path.join(source_dir, "java-environment")
        replace(java_dir, target_dir)
        replace(os.path.join(python_build_dir, "static"),
                os.path.join(target_dir, "war", "static"))
        tutorial_dir = os.path.join(
            target_dir, "war", "WEB-INF", "python-tutorial")
        replace(os.path.join(python_build_dir), tutorial_dir)
        shutil.rmtree(os.path.join(tutorial_dir, "static"))
        build_xml_path = os.path.join(target_dir, "build.xml")
        build_xml = etree.fromstring(read_file(build_xml_path))
        sdk_prop = get1(build_xml.xpath(".//property[@name = 'sdk.dir']"))
        sdk_prop.attrib["location"] = sdk_path
        write_file(build_xml_path, etree.tostring(build_xml))
        appengine_xml_path = os.path.join(target_dir, "war", "WEB-INF",
                                          "appengine-web.xml")
        appengine_xml = etree.fromstring(read_file(appengine_xml_path))
        NSMAP = {"gae": "http://appengine.google.com/ns/1.0"}
        get1(
            appengine_xml.xpath(
                ".//gae:application", 
                namespaces=NSMAP)).text = str(app_yaml["application"])
        get1(
            appengine_xml.xpath(
                ".//gae:version", 
                namespaces=NSMAP)).text = str(app_yaml["version"])
        write_file(appengine_xml_path, etree.tostring(appengine_xml))

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

def _run_development_server(build_func, dev_appserver):
    with mkdtemp() as temp_dir:
        stage_dir = os.path.join(temp_dir, "staging")
        target_dir = os.path.join(temp_dir, "running")
        build_func(stage_dir)
        subprocess.check_call(["rsync", "-q", "-a", 
                               stage_dir.rstrip("/") + "/",
                               target_dir.rstrip("/") + "/"])
        child = subprocess.Popen(dev_appserver + [target_dir])
        try:
            with interruptable():
                while child.poll() is None:
                    shutil.rmtree(stage_dir)
                    try:
                        build_func(stage_dir)
                    except Exception, e:
                        print "Build error.  Transient?", str(e)
                    else:
                        subprocess.check_call(["rsync", "-r", "-i", "-c",
                                               stage_dir.rstrip("/") + "/",
                                               target_dir.rstrip("/") + "/"])
                    time.sleep(1)
        finally:
            os.kill(child.pid, signal.SIGKILL)

def run_development_server_python(sdk_path):
    _run_development_server(
        _build_python, 
        ["python2.5", os.path.join(sdk_path, "dev_appserver.py")])

def run_development_server_java(sdk_path):
    _run_development_server(
        lambda a: _build_java(a, sdk_path),
        ["sh", "-c", 'cd "$1" && ant runserver', "-"])

def deploy_live_python(sdk_path):
    with mkdtemp() as temp_dir:
        target_dir = os.path.join(temp_dir, "python-tutorial")
        _build_python(target_dir)
        subprocess.check_call(["python2.5", 
                               os.path.join(sdk_path, "appcfg.py"),
                               "update", target_dir])

def main(prog, argv):
    parser = optparse.OptionParser(__doc__, prog=prog)
    parser.add_option("--sdk", dest="sdk")
    parser.add_option("--java", dest="platform", const="java",
                      default="python", action="store_const")
    options, args = parser.parse_args(argv)
    if len(args) == 0:
        parser.error("Missing: ACTION")
    action = args.pop(0)
    if len(args) > 0:
        parser.error(format("Unexpected: %r", args))
    if options.platform == "java":
        actions = {"dev": run_development_server_java,
                   "push": deploy_live_python}
        default_sdk = os.path.join(os.path.expanduser("~"), "Desktop",
                                   "appengine-java-sdk")
    elif options.platform == "python":
        actions = {"dev": run_development_server_python,
                   "push": deploy_live_python}
        default_sdk = os.path.join(os.path.expanduser("~"), "Desktop",
                                   "google_appengine")
    else:
        raise NotImplementedError(options.platform)
    if options.sdk is None:
        sdk_path = default_sdk
    else:
        sdk_path = options.sdk
    func = actions.get(action)
    if func is None:
        parser.error(format("Action %r not in %r", action, 
                            list(sorted(actions.keys()))))
    return func(sdk_path)

if __name__ == "__main__":
    sys.exit(main(sys.argv[0], sys.argv[1:]))
