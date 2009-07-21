def fib(i):
  if i < 2:
    return i
  else:
    return fib(i-1) + fib(i-2)

class Foo(object):
  def __init__(self, data):
    self._data = data
  def bar(self):
    print self._data

Foo("hello, world").bar()
print [fib(i) for i in range(10)]
