def hello_world(env, response):
  response('200 OK', [('content-type', 'text/hmtl')])
  return ['hello david']

from wsgiref import simple_server
simple_server.make_server('', 8080, hello_world).serve_forever()


