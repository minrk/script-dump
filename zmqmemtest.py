import numpy
import threading
import zmq

def client(iface, n=2000):
    ctx = zmq.Context.instance()
    req = ctx.socket(zmq.REQ)
    req.linger = 0
    req.connect(iface)
    for i in range(n):
        if i % 100 == 0:
            print i
        A = numpy.random.random(1024*1024)
        req.send(A, copy=False)
        del A
        buf = req.recv(copy=False)
        B = numpy.frombuffer(buf)
        del B

def server(iface, n=2000):
    ctx = zmq.Context.instance()
    rep = ctx.socket(zmq.REP)
    rep.linger = 0
    rep.bind(iface)
    for i in range(2000):
        buf = rep.recv(copy=False)
        B = numpy.frombuffer(buf)
        del B
        A = numpy.random.random(1024*1024)
        rep.send(A, copy=False)
        del A

def main():
    iface = 'tcp://127.0.0.1:5656'
    sthread = threading.Thread(target=server, args=(iface,2000))
    sthread.daemon=True
    sthread.start()
    client(iface, 2000)
    raw_input("done, check memory usage")

if __name__ == '__main__':
    main()
    