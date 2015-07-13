import sys
import time
from subprocess import Popen, PIPE
from numpy import logspace,array
import numpy
# from numpy.linalg import norm
from IPython.zmq.parallel import client, streamsession as ss
tries = 3
def timeit(f):
    def timed(*args, **kwargs):
        tic = time.time()
        f(*args, **kwargs)
        timer = time.time()-tic
        
        return timer
    return timed


def f(a):
    import time
    tic = time.time()
    from numpy.linalg import norm
    z=norm(a,2)
    return time.time()-tic

@timeit
def flood(A,block=True):
    print A.shape, block,
    c.block = block
    for i in range(tries):
        # A = numpy.random.random((a,a))
        c.apply(f,args=(A,),bound=True)

@timeit
def barrier():
    c.barrier()

def run():
    print len(c.ids)
    for block in (False,):
        for n in map(int, logspace(4,10,7,base=2)):
            N = 4e-6**n*n
            for i in range(2):
                A = numpy.random.random((n,n))
                
                t=flood(A,block)
                t2=barrier()
                print t, (t+t2), 
                # print map
                res = c.results.get(c.history[-1])
                if isinstance(res, dict):
                    print ''.join(res['traceback'])
                    raise Exception
                # print map(c.results.get, c.history[-1*tries:])
                print sum(map(c.results.get, c.history[-1*tries:]))
                time.sleep(1)
                sys.stdout.flush()

c = client.Client('tcp://127.0.0.1:10101')
c.spin()
# time.sleep(1)
children = []
for i in range(1,tries+1):
    children.append(Popen(("ipenginez --ident engine-%i"%i).split(), stdout=open("/dev/null", 'w')))
    # Popen("python /home/minrk/git/ipython/IPython/zmq/engine.py".split(), stdout=open("/dev/null", 'w'))
    try:
        while len(c.ids) < i:
            # print c.ids
            time.sleep(0.5)
        run()
    # except KeyboardInterrupt:
    #     break
    except Exception, e:
        print e
        break

for p in children:
    p.kill()
# sys.exit()
    