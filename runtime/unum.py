from app import lambda_handler as user_lambda
from ds import S3Driver, DynamoDBDriver
import json
import boto3
import uuid
import os
import time, datetime

with open('unum_config.json', 'r') as f:
    config = json.loads(f.read())

ds_type = os.environ['UNUM_INTERMEDIARY_DATASTORE_TYPE']
ds_name = os.environ['UNUM_INTERMEDIARY_DATASTORE_NAME']

if ds_type == "s3":
    my_return_value_store = S3Driver(ds_type,ds_name)
elif ds_type == "dynamodb":
    my_return_value_store = DynamoDBDriver(ds_type,ds_name)
else:
    raise IOError(f'unknown return value store type')

if "Next" in config:
    lambda_client = boto3.client("lambda")

my_function_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']

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

def ingress(event, context):
    ''' Extract user function input from the request
        User functions input are always JSON serializable dicts.
        The input could be passed as a pointer to the intermediary datastore.
        In the case of fan-in nodes (node after a map or parallel step), the
        input is a directory containing fan-out function outputs. Ingress needs
        to read all fileds from the directory and return an ordered list.
    '''
    if "Data" not in event:
        raise IOError(f'No Data field found in event')

    data = event["Data"]
    val = data["Value"]

    if data["Source"] =="http":
        return val
    elif data["Source"] == my_return_value_store.my_type:
        # Check whether the input is a context (fan-in) or a scalar
        # Scalar value should be read and return as is
        # Context should read all items and return them in order as a list

        if "Context" in val:
            #TODO: If both "Context" and "Key" exist
            if "Keys" in val:
                return my_return_value_store.read_fanin_context(data["Value"]["Context"], keys=val["Keys"])
            else:
                return my_return_value_store.read_fanin_context(data["Value"]["Context"])
 
        elif "Keys" in val:
            pass
        else:
            raise IOError(f'Ingress via data store missing value pointer information: {data}')

    else:
        raise IOError(f'Unknown input data source: {data["Source"]}')

    # if data["Source"] =="http":
    #     return val
    # elif data["Source"] == "s3":
    #     if "Fan-in" in val:
    #         return
    #     else:
    #         return
    # elif data["Source"] == "dynamodb":
    #     if "Fan-in" in val:
    #         return
    #     else:
    #         return
    # else:
    #     raise IOError(f'Unknown input data source: {data["Source"]}')

def egress(user_function_output, event, context):
    # Write user_function_output to storage if I need to fan-in or need to checkpoint the output
    # write location is given in event["UnumMetadata"].
    # TODO

    # If there's a next function to invoke, invoke it. Otherwise simply return
    if "Next" in config:
        if config["NextInput"] == "Scalar":
            if isinstance(config["Next"],str):
                # single function
                payload = {
                    "Data": {
                        "Source": "http",
                        "Value": user_function_output
                    }
                }

                # preserve the UnumMetadata field in event
                if "UnumMetadata" in event:
                    payload["UnumMetadata"] = event["UnumMetadata"]

                http_invoke_async(config["Next"], payload)

            elif isinstance(config["Next"], list):
                # fan-out the same scalar to multiple functions
                # create a subdirectory for fan-out functions to write their outputs to
                # TODO

                # Pass the subdirectory in the request payload under "UnumMetadata"
                payload = {
                    "Data": {
                        "Source": "http",
                        "Value": user_function_output
                    }
                }
                # preserve the UnumMetadata field in event
                if "UnumMetadata" in event:
                    payload["UnumMetadata"] = event["UnumMetadata"]

                # Invoke each function
                for f in config["Next"]:
                    http_invoke_async(f, payload)
            else:
                raise IOError(f'Next field has to be a function name or a list of function names')

        elif config["NextInput"] == "Map":
            if isinstance(config["Next"],str):
                # Check if the user_function_output is a list
                if isinstance(user_function_output, list) == False:
                    raise IOError(f'Map node needs egress data to be of type list. {type(user_function_out)}')

                # Allocate a subcontext in the intermediary datastore
                context = my_return_value_store.create_fanin_context()

                # Invoke one instance of the next function for each element of the array
                for i, e in enumerate(user_function_output):
                    # construct payload
                    payload = {
                                "Data": {
                                    "Source":"http",
                                    "Value": e
                                },
                                "UnumMetadata": {
                                    "ReturnValueStore": {
                                        "Type": my_return_value_store.my_type,
                                        "Name": my_return_value_store.name,
                                        "Context": context
                                    },
                                    "Index": i,
                                    "FanoutSize": len(user_function_output)
                                }
                            }
                    http_invoke_async(config["Next"], payload)

                return

            elif isinstance(config["Next"], list):
                # TODO
                pass
            else:
                raise IOError(f'Next field has to be a function name or a list of function names')

        elif config["NextInput"] == "Fan-in":
            if isinstance(config["Next"],str):
                # write my output to the ReturnValueStore
                if ("UnumMetadata" not in event) or ("ReturnValueStore" not in event["UnumMetadata"]):
                    raise IOError(f'Fan-in node missing UnumMetadata and ReturnValueStore in event: {event}')

                my_return_value_store.write_fanin_context(user_function_output,
                    my_function_name,
                    event["UnumMetadata"]["ReturnValueStore"]["Context"],
                    event["UnumMetadata"]["Index"],
                    event["UnumMetadata"]["FanoutSize"])

                # check if the WaitFor functions have completed by checking
                # whether their outputs exist in the ReturnValueStore
                if config["WaitFor"] == "Map":
                    if event["UnumMetadata"]["Index"]+1 == event["UnumMetadata"]["FanoutSize"]:
                        # NOTE: only the last fan-out function waits
                        keys = []
                        while len(keys) < event["UnumMetadata"]["FanoutSize"]:
                            keys = my_return_value_store.list_fanin_context(event["UnumMetadata"]["ReturnValueStore"]["Context"])

                            if len(keys) == event["UnumMetadata"]["FanoutSize"]:
                                break
                            elif len(keys) > event["UnumMetadata"]["FanoutSize"]:
                                raise IOError(f'More fan-out function return values than fan-out size')

                            time.sleep(0.1)

                    # Invoke the next function if WaitFor functions have completed.
                    # Otherwise simply return
                        payload = {
                            "Data": {
                                "Source": my_return_value_store.my_type,
                                "Value": {
                                    "Name": my_return_value_store.name,
                                    "Context": event["UnumMetadata"]["ReturnValueStore"]["Context"]
                                }
                            },
                            "UnumMetadata": {
                                "Index": event["UnumMetadata"]["Index"],
                                "FanoutSize": event["UnumMetadata"]["FanoutSize"]
                            }
                        }

                        http_invoke_async(config["Next"], payload)
                else:
                    # Wait for specific outputs
                    waitfor = get_waiter_list(config["WaitFor"], event)
                    output_list = []

                    for w in waitfor:
                        counter = 0
                        exist, fn = check_prefix_index_exist(event["UnumMetadata"]["ReturnValueStore"]["Context"], w["Prefix"], w["Index"])
                        while exist == False:
                            time.sleep(1)
                            counter = counter+1
                            if counter >= 20:
                                break
                            exist, fn = check_prefix_index_exist(event["UnumMetadata"]["ReturnValueStore"]["Context"], w["Prefix"], w["Index"])
                        if fn != None:
                            output_list.append(fn)

                    # Invoke the next function if WaitFor functions have completed.
                    payload = {
                        "Data": {
                            "Source": my_return_value_store.my_type,
                            "Value": {
                                "Name": my_return_value_store.name,
                                "Context": event["UnumMetadata"]["ReturnValueStore"]["Context"],
                                "Keys": output_list
                            }
                        },
                        "UnumMetadata": {
                            "Index": event["UnumMetadata"]["Index"],
                            "FanoutSize": event["UnumMetadata"]["FanoutSize"]
                        }
                    }

                    http_invoke_async(config["Next"], payload)

            elif isinstance(config["Next"], list):
                # TODO
                pass
            else:
                raise IOError(f'Next field has to be a function name or a list of function names')
            return
        else:
            raise IOError(f'Unknown NextInput value: {config["NextInput"]}')

    return

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

    user_function_input = ingress(event, context)
    
    user_function_output = user_lambda(user_function_input, context)
    
    egress(user_function_output, event, context)

    return user_function_output
