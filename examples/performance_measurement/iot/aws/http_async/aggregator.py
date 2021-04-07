# Compatible Triggers:
# This version expects the raw input in the `event` input parameter.
# Therefore, it can only be invoked via HTTP requests (synchronous or
# asynchronous). This means the compatible triggers are:
# 1. boto3 sync
# 2. boto3 async
# 3. aws lambda invoke
#
# Incompatible triggers include
# 1. S3 events
# 2. SNS messages
# 3. Destination
#
# Next Function Invocation Method:
# This version invokes hvac_controller asynchronously via boto3

import json
from datetime import datetime
from functools import reduce
import boto3

client = boto3.client('lambda')

def to_datetime(elem):
	if len(elem) != 1:
		raise

	time_str = list(elem)[0]
	time = datetime.fromisoformat(time_str)

	return (time, elem[time_str])

def lambda_handler(event, context):
    series = event
    num_elem = len(series)

    series = [to_datetime(elem) for elem in series]

    delta = (series[1][0] - series[0][0]).total_seconds()/60 # difference between 2 timestamps in minutes

    total_time_in_mins = delta*num_elem
    total_power_consumption = reduce(lambda x, y: x+y[1], series, 0)

    average_power_consumption = total_power_consumption/total_time_in_mins

    ret = {
        "starting_tsp": datetime.isoformat(series[0][0]),
        "ending_tsp": datetime.isoformat(series[-1][0]),
        "total_time": total_time_in_mins,
        "total_power_consumption": total_power_consumption,
        "average_power_consumption": average_power_consumption
    }


    client.invoke(
        FunctionName='hvac_controller-http-async',
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(ret),
    )

    # response = client.invoke(
    #     FunctionName='hvac_controller-http-async',
    #     InvocationType='Event',
    #     LogType='None',
    #     Payload=json.dumps(ret),
    # )

    # return {
    #     'StatusCode': response['StatusCode']
    # }
