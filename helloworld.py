

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
import cgi
import functools
import os
import sys
import logging

import pycheck2 as pycheck
import transformer2 as transformer
import varbindings2 as varbindings
import linecache
import safeeval2 as safeeval
import traceback

import simplejson

from StringIO import StringIO


class UserTag(db.Model):
    user = db.UserProperty()
    tag = db.StringProperty()


def add_seen_tag():
    user = users.get_current_user()
    if not user:
        return
    seen_tags = db.GqlQuery("SELECT * FROM UserTag "
                            "WHERE user = :1 AND tag = 'seen'", user)
    if seen_tags.count() == 0:
        db.put(UserTag(user=user, tag="seen"))


def has_tag(tag):
    user = users.get_current_user()
    if not user:
        return False
    db.run_in_transaction(add_seen_tag)
    if users.is_current_user_admin():
        return True
    user_tags = db.GqlQuery("SELECT * FROM UserTag "
                            "WHERE user = :1 AND tag = :2", user, tag)
    return user_tags.count() > 0


def make_user_template(uri):
    if users.get_current_user():
        url = users.create_logout_url(uri)
        url_linktext = 'Logout'
    else:
        url = users.create_login_url(uri)
        url_linktext = 'Login'
    template_values = {
        'url': url,
        'url_linktext': url_linktext,
        }
    return template_values


def requires_tag(tag):
    def decorator(func):
        @functools.wraps(func)
        def handler(self, *args, **kwargs):
            if has_tag(tag):
                return func(self, *args, **kwargs)
            else:
                path = os.path.join(os.path.dirname(__file__), 'index.html')
                template_values = make_user_template(self.request.uri)
                self.response.out.write(template.render(path, template_values))
        return handler
    return decorator


class MainPage(webapp.RequestHandler):
    
    @requires_tag("seen")
    def get(self):
        template_values = make_user_template(self.request.uri)
        if has_tag("execute"):
            path = os.path.join(os.path.dirname(__file__), 'repl.html')
            self.response.out.write(template.render(path, template_values))
        else:
            path = os.path.join(os.path.dirname(__file__), 'seen.html')
            self.response.out.write(template.render(path, template_values))


def no_imports(name, fromlist):
    raise ImportError("You are not yet allowed to import anything: " + name )


class WebService(webapp.RequestHandler):

    def cappython_validate(self, string):
        tree = transformer.parse(string.encode("utf-8") + "\n")
        global_vars, bindings = varbindings.annotate(tree)
        log = pycheck.check(tree, bindings)
        return len(log) == 0

    def cappython_run(self, string):
        data = StringIO()
        env = safeeval.safe_environment()
        env.set_importer(no_imports)
        def safe_write(string):
            data.write(unicode(string, encoding="ascii").encode("utf-8"))
        env.bind("write", safe_write)
        try:
            safeeval.safe_eval(string.encode("utf-8") + "\n", env)
        except Exception, e:
            return unicode(traceback.format_exc())
        return data.getvalue().decode("utf-8")

    @requires_tag("execute")
    def post(self):
        string = self.request.body.decode("utf-8")
        json = simplejson.loads(string)
        if json[u"method"] == u"validate":
            if self.cappython_validate(json[u"params"][0]):
                response_data = {u"result": u"passed"}
            else:
                response_data = {u"result": u"failed"}
        elif json[u"method"] == u"execute":
            response_data = self.cappython_run(json[u"params"][0])
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
