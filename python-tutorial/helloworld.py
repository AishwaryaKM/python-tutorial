

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.api import urlfetch

import cgi
import functools
import os
import sys
import logging

import pycheck2 as pycheck
import transformer2 as transformer
import varbindings2 as varbindings
import linecache
import traceback
from pprint import pformat

import simplejson

import tutorial


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
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        template_values = make_user_template(self.request.uri)
        self.response.out.write(template.render(path, template_values))


class LoginIframe(webapp.RequestHandler):
    
    def get(self, action):
        if action == "refresh":
            path = os.path.join(os.path.dirname(__file__), 
                                "account-refresh.html")
            self.response.out.write(template.render(path, {}))
        else:
            if action == "login":
                url = users.create_login_url("/account/refresh")
            elif action == "logout":
                url = users.create_logout_url("/account/refresh")
            else:
                raise NotImplemnetedError(action)
            template_values = {"login_url": url}
            path = os.path.join(os.path.dirname(__file__), 'account.html')
            self.response.out.write(template.render(path, template_values))


class CdnProxy(webapp.RequestHandler):

    def get(self, rel_url):
        url = "http://ajax.googleapis.com/ajax/libs/" + rel_url
        data = memcache.get(url)
        if data is None:
            response = urlfetch.fetch(url)
            if response.status_code == 200:
                data = {"url": url,
                        "body": response.content,
                        "content_type": response.headers["Content-Type"],
                        "result": 200}
            else:
                # We put failures into the cache too, to prevent
                # spinning failures
                data = {"url": url,
                        "result": result.status_code}
            memcache.set(key=url, value=data)
        if data["result"] == 200:
            self.response.headers.add_header("Content-Type",
                                             data["content_type"])
            self.response.out.write(data["body"])


class WebService(webapp.RequestHandler):

    @requires_tag("execute")
    def validate(self, code):
        code = unicode(code).encode("utf-8") + "\n"
        tree = tutorial.transforming_parser(code)
        global_vars, bindings = varbindings.annotate(tree)
        log = pycheck.check(tree, bindings)
        if len(log) == 0:
            return u"No validation failures"
        else:
            return (u"Validation failed for with the following errors:\n" 
                    + pformat(log))

    @requires_tag("execute")
    def execute(self, code):
        code = unicode(code).encode("utf-8") + "\n"
        try:
#             return tutorial.run_with_emulated_print(code).decode("utf-8")
            return tutorial.run_straight_cappython(code).decode("utf-8")
        except Exception, e:
            return unicode(traceback.format_exc())

    def get_account_status(self):
        user = users.get_current_user()
        if not user:
            return ["unknown"]
        db.run_in_transaction(add_seen_tag)
        if users.is_current_user_admin():
            return ["known", "admin", user.nickname()]
        user_tags = db.GqlQuery("SELECT * FROM UserTag "
                                "WHERE user = :1 AND tag = 'execute'", user)
        if user_tags.count() > 0:
            return ["known", "registered", user.nickname()]
        else:
            return ["known", "unregistered", user.nickname()]

    def get_constants(self):
        return {"logout": users.create_logout_url("about:blank"),
                "login": users.create_login_url("about:blank")}

    def post(self):
        string = self.request.body.decode("utf-8")
        json = simplejson.loads(string)
        assert not json[u"method"].startswith(u"_"), json[u"method"]
        method = getattr(self, json[u"method"].encode("ascii"))
        result = method(*json[u"params"])
        self.response.headers.add_header("Content-Type", 
                                         "application/json; charser=utf-8")
        self.response.out.write(simplejson.dumps(result).encode("utf-8"))


application = webapp.WSGIApplication([
        ('/', MainPage),
        ("/ws", WebService),
        ("/cdn/(.*)", CdnProxy),
        ("/account/(login|logout|refresh)", LoginIframe)
        ], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == "__main__":
  main()