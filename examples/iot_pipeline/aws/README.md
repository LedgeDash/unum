How does the IoT application look and perform differently over different
invocation channels?

Specifically, the following AWS triggers are included in the experiment:

1. Destination (Async Lambda event queue)
2. HTTP (boto3) sync (also through the Lambda event queue?)
3. HTTP (boto3) async (Async Lambda event queue)
4. S3 (asynchronous trigger)
5. SNS (asynchronous trigger)

This experiment helps quantify the perform difference between invocation
channels, as well as showing examples of how compiled unum binaries might look
like with different substrates (e.g., over S3 or HTTP).

Each directory contains both the component function source code and the
Makefile that would generate the necessary configuration files. For example,
the SNS Makefile includes functionality to 
1. package component functions
2. deploy component functions to AWS Lambda
3. create the intermediary SNS topic
4. give permission to the SNS topic to invoke the 2nd Lambda function by
   adding a policy configuration to the 2nd Lambda function
5. subscribe the 2nd Lambda function to the intermediary SNS topic

If unum uses SNS as the intermediary invocation method for this IoT
application, then the "compiled binary" would be the component function zips,
the permission configuration to the 2nd Lambda function, all necessary `aws
cli` commands that create the necessary resources and configure them properly
and a script that execute those commands in the correct order.

Additionally, each directory contains the experiment results which includes
the raw Cloudwatch log for the experiments and 2 graphs: a scatter plot
showing the invocation latency for each iteration and a histgram showing the
distribution with the mean and standard deviation.