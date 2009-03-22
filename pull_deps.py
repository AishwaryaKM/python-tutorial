"""\
%prog [options]
"""

import optparse
import os
import subprocess
import sys


def main(prog, argv):
    parser = optparse.OptionParser(__doc__, prog=prog)
    options, args = parser.parse_args(argv)
    if len(args) > 0:
        parser.error("Unexpected: %r" % (args,))
    base = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(base, "cappython")
    subprocess.check_call(
        ["bzr", "branch", "lp:~mrs/cappython/experimental", dest])
    subprocess.check_call(["svn", "co", "http://codespeak.net/svn/pypy/dist",
                           os.path.join(base, "pypy-dist")])


if __name__ == "__main__":
    sys.exit(main(sys.argv[0], sys.argv[1:]))
