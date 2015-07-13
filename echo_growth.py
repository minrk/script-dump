import os
import time
from itertools import count

from IPython import parallel

rc = parallel.Client()
engine = rc[-1]

def echo(x):
    return x

print("client PID: %i" % os.getpid())
print("engine PID: %i" % engine.apply_sync(os.getpid))

data = b'x' * 1024# * 1024
rc.session.digest_history_size = 100

for i in count():
    if not i % 1000:
        print(i)
        engine.history = []
        rc.history = []
        # print(len(rc.metadata), len(rc.results))
    engine.apply_sync(echo, data)
    # time.sleep(1e-4)
