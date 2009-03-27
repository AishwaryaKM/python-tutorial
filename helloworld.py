

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
# import pycheck
import cgi
import functools
import os
import sys
import logging

import pycheck2 as pycheck
import transformer2 as transformer
import varbindings2 as varbindings
import linecache

import simplejson


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


@requires_tag("validate")
def cappython_validate(string):
    tree = transformer.parse(string.encode("utf-8") + "\n")
    global_vars, bindings = varbindings.annotate(tree)
    log = pycheck.check(tree, bindings)
    def get_line(lineno):
        return "<getting of line %s not yet implemented>" % (lineno,)
    return len(log) == 0
#     for message in pycheck.format_log(log, tree, get_line, filename):
#         stdout.write(message + "\n")
#     return False

    
class WebService(webapp.RequestHandler):

    @requires_tag("user")
    def post(self):
        string = self.request.body.decode("utf-8")
        json = simplejson.loads(string)
        assert json[u"method"] == u"validate", json[u"method"]
        if cappython_validate(json[u"params"][0]):
            response_data = {u"result": u"passed"}
        else:
            response_data = {u"result": u"failed"}
        self.response.headers.add_header("Content-Type", 
                                         "application/json; charser=utf-8")
        self.response.out.write(simplejson.dumps(response_data).encode("utf-8"))


application = webapp.WSGIApplication([('/', MainPage),
                                      ("/ws", WebService)],
                                     debug=True)


def main():
    run_wsgi_app(application)


if __name__ == "__main__":
  main()
