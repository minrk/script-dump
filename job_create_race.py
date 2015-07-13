from IPython.parallel import Client
import time
import os

client = Client()
lbview = client.load_balanced_view()

def do_nothing(render_script, env_dict):
    os.listdir(".")

num_tasks = 100
task_frames = range(1, num_tasks + 1, 1)
for x in task_frames:
    env_dict = {}
    render_script = "foo"
    ar = lbview.apply(do_nothing, render_script, env_dict)
    # avoid race condition
    #time.sleep(0.2)


client.wait()
time.sleep(5)
records = client.db_query({'msg_id' : {'$in' : client.history}}, keys=['header', 'completed', 'engine_uuid'])
print "records: "+str(len(records))
print "history: "+str(len(client.history))

arrived = filter(lambda rec: rec['engine_uuid'] is not None, records)
print "arrived tasks: "+str(len(arrived))

finished = filter(lambda rec: rec['completed'] is not None, records)
print "finished tasks: "+str(len(finished))
