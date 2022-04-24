import json
import os
import time
import sys
if os.environ['FAAS_PLATFORM'] == 'gcloud':
    import base64

from unum import Unum
from app import lambda_handler as user_lambda

'''Create the unum runtime context from this function's unum configuration and
the workflow's intermediary data store information.

The unum runtime context is represented by the Unum class.

The unum configuration for a function is in the unum_config.json file and it
is function-specific. The unum intermediary data store information is in
unum-template.yaml and it is shared by all functions in the workflow.

Both the unum configuration and intermediary data store information are static
and do not change once the function is deployed.
'''
try:
    with open('unum_config.json', 'r') as f:
        config = json.loads(f.read())
except Exception as e:
    raise e

# Intermediate data store is passed in via environment variables. The way to
# do this on Lambda is through the application-wide template file (i.e.,
# template.yaml in SAM).
#
# Alternatively, we can include this information entirely inside the IR (i.e.,
# unum_config.json). Doing this requires changes to the compiler.

if os.environ['FAAS_PLATFORM'] == 'gcloud':
    unum = Unum(config,
    os.environ['UNUM_INTERMEDIARY_DATASTORE_TYPE'],
    os.environ['UNUM_INTERMEDIARY_DATASTORE_NAME'],
    os.environ['FAAS_PLATFORM'],
    os.environ['GC']=="True")
else:
    unum = Unum(config,
        os.environ['UNUM_INTERMEDIARY_DATASTORE_TYPE'],
        os.environ['UNUM_INTERMEDIARY_DATASTORE_NAME'],
        os.environ['FAAS_PLATFORM'],
        os.environ['GC'])



def ingress(event):
    '''Extract user function input from the request

    unum requires a particular payload format where there is a "Data" field
    that specifies the "Source" and "Value" of the input to user functions.

    On a high level, there are two categories of data sources: http and unum
    intermediary data stores (e.g., s3, dynamodb).

    When the "Source" is "http", the "Value" field contains the actual data
    for user functions. For example,

        {
            "Data": {
                "Source": "http",
                "Value": {
                    "Purchase record": [
                        "ItemA",
                        "ItemB"
                    ]
                }
            }
        }

    We can directly pass the data in the "Value" field to the user function.

    When the "Source" is an unum intermediary data store, the "Value" field
    contains pointers to items in the data store. For example,

        {
            "Data": {
                "Source": "s3",
                "Value": [
                    "ImageResize-unumIndex-0",
                    "FaceRecognition-unumIndex-1"
                ]
            }
        }

    The pointers in the "Value" field should be passed to the `read_input()`
    API of the data store library which will read the data from the data store
    and correctly format it.

    In reality, you'll only see data sources from a data store when the
    orchestration is performing a fan-in where the function's input is the
    output of multiple upstream functions. unum stores each upstream
    function's output in a data store and invokes the fan-in function with the
    pointers when all upstream functions complete.

    The input to the fan-in function in this case is an ordered array of the
    upstream functions' outputs. The order is decided by the upstream
    functions' unum configuration. All upstream functions that are part of the
    fan-in should list outputs in the same order in their configurations.

    User function inputs are always JSON serializables.
    '''

    if event["Data"]["Source"] =="http":
        if unum.entry_function == False:
            if unum.gc == True:
                unum.my_gc_tasks = event['GC']

        return event["Data"]["Value"]
    else:

        ckpt_vals = unum.ds.read_input(event["Session"], event["Data"]["Value"])

        if unum.debug:
            print(f'[DEBUG] Read checkpoints: {event["Session"]}, {event["Data"]["Value"]}')
            print(f'[DEBUG] Input values from checkpoints: {ckpt_vals}')

        if unum.gc == True:
            gc_tasks = [ckpt["GC"] for ckpt in ckpt_vals]
            unum.my_gc_tasks = {k:v for t in gc_tasks for k,v in t.items()}

            unum.fan_in_gc = True

        input_data = [ckpt["User"] for ckpt in ckpt_vals]

        return input_data




def egress(user_function_output, event):
    '''Egress processing after user function runs

    Immediately after user function returns, unum will try to checkpoint by
    saving user function's result in a uniquely named object in the
    intermediary data store.

    If checkpoint is set to false, unum will not checkpoint.

    If checkpoint already exists before running the user function, unum will
    not checkpoint again.

    Note that if checkpoint is turned off, unum would have no way to know
    whether the user function ran before. To guarantee at-least-once
    execution, unum would have to run the user function even if it ran
    previously.
    '''

    # Compute all the outgoing edges for this execution.
    #
    # Outgoing edges are needed for GC *at the next node*.
    #
    # Computing the outgoing edges requires "dry-running" the continuations
    # because of dynamic patterns such as branch and map.
    #
    # See Unum.get_my_outgoing_edges for details on how outgoing edges are
    # computed.

    if unum.gc == True:
        gc = {
            unum.get_my_instance_name(event): unum.get_my_outgoing_edges(event, user_function_output)
        }
        checkpoint_data = {
            'GC': gc,
            "User": json.dumps(user_function_output)
        }
    else:
        checkpoint_data = {
            "User": json.dumps(user_function_output)
        }


    # Checkpoint first, before invoking continuations
    #
    # The data written into the checkpoint file is the user code result
    # (user_function_output) and the outgoing edges of this function.
    #
    # The outgoing edges are needed for GC and it must be written to the
    # checkpoint file for patterns like fan-in, because the aggregation
    # function will be invoked by only one of the branches and the invoker
    # branch cannot have complete knowledge on the outgoing branches of its sibling
    # branches.

    ret = unum.run_checkpoint(event, checkpoint_data)

    next_payload_metadata = None

    if ret == 0:
        # checkpoint on and checkpoint succeeded

        # invoke continuation with my user function results
        # t3 = time.perf_counter_ns()
        session, next_payload_vmetadata = unum.run_continuation(event, user_function_output)
        # t4 = time.perf_counter_ns()
    elif ret == -1:
        # checkpoint on and checkpoint failed due to concurrent instance beat
        # me to checkpoint.
        # Do not invoke continuations. 
        pass
    elif ret == -2:
        # checkpoint on and a checkpoint already exists before running the
        # user function, i.e., I'm a non-concurrent duplicate

        # user_function_output should have been set to the data from the
        # existing checkpoint already and I need to invoke my continuations
        # again because there's no way for me to tell whether the previous
        # instance has done that or not.
        # t3 = time.perf_counter_ns()
        session, next_payload_metadata = unum.run_continuation(event, user_function_output)
        # t4 = time.perf_counter_ns()
    elif ret == None:
        # checkpoint off

        # I have to always invoke the continuations because there's no way for
        # me to tell if there was a previous instance or if there's concurrent
        # instances.
        # t3 = time.perf_counter_ns()
        session, next_payload_metadata = unum.run_continuation(event, user_function_output)
        # t4 = time.perf_counter_ns()
    else:
        print(f'[ERROR] Unknown run_checkpoint() return value: {ret}')

    session = unum.curr_session

    # Garbage collect my parents' checkpoints
    if unum.gc == True:
        unum.run_gc()

    unum.cleanup()

    return session, next_payload_metadata


def lambda_handler(event, context):
    '''
    1. Check if a checkpoint already exists.

       This involves computing the instance's unique name and a read from the
       data store.

       This check guards against non-concurrent duplicates, such as retries or
       duplicate invocations that happen after a previous instance completes.

       1. For non-entry functions, non-concurrent duplicates might see
          checkpoints exist. Concurrent duplicates will not see checkpoints
          exist at this point.

       1. For workflow entry functions, this check is always false, even for
          non-concurrent duplicates (e.g., retries, duplicates that happen
          later), because every invocation of the entry function creates a new
          session ID.

    2. If checkpoint does not exist, run the user function and use its result
       as `user_function_output`. If checkpoint does exist, read from the
       checkpoint and use it as `user_function_output`.

    3. Once user function's output is decided, run egress: checkpoint and
       invoke continuations.

       Note that if checkpoint already exists before running the user
       function, we don't need to checkpoint again during egress.

    '''

    unum.cleanup()

    if os.environ['FAAS_PLATFORM'] == 'gcloud':
        if 'data' in event:
            input_data = base64.b64decode(event['data']).decode('utf-8')
            input_data = json.loads(input_data)

    elif os.environ['FAAS_PLATFORM'] == 'aws':
        input_data = event

    if unum.debug:
        print(f'[DEBUG] My instance name: {unum.get_my_instance_name(input_data)}. Invocation payload: {input_data}')

    ckpt_ret = unum.get_checkpoint(input_data)
    if ckpt_ret == None:
        user_function_input = ingress(input_data)
        user_function_output = user_lambda(user_function_input, context)
        if unum.debug:
            print(f'[DEBUG] User function input: {user_function_input}')
            print(f'[DEBUG] User function output: {user_function_output}')
    else:
        user_function_output = ckpt_ret

        if unum.debug:
            print(f'[DEBUG] User function output from a prior checkpoint: {user_function_output}')

    session, next_payload_metadata = egress(user_function_output, input_data)

    return user_function_output, session, next_payload_metadata