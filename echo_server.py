import sys
import zmq

ctx = zmq.Context()
xrep = ctx.socket(zmq.XREP)

print xrep.bind_to_random_port('tcp://*')
sys.stdout.flush()

while True:
    msg = xrep.recv_multipart(copy=False)
    xrep.send_multipart(msg, copy=False)