# Architecture

Fan out to many parallel pipelines. Each pipeline has 3 Lambdas. Each Lambda
returns a fixed amount of data.

In the case of unum, initial fan-out is performed by a separate Lambda
(`unum_map`) via asynchronous HTTP requests. The Lambdas in the pipelines do
not send their outputs back to `unum_map`; Instead, they directly invoke the
next stage Lambda via asynchronous HTTP requests. The last Lambda in each
pipeline writes its result to an DynamoDB item. The item is created by
`unum_map`, unique to each invocation, and passed along to the last Lambdas in
the pipelines.

In the case of Step Functions, initial fan-out is performed by the SF
instance. Every Lambda in the pipelines send their outputs back to the SF and
SF invokes the next stage. The last Lambdas in the pipelines just send their
results back to SF and do not write to DynamoDB.
