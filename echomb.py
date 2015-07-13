import time
import os
import numpy

from IPython import parallel
rc = parallel.Client()
# v = rc.load_balanced_view()
v = rc[rc.ids[-1]]

def get_usage():
    M = 1024*1024
    import psutil,os
    mem = psutil.Process(os.getpid()).get_memory_info()
    return "mem:%4iMB" % (mem.rss / M)

def time_f(f, *a, **kw):
    tic = time.time()
    f(*a,**kw)
    return time.time()-tic
    
def echo_mb():
    import numpy
    A = numpy.random.random(1024*1024/8)#1024/8)
    ar = v.apply_sync(lambda x:x, A)
    if isinstance(ar, parallel.AsyncResult):
        raise KeyboardInterrupt
    # disable local caching
    rc.results.clear()
    v.results.clear()


i = 0
start = time.time()
tic = time.time()
times = []
for i in range(2000):
    times.append(time_f(echo_mb))
    
    time.sleep(0.01)
    if i % 10 == 0:
        toc = time.time()
        print i, "%.1f" % (toc-tic)
        tic = time.time()
print "total time to echo %i MB: %.1fs" % (i, time.time()-start)
from matplotlib import pyplot as plt
plt.hist(times, bins=i/10)
plt.show()

        