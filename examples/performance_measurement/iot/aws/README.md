Measure the latency of various AWS triggers:

1. Destination (Async Lambda event queue)
2. HTTP (boto3) sync (also through the Lambda event queue?)
3. HTTP (boto3) async (Async Lambda event queue)
4. S3 (asynchronous trigger)
5. SNS (asynchronous trigger)


I want to measure from when the 1st Lambda invokes the second Lambda:

1. Destination: When the 1st Lambda returns
2. HTTP (boto3) sync: When the 1st Lambda makes the boto3 calls
3. HTTP (boto3) async: When the 1st Lambda makes the boto3 calls
4. S3: When the 1st Lambda finishes uploading to S3
5. SNS: When the 1st Lambda finishes writing to SNS

to when the 2nd Lambda starts running.

I use the IoT app for this experiment because it has a simple pipeline with
only 2 functions. The computation of each individual function doesn't matter
because the latency we care about does not include those work.

Secondly, the IoT app can showcase the lack of function reusability under the
current Lambda interface. Specificially, the invocation method is coupled in
the function code. The 1st function needs to include code to explicitly use
boto3 or S3 or SNS. Destination is much better but still not sufficient (as
I'll show in the Hello Sequence case later). The 2nd function also includes
code that's aware of the invocation method. It needs to explicitly read from
S3 and SNS. HTTP and Destination requests (through HTTP endpoint and Lambda
event queue) are better.

The invocation method of the 1st function in the IoT application /pipeline is
also "hard-coded". Does SAM or the Lambda application page provide anything
that can make the 1st function interoperable across different invocation
methods?


Another 2 scenarios worth trying out:
1. S3 with whatever is the fastest. So basically don't rely on S3 for event
   triggers
2. controller Lambda function with boto3 sync (boto3 async doesn't work here
   because the controller function cannot get the response)

## Plan

Implement individual applications separately.

Measure the latency

Showcase the lack of function reusability

Implement with unum runtime to experiment with the unum data model and
egress+ingress wrapper.

# Hello Sequence

Similar 
