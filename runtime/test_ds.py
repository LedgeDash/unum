import ds
import multiprocessing

# create a table with partition key "Name" of type String.

test_datastore = ds.UnumIntermediaryDataStore.create('dynamodb', 'unum-dynamodb-test-table', False)

# create a checkpoint should succeed with return value 1 if debug == False or
# the consumed capacity if debug == True. Consumed capacity is an integer
# that's always greater than 1.
assert test_datastore.checkpoint('test-session', 'A', {"User": "A output"}) >= 1
# create a checkpoint with the same name should fail with error code -1
assert test_datastore.checkpoint('test-session', 'A', {"User": "A output"}) == -1

# delete a checkpoint should succeed with return value 1 if debug == False or
# the consumed capacity if debug == True. Consumed capacity is an integer
# that's always greater than 1.
assert test_datastore.delete_checkpont('test-session', 'A') >= 1

# create a checkpoint should succeed with return value 1 if debug == False or
# the consumed capacity if debug == True. Consumed capacity is an integer
# that's always greater than 1.
assert test_datastore.checkpoint('test-session', 'A', {"User": "A output"}) >= 1

assert test_datastore.delete_checkpont('test-session', 'A') >= 1




ret = test_datastore._create_bitmap('test-bitmap', 10)

ret = test_datastore._update_bitmap_result('test-bitmap', 0)
print(ret)


ret = test_datastore._update_bitmap_result('test-bitmap', 3)
print(ret)

ret = test_datastore._update_bitmap_result('test-bitmap', 8)
print(ret)
test_datastore._delete("Name", "test-bitmap")

# test 400 concurrent writers to make sure only 1 of them will see a all-1's
# bitmap

def update_bitmap_check_ready(bitmap_name, index):
    rsp = test_datastore._update_bitmap_result(bitmap_name, index)

    for b in rsp:
        if b == False:
            # print(f'{index} peace out')
            return

    print(f'I am thread {index} in _update_bitmap_result(), and I see all Trues')
    return

jobs = []
procs = 400

ret = test_datastore._create_bitmap('test-bitmap', procs)

for i in range(0, procs):
    process = multiprocessing.Process(target=update_bitmap_check_ready, 
                                      args=('test-bitmap', i))
    jobs.append(process)

for j in jobs:
    j.start()

for j in jobs:
    j.join()
    j.close()

test_datastore._delete("Name", "test-bitmap")

# test 500 concurrent writers to make sure only 1 of them will see a all-1's
# bitmap using the _sync_ready API

def f(sync_point_name, index, num_branches):
    if test_datastore._sync_ready(sync_point_name, index, num_branches):
        print(f'I am thread {index} out of {num_branches} _sync_ready, and I see all Trues')

jobs = []
procs = 500
for i in range(0, procs):
    process = multiprocessing.Process(target=f, 
                                      args=('test-bitmap', i, procs))
    jobs.append(process)

for j in jobs:
    j.start()

for j in jobs:
    j.join()
    j.close()

test_datastore._delete("Name", "test-bitmap")



# test 450 concurrent branch fan-in to make sure only 1 of them will see a
# all-1's bitmap using the fanin_sync_ready API
def f(session, aggregation_function_instance_name, index, num_branches):
    if test_datastore.fanin_sync_ready(session, aggregation_function_instance_name, index, num_branches):
        print(f'I am thread {index} out of {num_branches} fan-in, and I see all Trues')

jobs = []
num_branches = 450
session = 'test-session'
aggregation_function_instance_name = 'aggregate'

for i in range(0, num_branches):
    process = multiprocessing.Process(target=f, 
                                      args=(session, aggregation_function_instance_name, i, num_branches))
    jobs.append(process)

for j in jobs:
    j.start()

for j in jobs:
    j.join()
    j.close()

test_datastore._delete("Name", test_datastore.fanin_sync_point_name(session, aggregation_function_instance_name))


# test 300 concurrent branch gc to make sure only 1 of them will see a
# all-1's bitmap using the gc_sync_ready API
def f(session, parent_function_instance_name, index, num_branches):
    if test_datastore.gc_sync_ready(session, parent_function_instance_name, index, num_branches):
        print(f'I am thread {index} out of {num_branches} gc, and I see all Trues')

jobs = []
num_branches = 300
session = 'test-session'
parent_function_instance_name = 'UnumMap0'

for i in range(0, num_branches):
    process = multiprocessing.Process(target=f, 
                                      args=(session, parent_function_instance_name, i, num_branches))
    jobs.append(process)

for j in jobs:
    j.start()

for j in jobs:
    j.join()
    j.close()

test_datastore._delete("Name", test_datastore.gc_sync_point_name(session, parent_function_instance_name))