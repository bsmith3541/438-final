import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.template
import time

import threading
import Queue

import json
import sqlite3
DEFAULT_DB = 'development.sqlite3'

class MainHandler(tornado.web.RequestHandler):
  def get(self):
    loader = tornado.template.Loader(".")
    self.write(loader.load("query.html").generate())

  def post(self):
    query = self.get_argument('query', '')

    conn = sqlite3.connect(DEFAULT_DB)
    c = conn.cursor()
    c.execute(query)
    results = c.fetchone()
    self.write(json.dumps(results))
    conn.close()

class WSHandler(tornado.websocket.WebSocketHandler):
  def open(self):
    self.driver = SqliteDriver(self)

  def on_message(self, message):
    self.driver.handle_message(message)

  def on_close(self):
    print 'Connection closed.'

class Driver:
  def __init__(self, channel, extra_handlers={}):
    self.channel = channel

    self.handlers = {
      'help' : self.handle_help,
      'loop' : self.handle_loop,
    }

    self.handlers.update(extra_handlers)

  def determine_handler(self, cmd):
    return self.handlers.get(cmd, self.handle_none)

  def handle_help(self, cmd, args):
    self.channel.write_message("Need some help?")

  def handle_none(self, cmd, args):
    self.channel.write_message("No handler found.")

  def handle_loop(self, cmd, args):
    i = 0
    while True:
      i += 1
      self.channel.write_message("Loop %d" % i)
      time.sleep(2)

class DriverThreaded(Driver):
  def handle_message(self, message):
    msg_parts = message.split(':', 1)
    cmd = msg_parts[0]
    args = msg_parts[1] if len(msg_parts) > 1 else None

    handler = self.determine_handler(cmd)

    # Turn off threading for experiment
    # t = threading.Thread(target=handler, args=[cmd, args])
    # t.start()
    handler(cmd, args)

class SqliteDriver(DriverThreaded):
  def __init__(self, channel):
    sqlite_handlers = {
      'connect' : self.handle_connect,
      'execute' : self.handle_execute,
      'commit' : self.handle_commit,
      'close' : self.handle_close,
      'fetchone' : self.handle_fetchone,
    }

    DriverThreaded.__init__(self, channel, sqlite_handlers)

    self.database = None
    self.conn = None
    self.c = None

  def handle_connect(self, cmd, args):
    db = DEFAULT_DB if args is None else args
    self.conn = sqlite3.connect(db)

    self.channel.write_message('Opened connection to %s' % db)

  def handle_execute(self, cmd, query):
    if query is None:
      self.channel.write_message('Nothing to execute')
      return

    self.c = self.conn.cursor()
    self.c.execute(query)

    self.channel.write_message('Executed %s' % query)

  def handle_commit(self, cmd, args):
    self.conn.commit()
    self.channel.write_message('Committed.')

  def handle_close(self, cmd, args):
    self.channel.write_message('Closing socket. Goodbye.')
    self.conn.close()

  def handle_fetchone(self, cmd, args):
    result = self.c.fetchone()
    jsoned = json.dumps(result)

    self.channel.write_message('Result: ' + jsoned)

  def handle_fetchall(self, cmd, args):
    results = self.c.fetchall()
    jsoned = json.dumps(results)

    self.channel.write_message(jsoned)

####################################################################

application = tornado.web.Application([
  (r'/ws', WSHandler),
  (r"/", MainHandler),
  (r"/(.*)", tornado.web.StaticFileHandler, {"path": "./resources"}),
])

if __name__ == "__main__":

  application.listen(80)
  tornado.ioloop.IOLoop.instance().start()
