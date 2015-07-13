#!/usr/bin/env python

import sys
import time

import numpy as np
import pandas as pd

sleep = time.sleep

dtype = [('p', 'i4'), ('n', 'i4'), ('per_p', 'i4'), ('chunk', 'i4'), ('dt','f8'), ('wall','f8'), ('sent', 'f8')]

def divisors(n):
    divs = set([1,n])
    for d in xrange(2,n/2+1):
        if n%d==0:
            divs.add(d)
    return sorted(divs)

def do_run(v, n, dt, chunk_size, ntrials, map=True):
    sleeps = [dt]*n
    sends = 0
    it = xrange(ntrials)
    start = time.time()
    for i in it:
        print i
        tic = time.time()
        if map:
            ar = v.map_async(sleep, sleeps, chunksize=chunk_size)
        else:
            ars = [v.apply_async(sleep, dt).msg_id for _ in xrange(n)]
        toc = time.time()
        sends += toc-tic
        
        if map:
            ar.get()
        else:
            v.client.barrier(ars)
    stop = time.time()
    return sends/ntrials, (stop-start)/ntrials


def generate_data(v, nlist=None, dt0=1e-3, dtmax=.13, ntrials=2, dtstep=2, limit=1.1, maxchunks=6, cmin=5, periodic_save=False):
    p = len(v.client) if v.targets is None else len(v.targets)
    if not nlist:
        nlist = np.logspace(2,10,9,base=2).astype('int') # 4,8,16...1024 per process
    runs = []
    try:
      for per_p in nlist:
        n = p*per_p
        print n, p, per_p
        # use all evenly divisible chunks, truncate largest chunks
        chunks = divisors(n/p)[:maxchunks]
        # chunks = np.linspace(1,n/p,min(maxchunks,n/p)).astype('int')
        for chunk in chunks:
            dt = 1.*dt0 # ensure float
            # dummy values to start loop:
            target=1
            wall=target+1
            # limit by either approaching parallel ideal or max runtime
            c = 0
            print chunk
            while c < cmin or (dt <= dtmax and wall > target):
                c += 1
                serial=dt*n
                ref = serial/p
                target = limit*ref
                sent, wall = do_run(v,n,dt, chunk, ntrials)
                print n, chunk, dt, serial, ref, wall, serial/wall
                sys.stdout.flush()
                run = (p, n, per_p, chunk, dt, wall, sent)
                runs.append(run)
                dt *= dtstep
            time.sleep(0.1*max(1,wall))
            v.client.purge_results('all')
        if periodic_save:
            df = pd.DataFrame(runs, columns=('p','n','per_p','chunk','dt', 'wall','sent'))
            df.to_pickle(periodic_save)
    except KeyboardInterrupt:
        print "interrupted, stopping..."
    df = pd.DataFrame(runs, columns=('p','n','per_p','chunk','dt', 'wall','sent'))
    return df
    

def plot_chunks(data, n, p=None):
    # mask to n
    from matplotlib import pyplot as plt
    plt.figure()
    data = data[data['n']==n]
    if p is None:
        p = data['p'][0]
    else:
        data = data[data['p']==p]
    for chunk in sorted(set(data['chunk'])):
        subdata = data[data['chunk']==chunk]
        x = subdata['dt']
        y = subdata['dt']*n/subdata['wall']
        plt.semilogx(x,y, '-+', label='%i'%chunk)
    ax = plt.gca()
    xmin,xmax = ax.get_xlim()
    
    plt.plot([xmin,xmax], [1,1],'k:')
    plt.plot([xmin,xmax], [p,p],'k')
    plt.title("%i elements, %i engines"%(n,p))
    plt.xlabel('job size (s)')
    plt.ylabel('$T_{serial}/T_{parallel}$')
    plt.legend(loc=0)
    plt.grid(True)

def plot_jobs(data, n, p=None):
    # mask to n
    from matplotlib import pyplot as plt
    plt.figure()
    data = data[data['n']==n]
    if p is None:
        p = data['p'][0]
    else:
        data = data[data['p']==p]
    for dt in sorted(set(data['dt']))[::-1]:
        subdata = data[data['dt']==dt]
        x = subdata['chunk']
        y = subdata['dt']*n/subdata['wall']
        plt.semilogy(x,y, '-+', label='%i ms'%(dt*1000))
    ax = plt.gca()
    xmin,xmax = ax.get_xlim()
    
    plt.plot([xmin,xmax], [1,1],'k:')
    plt.plot([xmin,xmax], [p,p],'k')
    plt.title("%i elements, %i engines"%(n,p))
    plt.xlabel('chunk size')
    plt.ylabel('$T_{serial}/T_{parallel}$')
    plt.legend(loc=0)
    plt.grid(True)

def plot_ns(data, chunk=1, p=None):
    # mask to chunk
    from matplotlib import pyplot as plt
    plt.figure()
    data = data[data['chunk']==chunk]
    if p is None:
        p = data['p'][0]
    else:
        data = data[data['p']==p]
    for n in sorted(set(data['n'])):
        subdata = data[data['n']==n]
        x = subdata['dt']
        y = subdata['dt']*n/subdata['wall']
        plt.loglog(x,y, '-+', label='%i'%(n))
    ax = plt.gca()
    xmin,xmax = ax.get_xlim()
    
    plt.plot([xmin,xmax], [1,1],'k:')
    plt.plot([xmin,xmax], [p,p],'k')
    plt.title("chunk size %i, %i engines"%(chunk,p))
    plt.xlabel('job size (s)')
    plt.ylabel('$T_{serial}/T_{parallel}$')
    plt.legend(loc=0)
    plt.grid(True)


if __name__ == '__main__':
    try:
        get_ipython
    except NameError:
        # not in IPython, redirect stdout, get config, and run the script
        import os
        from IPython.parallel import Client
        
        sys.stdout = open('output-%i.log'%os.getpid(), 'w')
        rc = Client()
        v = rc.load_balanced_view()
        data = generate_data(v, periodic_save='output.dat')
        data.to_pickle("output.dat")

