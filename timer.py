import sys
import time
from subprocess import Popen, PIPE
from numpy import logspace
from IPython.zmq.parallel import client, streamsession as ss

def timeit(f):
    def timed(*args, **kwargs):
        tic = time.time()
        f(*args, **kwargs)
        timer = time.time()-tic
        
        return timer
    return timed


def dot(a,b=1):
    return a*b

@timeit
def flood(n,block=True):
    print n, block,
    c.block = block
    v = c[None]
    for a in xrange(n):
        v.apply(dot,a,b=a)

@timeit
def barrier():
    c.barrier()

def run():
    print len(c.ids)
    for block in (True, False):
        a,b=3,11
        for n in map(int, logspace(a,b,b-a+1,base=2)):
            for i in range(2):
                t=flood(n,block)
                t2=barrier()
                print n/t, n/(t+t2)
                time.sleep(1)
                sys.stdout.flush()

if len(sys.argv) > 1:
    c = client.Client('tcp://127.0.0.1:10101', sshserver=sys.argv[1])
else:
    c = client.Client('tcp://127.0.0.1:10101')
c.spin()
assert len(c.ids) == 0, "already have engines"
# time.sleep(1)
children = []
prev_i = 0
for i in [1,2,4,6,8]:
    for j in range(i-prev_i):
        children.append(Popen(("ipenginez --ident engine-%i"%(prev_i+j)).split(), stdout=open("/dev/null", 'w')))
    prev_i = i
    while len(c.ids) < i:
        # print len(c.ids)
        time.sleep(0.25)
    run()