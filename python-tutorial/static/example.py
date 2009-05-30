def fib(i):
  if i < 2:
    return 1
  else:
    return fib(i-1) + fib(i-2)

class Foo(object):
  def __init__(self, data):
    self._data = data
  def bar(self):
    write(str(self._data) + "\n")

Foo("hello, world").bar()
write(str([fib(i) for i in range(10)]) + "\n")
