from app import lambda_handler as user_lambda
from ds import S3Driver, DynamoDBDriver
import json
import boto3
import uuid
import os, sys
import time, datetime
import random
import string
import re

# Connect to the intermediary data store
# If failed to connect, the function will raise an exception.
if os.environ['UNUM_INTERMEDIARY_DATASTORE_TYPE'] == "s3":
    my_return_value_store = S3Driver(os.environ['UNUM_INTERMEDIARY_DATASTORE_NAME'])
elif os.environ['UNUM_INTERMEDIARY_DATASTORE_TYPE'] == "dynamodb":
    my_return_value_store = DynamoDBDriver(os.environ['UNUM_INTERMEDIARY_DATASTORE_NAME'])
else:
    raise IOError(f'unknown return value store type')


with open('unum_config.json', 'r') as f:
    config = json.loads(f.read())

if "Next" in config:
    lambda_client = boto3.client("lambda")

my_function_name = config["Name"]



def get_random_string(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


def http_invoke_async(function, data):
    '''
    @param function string function arn
    @param data dict
    '''
    response = lambda_client.invoke(
        FunctionName=function,
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(data),
    )
    ret = response['Payload'].read()

    return

def uerror(session, name, msg):
    ''' Write error message to datastore/session_context/errors/
    '''
    if "Debug" in config and config["Debug"] == True:
        my_return_value_store.write_error(session, name, msg)


def validate_input(event):

    if "Data" not in event:
        uerror(f'No "Data" field found in event')
        return False

    if "Source" not in event["Data"] or "Value" not in event["Data"]:
        uerror(f'"Data" field must specify "Source" and "Value"')
        return False

    if "Session" not in event:
        if "Start" not in config or config["Start"] == False:
            if "Modifiers" not in event or "Invoke" not in event["Modifiers"]:
                uerror(f'Entry function failed to create session context')
                return False

    if event["Data"]["Source"] != "http" and event["Data"]["Source"] != my_return_value_store.my_type:
        uerror(f'Input data need to sent via HTTP or the intermediary data store: {event["Data"]["Source"]}')
        return False

    return True

def write_return_value(user_function_output, event, session_context):
    ''' A function's return value is written to unum data store on-demand.
        Situations that require a function to write its return value are:
        1. Checkpoint: True
        2. NextInput: Fan-in

        Functions return value are uniquely identified by its name.

        Names are implemented differently based on the underlying data store
        type (e.g., block storage, file system, database)
    '''
    # derive output file name from function name and fanout indexes
    pass

def ingress(event, context):
    ''' Extract user function input from the request
        User functions input are always JSON serializable dicts.
        The input could be passed as a pointer to the intermediary datastore.
        In the case of fan-in nodes (node after a map or parallel step), the
        input is a directory containing fan-out function outputs. Ingress needs
        to read all fileds from the directory and return an ordered list.
    '''
    data = event["Data"]
    if data["Source"] =="http":
        return data["Value"]
    else:
        return my_return_value_store.read_input(event["Session"], data["Value"])


def get_unumindex_str(fof):
    if "OuterLoop" not in fof:
        return str(fof["Index"])

    return get_unumindex_str(fof["OuterLoop"])+"."+str(fof["Index"])

def get_my_return_value_name(fof):
    if fof != {} and fof != None:
        idx = get_unumindex_str(fof)
        return my_function_name+"-unumIndex-"+idx
    else:
        return my_function_name


def _run_fanout_modifier(modifier, fof):
    ''' Run a single modifier

    @param modifier str

    Examples:
        $size = $size - 1
        $0 = $0 + 1
    '''
    if fof == {}:
        return {}
    if modifier == None:
        return fof

    if modifier == "Pop":
        if "OuterLoop" in fof:
            return fof["OuterLoop"]
        else:
            return {}
    
    exec_modifier = modifier
    # $size
    if "$size" in modifier:
        exec_modifier = exec_modifier.replace("$size", 'fof["Size"]')

    if "$0" in modifier:
        exec_modifier = exec_modifier.replace("$0", 'fof["Index"]')


    exec(exec_modifier)
    return fof


def run_fanout_modifiers(event):
    '''
    @param modifiers [str] a list of modifiers
    @param event dict input event
    '''
    if "Fan-out" not in event:
        return {}

    fof = event["Fan-out"]

    if "Fan-out Modifiers" not in config:
        return fof

    modifiers = config["Fan-out Modifiers"]

    for m in modifiers:
        fof = _run_fanout_modifier(m, fof)

    return fof

def parse_replace_unum_var(s, event):
    ''' Parse strings with unum variables and replace with python expressions
    @param s string with unum variables
    @param event input JSON

    $0, $1, ...
    *
    $size
    $ret
    '''
    pass

def evaluate_conditional(cont, event, user_function_output):
    ''' Check if the "Conditional" field in a continuation is True
    @param cont dict A continuation. It is a python dict with the following structure:
            {
                "Name": "fn",
                "Conditional": "boolean_expression"
            }

            The "Conditional" field may not exist, in which case the
            conditional is always True and the continuation should always run.
    @param event dict Function input
    @param user_function_output
    '''
    if "Conditional" not in cont:
        return True

    cond = cont["Conditional"] # cond should be a string of boolean expression

    # Need to replace all references with the actual value, not just the
    # variable name
    if "$size" in cond:
        cond = cond.replace("$size", str(event["Fan-out"]["Size"]))
    if "$0" in cond:
        cond = cond.replace("$0", str(event["Fan-out"]["Index"]))
    if "$1" in cond:
        cond = cond.replace("$1", str(event["Fan-out"]["OuterLoop"]["Index"]))

    if "$ret" in cond:
        # TODO: Depending on the return value types that we want to support,
        # we might need a more complex conversion than simply calling `str()`.
        # See the Step Functions Choice state for the types and comparison
        # operators that they support.

        if isinstance(user_function_output,str):
            cond = cond.replace("$ret", f"'{user_function_output}'")
        else:
            uerror(f'Unsupported user function return value type for Conditional')
            return False

    # raise IOError(f'{cond}, {type(cond)}; {cont["Conditional"]}')
    
    return eval(cond)


def expand_return_value_name(name, event):
    expanded_name= name

    if "$0" in expanded_name:
        expanded_name = name.replace("$0", str(event["Fan-out"]["Index"]))
    if "$1" in expanded_name:
        expanded_name = name.replace("$1", str(event["Fan-out"]["OuterLoop"]["Index"]))
    if "(" in expanded_name and ")" in expanded_name:
        exp_np = re.findall('\((.*?)\)', expanded_name)
        exp_wp = re.findall('\(.*?\)', expanded_name)
        for i in range(0,len(exp_np)):
            expanded_name = expanded_name.replace(exp_wp[i], str(eval(exp_np[i])))
    if "*" in expanded_name:
        tmp = expanded_name
        expanded_name = [tmp.replace("*",str(i)) for i in range(event["Fan-out"]["Size"])]

    return expanded_name


def expand_fanin_values(vl, event):

    # expanded_names = [item for sublist in tmp for item in sublist]
    expanded_names = []

    tmp = [expand_return_value_name(n, event) for n in vl]
    for e in tmp:
        if isinstance(e, list):
            expanded_names = expanded_names+e
        else:
            # expanded_names = expanded_names.append(e)
            expanded_names.append(e)

    return expanded_names


def egress(user_function_output, event, context):

    # Execute invoke modifiers
    # TODO

    # Compute the name of my return value
    if "Fan-out" in event:
        my_fof = event["Fan-out"]

        # If "Pop" is in the "Fan-out Modifiers", execute it first so that my
        # return value is correctly named.
        if "Fan-out Modifiers" in config and "Pop" in config["Fan-out Modifiers"]:
            # my_fof = run_fanout_modifiers(["Pop"], event["Fan-out"])
            # event["Fan-out"] = my_fof
            my_fof = _run_fanout_modifier("Pop", event["Fan-out"])
    else:
        my_fof = {}

    my_return_value_name = get_my_return_value_name(my_fof)

    # Get the session context
    if "Start" in config and config["Start"] == True:
        # If I'm the entry function, create a session context
        session_context = my_return_value_store.create_session()
    else:
        session_context = event["Session"]

    # If Checkpoint: True, write user function's output to the unum
    # intermediary data store first. Note that functions whose `NextInput` is
    # `Fan-in` should have `Checkpoint` set to True
    if "Checkpoint" in config and config["Checkpoint"] == True:
        my_return_value_store.write_return_value(session_context, my_return_value_name, user_function_output)

    # Execute Fan-out Modifiers
    # The Size and Index fields might be changed
    # if "Fan-out" in event:
    #     next_fof = run_fanout_modifiers(event)

    # If there's a next function to invoke, invoke it. Otherwise simply return
    if "Next" not in config:
        return

    # raise IOError(f'{config["Next"]}, {type(config["Next"])}')

    if config["NextInput"] == "Scalar":
        if isinstance(config["Next"], dict):
            cont = config["Next"]
            if evaluate_conditional(cont, event, user_function_output) == False:
                return

            # single function
            payload = {
                "Data": {
                    "Source": "http",
                    "Value": user_function_output
                }
            }

            payload["Session"] = session_context

            # Inherit and propagate the fan-out metadata
            if "Fan-out" in event:
                # payload["Fan-out"] = event["Fan-out"]
                next_fof = run_fanout_modifiers(event)
                if next_fof != {}:
                    payload["Fan-out"] = next_fof

            if "Fan-out" in payload:
                uerror(payload["Session"], f'{config["Name"]}-{payload["Fan-out"]["Index"]}-nextpayload-chain.json', payload)
            else:
                uerror(payload["Session"], f'{config["Name"]}-nextpayload-chain.json', payload)

            http_invoke_async(cont["Name"], payload)

        elif isinstance(config["Next"], list):
            # Send the same data to multiple functions
            for idx, cont in enumerate(config["Next"]):
                if evaluate_conditional(cont, event, user_function_output) == False:
                    continue

                payload = {
                    "Data": {
                        "Source": "http",
                        "Value": user_function_output
                    }
                }

                payload["Session"] = session_context

                payload["Fan-out"] = {
                    "Type": "Parallel",
                    "Index": idx,
                    "Size": len(config["Next"])
                }
                # Embed the outer loop metadata under ["Fan-out"]["OuterLoop"]
                if "Fan-out" in event:
                    # payload["Fan-out"]["OuterLoop"] = event["Fan-out"]
                    next_fof = run_fanout_modifiers(event)
                    if next_fof != {}:
                        payload["Fan-out"]["OuterLoop"] = next_fof

                uerror(payload["Session"], f'{config["Name"]}-{payload["Fan-out"]["Index"]}-nextpayload-parallel.json', payload)

                http_invoke_async(cont["Name"], payload)

        else:
            raise IOError(f'Next field has to be a function name or a list of function names')

    elif config["NextInput"] == "Map":
        if isinstance(config["Next"], dict):

            cont = config["Next"]
            if evaluate_conditional(cont, event, user_function_output) == False:
                return

            # Check if the user_function_output is a list
            if isinstance(user_function_output, list) == False:
                raise IOError(f'Map node needs egress data to be of type list. {type(user_function_out)}')

            for i, e in enumerate(user_function_output):
                # construct payload
                payload = {
                        "Data": {
                            "Source":"http",
                            "Value": e
                        },
                        "Session": session_context,
                        "Fan-out": {
                            "Type": "Map",
                            "Index": i,
                            "Size": len(user_function_output)
                        }
                    }

                # Embed the outer loop metadata under ["Fan-out"]["OuterLoop"]
                if "Fan-out" in event:
                    # payload["Fan-out"]["OuterLoop"] = event["Fan-out"]
                    next_fof = run_fanout_modifiers(event)
                    if next_fof != {}:
                        payload["Fan-out"]["OuterLoop"] = next_fof

                uerror(payload["Session"], f'{config["Name"]}-{payload["Fan-out"]["Index"]}-nextpayload.json', payload)

                http_invoke_async(cont["Name"], payload)

        elif isinstance(config["Next"], list):
            # TODO
            pass
        else:
            raise IOError(f'Next field has to be a function name or a list of function names')

    elif isinstance(config["NextInput"], dict) and "Fan-in" in config["NextInput"]:
        if isinstance(config["Next"], dict):
            # Functions whose `NextInput` is "Fan-in" should always has its
            # "Checkpoint" field being true. Therefore, my output should have
            # already been written to the intermediary data store.

            # We can use the `Conditional` combined with the `Wait` field to
            # control which function performs the fan-in.
            cont = config["Next"]
            if evaluate_conditional(cont, event, user_function_output) == False:
                return

            # Get the list of all names that this function needs to wait for
            # by expanding config["NextInput"]["Fan-in"]["Values"]
            expanded_names = expand_fanin_values(config["NextInput"]["Fan-in"]["Values"], event)

            uerror(event["Session"], f'{config["Name"]}-{get_random_string(5)}-fanin-expandednames.json', expanded_names)

            # Check for existence of values
            if my_return_value_store.check_values_exist(session_context, expanded_names):
                payload = {
                    "Data": {
                        "Source": my_return_value_store.my_type,
                        "Value": expanded_names
                    },
                    "Session": session_context,
                }

                if "Fan-out" in event:
                    next_fof = run_fanout_modifiers(event)
                    if next_fof != {}:
                        payload["Fan-out"] = next_fof

                if "Fan-out" in payload:
                    uerror(payload["Session"], f'{config["Name"]}-{payload["Fan-out"]["Index"]}-nextpayload-fanin.json', payload)
                else:
                    uerror(payload["Session"], f'{config["Name"]}-nextpayload-fanin.json', payload)

                http_invoke_async(cont["Name"], payload)

            else:
                if "Wait" in config["NextInput"]["Fan-in"] and config["NextInput"]["Fan-in"]["Wait"]:
                    # wait for all values to become available. This function
                    # might timeout while waiting. Timeout is controlled by
                    # the FaaS platform. unum has no control over it.
                    count = 0
                    while my_return_value_store.check_values_exist(session_context, expanded_names) == False:
                        count = count+1
                        time.sleep(1)

                        if count > 30:
                            s3_names = [f'{session_context}/{n}-output.json' for n in expanded_names]

                            response = my_return_value_store.backend.list_objects_v2(
                                            Bucket=my_return_value_store.name,
                                            Prefix=f'{session_context}/' # e.g., reducer0/
                                        )
                            all_keys = [e["Key"] for e in response["Contents"]]

                            raise IOError(f'{my_return_value_store.check_values_exist(session_context, expanded_names)}, {expanded_names}, {all_keys}, {response}')

                    if my_return_value_store.check_values_exist(session_context, expanded_names):
                        payload = {
                            "Data": {
                                "Source": my_return_value_store.my_type,
                                "Value": expanded_names
                            },
                            "Session": session_context,
                        }

                        if "Fan-out" in event:
                            next_fof = run_fanout_modifiers(event)
                            if next_fof != {}:
                                payload["Fan-out"] = next_fof

                        if "Fan-out" in payload:
                            uerror(payload["Session"], f'{config["Name"]}-{payload["Fan-out"]["Index"]}-nextpayload-fanin.json', payload)
                        else:
                            uerror(payload["Session"], f'{config["Name"]}-nextpayload-fanin.json', payload)

                        http_invoke_async(cont["Name"], payload)
                else:
                    return


        elif isinstance(config["Next"], list):
            # TODO
            pass
        else:
            raise IOError(f'Next field has to be a function name or a list of function names')
    else:
        raise IOError(f'Unknown NextInput value: {config["NextInput"]}')


def get_waiter_list(cw, event):
    wl = []
    for w in cw:
        ret = {"Prefix": w["Prefix"]}
        try:
            idx = w["Index"]
            my_idx = event["UnumMetadata"]["Index"]
            if isinstance(my_idx, str) == False:
                my_idx = str(my_idx)
            idx.replace("$MyIndex", my_idx)
            wait_idx = eval(idx)
            ret["Index"] = wait_idx
        except Exception as e:
            pass

        wl.append(ret)
    return wl

def lambda_handler(event, context):

    if validate_input(event) == False:
        return {
            "Error": "Invalid unum input"
        }

    user_function_input = ingress(event, context)

    if "Session" in event:
        rs = get_random_string(5)
        uerror(event["Session"], f'{config["Name"]}-{rs}-input.json', event)
        uerror(event["Session"], f'{config["Name"]}-{rs}-userfunctioninput.json', user_function_input)
    
    user_function_output = user_lambda(user_function_input, context)
    
    egress(user_function_output, event, context)

    return user_function_output
