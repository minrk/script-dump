import os, sys, time
import json

from datetime import datetime

import zmq
from zmq.eventloop.ioloop import IOLoop, PeriodicCallback
from zmq.eventloop.zmqstream import ZMQStream

from IPython.lib.kernel import find_connection_file
from IPython.zmq.session import Session

def log_msg(session, msg_list):
    idents, msg_list = session.feed_identities(msg_list)
    msg = session.unserialize(msg_list)
    content = msg['content']
    if msg['msg_type'] == 'stream':
        fd = getattr(sys, content['name'])
        fd.write(content['data'])
        fd.flush()

def print_time():
    print datetime.now()

def main(pat):
    
    fname = find_connection_file(pat)
    with open(fname) as f:
        cfg = json.load(f)
    
    url = "%s://%s:%s" % (cfg.get('transport', 'tcp'), cfg['ip'], cfg['iopub_port'])
    
    session = Session(key=cfg['key'])
    
    ctx = zmq.Context.instance()
    sub = ctx.socket(zmq.SUB)
    sub.subscribe = b''
    sub.connect(url)
    # import IPython
    # IPython.embed()
    # return
    
    stream = ZMQStream(sub)
    
    stream.on_recv(lambda msg_list: log_msg(session, msg_list))
    
    pc = PeriodicCallback(print_time, 5 * 60 * 1000)
    pc.start()
    IOLoop.instance().start()

if __name__ == '__main__':
    main(sys.argv[1])