# Error Handling

## Background: Retry

### Lambda

In Lambda and SAM, the number of retries is specified under
`EventInvokeConfiguration` as part of forwarding success and failure (See
[SAM's `AWS::Serverless::Function`property
definition](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-resource-function.html),
[SAM's
`EventInvokeConfiguration`](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-property-function-eventinvokeconfiguration.html)
for details on how to forward a lambda's result and error to another lambda).
For example,

```yaml
Type: AWS::Serverless::Function
Properties:
    EventInvokeConfig:
        MaximumEventAgeInSeconds: 60
        MaximumRetryAttempts: 2
        DestinationConfig:
            OnSuccess:
                Type: SQS
                Destination: arn:aws:sqs:us-west-2:012345678901:my-queue
            OnFailure:
                Type: Lambda
                Destination: !GetAtt DestinationLambda.Arn

```

Note that [MaximumRetryAttempts supports only
0-2](https://aws.amazon.com/about-aws/whats-new/2019/11/aws-lambda-supports-max-retry-attempts-event-age-asynchronous-invocations/).
*That is Lambda only allows 0-2 retries for asynchronous invocations*.

Moreover, Lambda does not retry for synchronous invocations. Testing a
function from the web console, for instance, is synchronous and failures do
not lead to retries.

A retry will have the same `aws_request_id` as the original execution. Here's
whati's in the `context` argument:

```python
{
    'aws_request_id': '16574059-11f3-4b34-9595-6ded3c1a59b6',
    'log_group_name': '/aws/lambda/unum-catch-SecondFunction-9OnzpWLAbhA9',
    'log_stream_name': '2022/01/04/[$LATEST]292d0c31dfeb4b7a83583b35e7c9eb84',
    'function_name': 'unum-catch-SecondFunction-9OnzpWLAbhA9',
    'memory_limit_in_mb': '128',
    'function_version': '$LATEST',
    'invoked_function_arn': 'arn:aws:lambda:us-west-1:746167823857:function:unum-catch-SecondFunction-9OnzpWLAbhA9',
    'client_context': None,
    'identity': <__main__.CognitoIdentity object at 0x7f47e5720760>,
    '_epoch_deadline_time_in_ms': 1641336875895
}
```

However, for this to work, functions need to first save the `aws_request_id`
in a data store persistent across invocations (e.g., DynamoDB) so that a retry
execution can compare and know that it is a retry.

### Step Functions

In Step Functions, retry behavior is specified as a property of a state and
only works for `Task` and `Parallel` states (See "Retrying after an error" in
[Error handling in Step
Functions](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)).
For example,

```json
"X": {
   "Type": "Task",
   "Resource": "arn:aws:states:us-east-1:123456789012:task:X",
   "Next": "Y",
   "Retry": [
        {
           "ErrorEquals": [ "States.TaskFailed" ],
           "IntervalSeconds": 3,
           "MaxAttempts": 2,
           "BackoffRate": 1.5
        }
    ]
}
```

Step Functions retries do not rely on Lambda's retry functionality. In fact,
retry lambda executions have different `aws_request_id` values in the
`context` (confirmed with the `RetryOnlySF` in
`experiments/catch/step-fucntions`).

When a state has a `Retry` field, you will see the execution log entering the
state (`TaskStateEntered`) and then for the original execution and each
subsequent retry a series of `LambdaFunctionScheduled`,
`LambdaFunctionStarted` and `LambdaFunctionFailed`, until a
`LambdaFunctionSucceeded` followed by a `TaskStateExited` or
`ExecutionFailed`.

### Unum (old)

The first version of Unum relies on Lambda's retry for error handling. That
is, failed lambdas are automatically retried by Lambda, whether the failure
happened during user code or Unum runtime (in fact, from Lambda's perspective,
"user code" from Unum's perspective and Unum runtime code are all *user*
code). Unum does not initiate the retry process; Lambda does. A Unum function execution
does not distinguish whether it's a retry or not. The runtime focuses on
guaranteeing consistency (i.e., exactly-one-result) using checkpoints such
that retry executions do not run user code again if a prior execution already
produced a result.

The number of retry attempts is specified in the template and configured
during function creation. For example, in the generated `template.yaml` file,
developers can add `EventInvokeConfig`:

```yaml
Resources:
  FirstFunction:
    Properties:
      CodeUri: first/
      Handler: wrapper.lambda_handler
      Policies:
        - AWSLambdaRole
        - AmazonDynamoDBFullAccess
        - AmazonS3FullAccess
        - AWSLambdaBasicExecutionRole
      Runtime: python3.8
      EventInvokeConfig:
          MaximumRetryAttempts: 1
    Type: AWS::Serverless::Function
```

This is piggybacking on Lambda or SAM's support to configure the number of
retry attempts. Alternatively, we can add a field in `unum-template.yaml` and
have the frontend compiler generate the `EventInvokeConfig` field in the
`template.yaml`. If not specified, the default number of retries is 2.

Synchronous invocations of the entry function can simply return the error
messgae if failed. Lambda actually does not retry for synchronous invocations.



## Background: Catch


### Lambda Failure Destination

Only trigger failure destination after all retry attempts for asynchronous
invocations? What about sychronous?

### Step Functions Catch

If there is a `Retry` field in the state, Step Functions [only execute `Catch`
field if retries fail to resolve the
error](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html).





An important assumption when reasoning about error handling is that the
orchestrator mostly does not fail. For example, for retries to work, Unum
relies on the assumption that Lambda will indeed retry the specified number of
times. If Lambda fails to do that, there's very little that Unum can do.
Similarly, when a Step Functions definition specifies that a state should
retry X number of times, it relies on the Step Functions not crashing to do
the retry.


TBA: When Step Functions fail in the presence of `Catch` logic.

TBA: When Lambda failure destination fails.


