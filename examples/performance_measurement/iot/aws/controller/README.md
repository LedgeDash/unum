Controller latency measurement is from the START timestamp to the END
timestamp of the iot-controller function.

http_async measurement is from the START timestamp of the
aggregator-http-async to the END timestamp of the hvac_controller-http-async
timestamp.


# Strange latency behavior with boto3

I was expecting HTTP Async case to be faster than the controller case because

1. There's no round trip
2. Instead of 2 synchronous HTTP requests, there's only 1 asynchronous HTTP request

However, I noticed that the aggregator-async function somehow has an average runtime of 163ms! While the iot-controller function has an average runtime of 81ms.

Initially, I thought that the stack of boto3 sync and async calls must be different and that difference must somehow caused the difference. However, later I found out that in the `controller.py`, if I remove reading the response of a boto3 HTTP request, i.e.,

```python
def lambda_handler(event, context):

	response = client.invoke(
        FunctionName='aggregator-controller',
        LogType='None',
        Payload=json.dumps(event),
    )

	ret = response['Payload'].read()

	response = client.invoke(
        FunctionName='hvac_controller-controller',
        LogType='None',
        Payload=ret,
    )

	ret = response['Payload'].read()

	return ret
```

remove the last 2 lines of the above code, the latency of the iot-controller function jumps to over 200ms!

Similarly, when I add code in `aggregator.py` for the asynchronous HTTP case, i.e., 

```python
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


    response = client.invoke(
        FunctionName='hvac_controller-http-async',
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(ret),
    )

    return response['Payload'].read()
```

add the last line, the runtime somehow decreases to 40ms...

In fact, I have to `read()` from the `botocore.response.StreamingBody` object,
[which is in the `Payload` field of the
response](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.invokes).
Otherwise the latency is significantly higher.