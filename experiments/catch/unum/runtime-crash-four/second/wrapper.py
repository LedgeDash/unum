import json
import os
import time

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

unum = Unum(config,
    os.environ['UNUM_INTERMEDIARY_DATASTORE_TYPE'],
    os.environ['UNUM_INTERMEDIARY_DATASTORE_NAME'],
    os.environ['FAAS_PLATFORM'])

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
        return event["Data"]["Value"]
    else:
        # print(f'Reading user function input from {unum.ds.my_type}')
        # print(f'Target files are: {event["Data"]["Value"]}')
        return unum.ds.read_input(event["Session"], event["Data"]["Value"])



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

    If 

    --
    Checkpoint, construct payload for continuation, invoke continuation
    '''

    # Checkpoint first, before invoking continuations
    t1 = time.perf_counter_ns()
    ret = unum.run_checkpoint(event, user_function_output)
    t2 = time.perf_counter_ns()

    next_payload_metadata = None
    
    if ret == 0:
        # checkpoint on and checkpoint succeeded

        # invoke continuation with my user function results
        t3 = time.perf_counter_ns()
        session, next_payload_metadata = unum.run_continuation(event, user_function_output)
        t4 = time.perf_counter_ns()
    elif ret == 1:
        # checkpoint on and checkpoint failed due to concurrent instance beat
        # me to checkpoint.

        # Do not invoke continuations. 
        pass
    elif ret == 2:
        # checkpoint on and a checkpoint already exists before running the
        # user function, i.e., I'm a non-concurrent duplicate

        # user_function_output should have been set to the data from the
        # existing checkpoint already and I need to invoke my continuations
        # again because there's no way for me to tell whether the previous
        # instance has done that or not.
        t3 = time.perf_counter_ns()
        session, next_payload_metadata = unum.run_continuation(event, user_function_output)
        t4 = time.perf_counter_ns()
    elif ret == None:
        # checkpoint off

        # I have to always invoke the continuations because there's no way for
        # me to tell if there was a previous instance or if there's concurrent
        # instances.
        t3 = time.perf_counter_ns()
        session, next_payload_metadata = unum.run_continuation(event, user_function_output)
        t4 = time.perf_counter_ns()
    else:
        print(f'Unknown run_checkpoint() return value: {ret}')

    session = unum.curr_session

    unum.cleanup()

    if unum.debug:
        print(f'[Unum Wrapper.egress]run_checkpoint: {t2-t1}; run_continuation: {t4-t3}')

    return session, next_payload_metadata

def handle_error(event, user_function_input, context, user_exception):
    ''' User code crashed

    Retry if the function is configured with retry and Retry Number is less
    than or equal to the limit. Retry = invoke myself again.s
    '''
    import traceback

    def invoke_lambda(data, function_name):
        import boto3
        lambda_client = boto3.client("lambda")

        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event',
            LogType='None',
            Payload=json.dumps(data),
        )
        ret = response['Payload'].read()

        return

    if "Retry" in config:
        if "Retry Number" in event:
            # This was a retry execution
            if event["Retry Number"] <= config["Retry"]:
                input_to_retry = event
                input_to_retry["Retry Number"] = event["Retry Number"]+1
                input_to_retry["ErrorType"] = "User"
                input_to_retry["ErrorMessage"] = str(user_exception)
                input_to_retry["StackTrace"] = traceback.format_exc()
                invoke_lambda(input_to_retry, context.function_name)
            else:
                print(f'Function {config["Name"]} fails after {event["Retry Number"]} retries')
                print(f'Invoking catcher')

                if "Next" in config and isinstance(config["Next"], list):
                    for n in config["Next"]:
                        if n["InputType"] == "Error":
                            catcher_name = n["Name"]
                            invoke_lambda(event, catcher_name)
        else:
            input_to_retry = event
            input_to_retry["Retry Number"] = 1
            input_to_retry["ErrorType"] = "User"
            input_to_retry["ErrorMessage"] = str(user_exception)
            input_to_retry["StackTrace"] = traceback.format_exc()
            invoke_lambda(input_to_retry, context.function_name)
    else:
        print(f'Function {config["Name"]} fails without retry')
    


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

    print(event)

    if "Retry Number" in event:
        if event["Retry Number"] > config['Retry']:
            print(f'This is the {event["Retry Number"]} retry. Retry limit exhausted. Terminating..')
            print(event)
            return event["ErrorMessage"], event["Session"]

    if unum.debug:

        t1 = time.perf_counter_ns()
        ckpt_ret = unum.get_checkpoint(event)
        t2 = time.perf_counter_ns()

        if ckpt_ret == None:
            user_function_input = ingress(event)

            t3 = time.perf_counter_ns()
            try:
                user_function_output = user_lambda(user_function_input, context)
            except Exception as e:
                handle_error(event, user_function_input, context, e)
            else:
                pass
            finally:
                pass
            
            t4 = time.perf_counter_ns()

        else:
            user_function_output = ckpt_ret

        t5 = time.perf_counter_ns()
        session, next_payload_metadata = egress(user_function_output, event)
        t6 = time.perf_counter_ns()

        print(f'[Unum Wrapper] get_checkpoint:{t2-t1}; user_lambda: {t4-t3}; egress: {t6-t5}')

        return user_function_output, session, next_payload_metadata

    else:

        ckpt_ret = unum.get_checkpoint(event)
        if ckpt_ret == None:
            user_function_input = ingress(event)

            try:
                user_function_output = user_lambda(user_function_input, context)
            except Exception as e:
                handle_error(event, user_function_input, context, e)
            else:
                session, next_payload_metadata = egress(user_function_output, event)
                return user_function_output, session, next_payload_metadata
                
            finally:
                pass
        else:
            user_function_output = ckpt_ret
            

        # print(f'[Wrapper] user_function_input: {user_function_input}')

        # if "Session" in event:
        #     rs = get_random_string(5)
        #     uerror(event["Session"], f'{config["Name"]}-{rs}-input.json', event)
        #     uerror(event["Session"], f'{config["Name"]}-{rs}-userfunctioninput.json', user_function_input)

        