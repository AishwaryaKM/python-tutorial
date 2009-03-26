
# Hack the interpreter around a bit.  Is there a neater way of doing this?

import os
import sys
import types

base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.join(base, "cappython"))
sys.path.insert(1, os.path.join(base, "pypy-dist"))
os.linesep = "\n"

# pypy's parser seems to import the cpython parser, hopefully it does
# not use it
# sys.modules["parser"] = types.ModuleType("parser")
# missing = ["parser", "py.compat.subprocess", "py.compat.doctest",
#            "py.compat.optparse", "py.compat.textwrap"]
missing = ["parser", "py", "py.compat.subprocess", "py.path",
           "py.path.local", "py.io", "py.__.io.terminalwriter"]
for name in missing:
    sys.modules[name] = types.ModuleType(name)
sys.modules["py"].path = sys.modules["py.path"]
sys.modules["py.path"].local = sys.modules["py.path.local"]
# import py.compat.subprocess
# import py.compat.doctest
# import py.compat.optparse
# import py.compat.textwrap
import pypy.rlib.streamio
class FakeStream(object):
    def __init__(self, data):
        self._data = data
    def readall(self):
        return self._data
    def close(self):
        pass
def fake_open_file_as_stream(path, *args, **kwargs):
    fh = open(path)
    try:
        return FakeStream(fh.read())
    finally:
        fh.close()
pypy.rlib.streamio.open_file_as_stream = fake_open_file_as_stream
import myparser as parser
sys.modules["parser"] = parser
#/Hack

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
import pycheck
import cgi
import functools
import os


class UserTag(db.Model):
    user = db.UserProperty()
    tag = db.StringProperty()


def has_tag(tag):
    user = users.get_current_user()
    user_tags = db.GqlQuery("SELECT * FROM UserTag "
                            "WHERE user = :1 AND tag = :2", user, tag)
    result = users.is_current_user_admin() or user_tags.count() > 0
    if result and user_tags.count() == 0:
        assert users.is_current_user_admin()
        db.put(UserTag(user=user, tag=tag))
    return result

    
def requires_tag(tag):
    def decorator(func):
        @functools.wraps(func)
        def handler(self, *args, **kwargs):
            if has_tag(tag):
                return func(self, *args, **kwargs)
            else:
                if users.get_current_user():
                    url = users.create_logout_url(self.request.uri)
                    url_linktext = 'Logout'
                else:
                    url = users.create_login_url(self.request.uri)
                    url_linktext = 'Login'
                template_values = {
                    'url': url,
                    'url_linktext': url_linktext,
                    }
                path = os.path.join(os.path.dirname(__file__), 'index.html')
                self.response.out.write(template.render(path, template_values))
        return handler
    return decorator


class MainPage(webapp.RequestHandler):
    
    @requires_tag("user")
    def get(self):
        if users.get_current_user():
          url = users.create_logout_url(self.request.uri)
          url_linktext = 'Logout'
        else:
          url = users.create_login_url(self.request.uri)
          url_linktext = 'Login'
        template_values = {
          'url': url,
          'url_linktext': url_linktext,
          }
        path = os.path.join(os.path.dirname(__file__), 'repl.html')
        self.response.out.write(template.render(path, template_values))


application = webapp.WSGIApplication([('/', MainPage),],
                                     debug=True)


def main():
    run_wsgi_app(application)


if __name__ == "__main__":
  main()
