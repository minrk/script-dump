import os,sys,shutil
import time

import resource
import tempfile
import uuid

from IPython.parallel.controller.sqlitedb import SQLiteDB
from IPython.parallel.controller.dictdb import DictDB

DB = DictDB

k = 1024
M = 1024*k
G = 1024*M

recsize = 1*M

def print_mem():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    print usage.ru_maxrss / M, "MB"

records = 0

tempdir = tempfile.mkdtemp()

# db = SQLiteDB(location=tempdir)
db = DictDB()
# fname = os.path.join(tempdir, db.filename)

def build_record(size):
    msg_id = str(uuid.uuid4())
    rec = dict(msg_id=msg_id, buffers=[os.urandom(size)])
    return msg_id, rec

print os.getpid()
try:
    while True:
        records += 1
        msg_id, rec = build_record(recsize)
        db.add_record(msg_id, rec)
        time.sleep(0.02)
        if records % 20 == 0:
            print records,
            print_mem()
            if DB is SQLiteDB:
                os.system("du -hs %s" % fname)
            
except KeyboardInterrupt:
    print "\nInterrupted"
    del db
    shutil.rmtree(tempdir) 