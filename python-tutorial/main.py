

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import simplejson
import traceback
import tutorial


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

    def execute(self, code):
        code = unicode(code).encode("utf-8") + "\n"
        try:
            return tutorial.run_with_emulated_print(code).decode("utf-8")
#             return tutorial.run_straight_cappython(code).decode("utf-8")
        except Exception, e:
            return unicode(traceback.format_exc())

    def get_constants(self):
        return {}

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
        ("/ws", WebService),
        ("/cdn/(.*)", CdnProxy),
        ], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()
