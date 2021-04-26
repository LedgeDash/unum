Given the aggregator and hvac_controller functions written in the style of
`aggregator_raw_data_no_se` and `hvac_controller_raw_data_no_se` respectively,
how do we compose them to form an application where a power consumption
monitor sends data to the aggregator to compute some aggregate statistics and
the hvac_controller uses those statistics to decide whether to turn the HVAC
system down.

![IoT_HVAC](https://github.com/LedgeDash/unum-compiler/blob/main/examples/iot_pipeline/IoT_HVAC.png)

# unum Application

Assume that the application's input is the raw data JSON document, which is
the case when the application is invoked via HTTP requests. This is the
cleanest form and don't need to deal with parsing event JSON from different
datastores and downloading data.

Challenges from `http_raw_data_handle.py`:

1. Need to know `requests.get(actuator_url, data = action)` has side effects
   so that the final IR is not empty.
2. 



# Alternative Approaches

## Asynchronous invocation, data passing via datastore

In this scenario, the power consumption monitor uploads a file to S3. The file
contains a JSON document similar to `power_consumption_data.json`. S3 is
configured to trigger the aggregator function with an S3 event when an object
is created. When the aggregator function completes writes its output to
another S3 bucket which is configured to trigger the hvac_controller function
when an object is created.

Several problems make this approach impossible

1. `aggregator_raw_data_no_se` expects the raw data JSON document, not the S3
   event JSON document
2. The currently (supported
   "destination")[https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html#invocation-async-destinations]
   for Lambda functions are SNS topics, SQS queues, Lambda functions and
   EventBridge event buses. The only way the aggregator function can write its
   output to S3 is if it explicitly specifies the bucket and creates an
   object.
3. Even if the the aggregator chooses say SNS as its output destination, or
   Lambda tomorrow supports S3 as a possible destination, the
   `hvac_controller_raw_data_no_se` is still written in a way that expects raw
   data JSON document.
4. `hvac_controller_raw_data_no_se` doesn't contain logic to call the
   actuator's API.

## HTTP requests

Synchronous or asynchronous, `aggregator_raw_data_no_se` can invoke and send
its results to `hvac_controller_raw_data_no_se` via HTTP. But this requires
changing `aggregator_raw_data_no_se` code to explicitly call
`hvac_controller_raw_data_no_se`, which renders `aggregator_raw_data_no_se`
incomposable.

Also, it doesn't solve the problem that `hvac_controller_raw_data_no_se`
doesn't contain logic to call the actuator's API.

## HTTP controller function

We can buid a controller function that invokes `aggregator_raw_data_no_se`
first via HTTP, get its output and then invokes
`hvac_controller_raw_data_no_se`.

This approach can solve several problems

1. We don't need to change the code of `aggregator_raw_data_no_se` or
   `hvac_controller_raw_data_no_se`.
2. The controller can contain logic that reads from S3 so that it can pass the
   raw data JSON to `aggregator_raw_data_no_se`
3. After getting the output of `hvac_controller_raw_data_no_se`, the
   controller can call the actuator's API.

The downside is that the controller function instance needs to synchronously
wait.

## Asynchronous invocation, data passing via Lambda runtime (destination)

You can specify another Lambda function as the destination of your output. You
can choose whether to invoke the next Lambda on success or failure. Such
invocations are asynchronous.

This approach could work in our case if we set `aggregator_raw_data_no_se`'s
destination on success to be `hvac_controller_raw_data_no_se` and then change
`hvac_controller_raw_data_no_se` to `hvac_controller_raw_data_yes_se` where it
has side effects by calling the actuator's API.

It's not a problem from Lambda's perspective if we change
`hvac_controller_raw_data_no_se` to `hvac_controller_raw_data_yes_se` where it
has side effects by calling the actuator's API. Lambda doesn't restrict
functions from having side effects.

However, the destination interface can only support simple pipelining.
Patterns such as fan-in is still impossible.