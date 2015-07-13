#!/usr/bin/env python
# coding: utf-8
import atexit
import logging
import os
import sys
import time

from itertools import izip
from subprocess import Popen, PIPE, STDOUT

import numpy as np
import pandas as pd
from IPython import parallel

sleep = time.sleep

dtype = [('p', 'i4'), ('n', 'i4'), ('per_p', 'i4'), ('hwm', 'i4'), ('dt','f8'), ('wall','f8'), ('sent', 'f8')]
columns = ('p', 'n', 'per_p', 'hwm', 'scheme', 'dt', 'var', 'wall', 'sent', 'serial')

# log = logging.getLogger()
# log.set
blackhole = open(os.devnull, 'w')

def divisors(n):
    divs = set([1,n])
    for d in xrange(2,n/2+1):
        if n%d==0:
            divs.add(d)
    return sorted(divs)
    
def time_f(t,echo=b''):
    import time
    time.sleep(t)
    return echo


def do_run(v, n, dt, size, var, ntrials, localtime=0, use_map=False):
    """
    v: view
    n: number of tasks
    dt: reference task time (time.sleep)
    size: size (in bytes) number of bytes to echo
    var: relative variation of sleep time: uniform distribution in [ dt,dt*(1+var) )
    ntrials: number of trials
    localtime: sleep between task submissions; only valid when use_map=False
    use_map: whether to use map instead of n calls to apply_async
    """
    echo = np.random.uniform(0,256, size=n).astype('uint8')
    sleeps = np.random.uniform(dt, dt*(1+var), size=n)
    echos = [echo]*n
    sends = 0
    it = xrange(ntrials)
    start = time.time()
    limitsleep = localtime * dt
    for i in it:
        tic = time.time()
        if use_map:
            assert not rate_limit, "rate limiting not supported with map"
            ar = v.map_async(time_f, sleeps, echos)
        else:
            ars = []
            for sleep,echo in izip(sleeps,echos):
                ars.append(v.apply_async(time_f, sleep, echo))
                time.sleep(localtime)
        toc = time.time()
        sends += toc-tic
        
        if use_map:
            ar.get()
        else:
            v.client.wait(ars)
    stop = time.time()
    # serial is the ideal computation time *including* local time
    serial = sum(sleeps) + (limitsleep * n)
    return sends/ntrials, (stop-start)/ntrials, serial

def start_cluster(p=4, hwm=0, profile='default', scheme='twobin', timeout=10):
    print "starting cluster with %i engines" % p
    ccmd = ['ipcontroller', '--profile', profile, '--hwm', str(hwm), '--scheme', scheme, '--reuse', '--log-level', 'WARN']
    controller = Popen(ccmd, stdout=blackhole, stderr=blackhole)
    time.sleep(1)
    if controller.poll() is not None:
        raise RuntimeError("Could not start controller")
    ecmd = ['ipengine', '--profile', profile]
    engines = [ Popen(ecmd, stdout=blackhole, stderr=blackhole) for _ in range(p) ]
    
    atexit.register(lambda : stop_cluster(controller, engines))
    
    print "connecting client"
    client = parallel.Client()
    tic = time.time()
    while len(client.ids) < p and time.time() - tic < timeout:
        print "waiting for %i/%i engines to register" % (p-len(client.ids), p)
        time.sleep(1)
    
    if len(client.ids) < p:
        stop_cluster(controller, engines)
        raise RuntimeError("Timeout waiting for engines")
    
    return client, controller, engines
    ecmd = ['ip']
    p = subprocess.Popen(['ipcluster', 'start'])

def stop_cluster(controller, engines):
    print "stopping cluster"
    for p in [controller] + engines:
        for i in range(10):
            try:
                p.terminate()
            except OSError:
                break
            if p.poll() is None:
                time.sleep(0.1)
            else:
                break
        if p.poll() is None:
            print "killing", p
            p.kill()
            time.sleep(0.1)
        if p.poll() is None:
            print "couldn't kill", p

def per_cluster(v, nlist, slist, vlist, localtimes=0, hwm=0, dt0=1e-3, dtmax=130e-3, ntrials=3, dtstep=2, scalelimit=1.1, mincount=5, scheme='twobin', periodic_save=False):
    p = len(v.client.ids) if v.targets is None else len(v.targets)
    runs = []
    if not isinstance(localtimes, list):
        localtimes = [localtimes]
    try:
        for var in vlist:
            for per_p in nlist:
                n = p*per_p
                for s in slist:
                    for local in localtimes:
                        print "hwm\tn\ts\tdt        \tserial\tref\twall\tserial/wall"
                        dt = 1.*dt0 # ensure float
                        # dummy values to start loop:
                        target=1
                        wall=target+1
                        # limit by either approaching parallel ideal or max runtime
                        c = 0
                        while c < mincount or (dt <= dtmax and wall > target):
                            c += 1
                            serial = dt*n
                            sent, wall, serial = do_run(v, n=n, size=s, dt=dt, var=var, ntrials=ntrials, localtime=local)
                            ref = serial/p
                            target = scalelimit*ref
                            print u"%i\t%i\t%i\t%03i±%.1f  \t%.3f\t%.3f\t%.3f\t%.3f" % (
                                hwm, n, s, 1000*dt, var, serial, ref, wall, serial/wall
                            )
                            sys.stdout.flush()
                            run = (p, n, per_p, hwm, scheme, dt, var, wall, sent, serial)
                            runs.append(run)
                            dt *= dtstep
                        time.sleep(0.1*max(1,wall))
                        v.purge_results('all')
                        if periodic_save:
                            df = pd.DataFrame(runs, columns=columns)
                            df.save(periodic_save)
    except KeyboardInterrupt:
        print "interrupted, stopping..."
    df = pd.DataFrame(runs, columns=columns)
    if periodic_save:
        df.save(periodic_save)
    return df
    
def generate_data(nlist=None, slist=None, vlist=None, plist=None, hwmlist=None, schemelist=None, dt0=1e-3, dtmax=.13, ntrials=3, dtstep=2, scalelimit=1.1, mincount=5, hwm=0, periodic_save_t=False, profile='default', debug=False):
    if not plist:
        plist = [4,8,1]
    if not schemelist:
        schemelist = ['lru', 'twobin', 'pure']
    if not hwmlist:
        hwmlist = [0,1,2,4,6,8,10]
    if not nlist:
        nlist = np.logspace(2,7,6,base=2).astype('int') # 4,8,16...256 per process
    if not vlist:
        vlist = [0,0.1,0.25,0.5,1,2,4]
    if not slist:
        slist = np.logspace(2,20,10,base=2).astype('int') # 4,16,64...1024*1024 echo size in bytes
    
    if debug:
        slist = slist[:2]
        nlist = nlist[:2]
        vlist = [0]
        hwmlist = hwmlist[:2]
        plist = plist[:1]
        schemelist = schemelist[:1]
    frames = []
    offset = 0
    data = None
    for scheme in schemelist:
        for p in plist:
            for hwm in (hwmlist if scheme != 'pure' else [0]):
                try:
                    client, controller, engines = start_cluster(p=p, hwm=hwm, profile=profile, scheme=scheme)
                except KeyboardInterrupt:
                    "connection interrupted, stopping..."
                    return frames
                try:
                    view = client.load_balanced_view()
                    if periodic_save_t:
                        periodic_save = periodic_save_t.format(hwm=hwm, p=p, scheme=scheme)
                    else:
                        periodic_save = False
                    frame = per_cluster(view, nlist, slist, vlist, dt0=dt0, dtmax=dtmax, ntrials=ntrials, dtstep=dtstep, scalelimit=scalelimit, mincount=mincount, hwm=hwm, scheme=scheme, periodic_save=periodic_save)
                    if data is None:
                        data = frame
                    else:
                        frame.index += (data.index[-1] + 1)
                        data.append(frame)
                    if periodic_save_t:
                        data.save(periodic_save_t.format(hwm='',p='',scheme=''))
                finally:
                    stop_cluster(controller, engines)
    return data

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
        data = generate_data(periodic_save_t='output.{p}.{hwm}.{scheme}.dat', debug=False, profile='perf')

