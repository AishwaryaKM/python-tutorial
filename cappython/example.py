
from wsgiref import simple_server


#if __name__ == "__main__":
server = simple_server.make_server("", 1234, simple_server.demo_app)
server.serve_forever()
