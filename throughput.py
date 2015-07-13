#!/usr/bin/env python

import sys
import time
import numpy as np
from IPython import parallel

nlist = map(int, np.logspace(2,9,16,base=2))
nlist2 = map(int, np.logspace(2,8,15,base=2))
longrun = np.logspace(2,12,21,base=2).astype(int)
tlist = map(int, np.logspace(7,22,16,base=2))
nt = 16
def wait(t=0):
    import time
    time.sleep(t)

def echo(s=''):
    return s

def time_throughput(rc, nmessages, t=0, f=wait):
    view = rc.load_balanced_view()
    # do one ping before starting timing
    if f is echo:
        t = np.random.random(t/8)
    # ping all engines for sync
    rc[:].apply_sync(echo, '')
    rc.spin()
    tic = time.time()
    for i in xrange(nmessages):
        view.apply(f, t)
    lap = time.time()
    rc.wait()
    toc = time.time()
    return lap-tic, toc-tic

def do_runs(rc, nlist, t=0, f=wait, trials=3, runner=time_throughput):
    dtype = [('p', int), ('n', int), ('sent', float), ('roundtrip', float), ('size', float), ('scheme', 'a32')]
    p = len(rc)
    A = np.recarray(len(nlist), dtype=dtype)
    A['scheme'] = rc._task_scheme
    A['size'] = t
    A['p'] = len(rc)
    try:
        for i,n in enumerate(nlist):
            sent = roundtrip = 0
            for _ in range(trials):
                time.sleep(.25)
                dt1,dt2 = runner(rc,n,t,f)
                sent += dt1
                roundtrip += dt2
            sent /= trials
            roundtrip /= trials
            A[i]['n'] = n
            A[i]['sent'] = sent
            A[i]['roundtrip'] = roundtrip
            # A[i] = n/A[i]
            print p,n,n/sent,n/roundtrip
    except KeyboardInterrupt:
        print 'interrupted'
        A = A[:i]
    return A

def do_echo(n,tlist=[0],f=echo, trials=2, runner=time_throughput):
    A = np.zeros((len(tlist),2))
    for i,t in enumerate(tlist):
        t1 = t2 = 0
        for _ in range(trials):
            time.sleep(.25)
            ts = runner(n,t,f)
            t1 += ts[0]
            t2 += ts[1]
        t1 /= trials
        t2 /= trials
        A[i] = (t1,t2)
        A[i] = n/A[i]
        print t,A[i]
    return A

if __name__ == '__main__':
    try:
        get_ipython
    except NameError:
        # not in IPython, redirect stdout, get config, and run the script
        import os
        from IPython.parallel import Client
        
        # sys.stdout = open('output-%i.log'%os.getpid(), 'w')
        # get config from running application:
        rc = Client(packer='msgpack.packb', unpacker='msgpack.unpackb', profile='thru')
        A = do_runs(rc, longrun)
        A.tofile('throughput-%i.dat'%os.getpid())

    