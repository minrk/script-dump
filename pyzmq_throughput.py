import os
import time
import numpy as np
from subprocess import Popen, PIPE

import zmq

rec_dtype = [('size', int), ('nmsgs', int), ('copy', bool), ('track', bool), ('sent', float), ('wall', float)]

def timeit(f,*args, **kwargs):
    tic = time.time()
    f(*args, **kwargs)
    return time.time()-tic

def throughput_test(socket, msg, nmsgs, copy=False, track=False):
    sendtimes = []
    tic = time.time()
    for i in range(nmsgs):
        socket.send(msg, copy=copy, track=track)
        # sendtimes.append(t)
    sent_t = time.time()-tic
    for i in range(nmsgs):
        msg = socket.recv(copy=copy, track=track)
    wall_t = time.time() - tic
    
    return len(msg), nmsgs, copy, track, sent_t, wall_t
    
def launch_echo_server():
    proc = Popen('python echo_server.py'.split(), stdout=PIPE)
    port = int(proc.stdout.readline())
    return proc, port


def run_tests(size_range=np.logspace(5,22,2*(22-5)+1,base=2).astype(int), 
            n_range=np.logspace(1,10,2*(10-1)+1,base=2).astype(int), 
            iface='tcp://127.0.0.1'):
    proc,port = launch_echo_server()
    ctx = zmq.Context()
    socket = ctx.socket(zmq.XREQ)
    socket.connect('%s:%i'%(iface, port))
    time.sleep(0.1)
    data = np.recarray(len(size_range)*len(n_range)*3, dtype=rec_dtype)
    i=0
    try:
        for size in size_range:
            msg = os.urandom(size)
            for n in n_range:
                for copy in range(2):
                    for track in range(2):
                        if track and copy:
                            continue
                        trial = throughput_test(socket, msg, n, copy=copy, track=track)
                        print trial
                        data[i] = trial
                        i+=1
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
    return data

def extract(data, **kwargs):
    mask = np.ones(len(data), dtype=np.bool)
    for axis,value in kwargs.items():
        mask = mask&(data[axis]==value)
    idx = np.where(mask)
    return data[idx]

def plot_lines(data, n=None):
    import pylab
    if n is None:
        n = data['nmsgs'][0]
    data = extract(data, nmsgs=n)
    assert len(data) > 0, 'no data, probably invalid n=%s'%n
    pylab.figure()
    pylab.plot([],[],'k:',label='sent')
    pylab.xlabel('bytes/msg')
    pylab.ylabel('msgs/sec')
    for copy in range(2):
        if copy:
            label = 'copy'
        else:
            label = 'nocopy'
        for track in range(2):
            if track and copy:
                continue
            track_s = ''
            if track:
                label += '+track'
            A = extract(data, copy=copy, track=track)
            x = A['size']
            lines = pylab.loglog(A['size'], 1.*n/A['wall'], label=label)
            c = lines[0].get_color()
            pylab.loglog(A['size'], 1.*n/A['sent'], ':'+c)
    pylab.legend(loc=0)
    pylab.grid(True)
    
    