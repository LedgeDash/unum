# Error Handling

## Background: Retry

[Example
scenario](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
for demonstrating the utility of retry:

A customer requests a username. The first time, your customer’s request is
unsuccessful. Using a Retry statement, you can have Step Functions try your
customer's request again. The second time, your customer’s request is
successful. 

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


## Background: Catch

[Example
scenario](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
for demonstrating the utility of catch:

A customer requests an unavailable username. Using a Catch statement, you have
Step Functions suggest an available username. If your customer takes the
available username, you can have Step Functions go to the next step in your
workflow, which is to send a confirmation email. If your customer doesn’t take
the available username, you have Step Functions go to a different step in your
workflow, which is to start the sign-up process over.

### Step Functions Catch

`Task`, `Map` and `Parallel` states support `Catch`. `Catch` matches on error
types and jumps to a *state* in the state machine.

If there is a `Retry` field in the state, Step Functions [only execute `Catch`
field if retries fail to resolve the
error](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html).

Based on the `TwoCatchSF` experiment in `experiments/catch/step-fucntions`, if
the catcher is a Lambda function, its inputs are:

```python
{
    'Error': 'RuntimeError',
    'Cause': '{"errorMessage": "No active exception to reraise", "errorType": "RuntimeError", "stackTrace": ["  File \\"/var/task/app.py\\", line 3, in lambda_handler\\n    raise\\n"]}'
}
```

### Lambda Failure Destination

Lambda supports triggering other services, including another Lambda function,
on failure. Use the [`DestinationConfig` under `EventInvokeConfig`](https://do
cs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-lambda-
eventinvokeconfig-destinationconfig.html) to add error (or results)
forwarding. See Background: Retry for an example.

If the failed lambda is configured with retries, the failure destination
lambda will be triggered only when all retries fail.

The failure destination lambda receives the following as the input `event`:

```python
{
    'version': '1.0',
    'timestamp': '2022-01-05T22:01:09.159Z',
    'requestContext': {
        'requestId': 'd57edd62-2b30-4db9-bf45-adb4bd8c37fa',
        'functionArn': 'arn:aws:lambda:us-west-1:746167823857:function:unum-catch-SecondFunction-9OnzpWLAbhA9:$LATEST',
        'condition': 'RetriesExhausted',
        'approximateInvokeCount': 2
    },
    'requestPayload': {
        'Data': {
            'Source': 'http',
            'Value': {}
        },
        'Session': '039a98b6-f051-4a8f-be73-b60da1ca954b'
    }, 
    'responseContext': {
        'statusCode': 200,
        'executedVersion': '$LATEST',
        'functionError': 'Unhandled'
    },
    'responsePayload': {
        'errorMessage': 'No active exception to reraise',
        'errorType': 'RuntimeError',
        'stackTrace': ['  File "/var/task/wrapper.py", line 233, in lambda_handler\n    user_function_output = user_lambda(user_function_input, context)\n', '  File "/var/task/app.py", line 4, in lambda_handler\n    raise\n']
    }
}

```

`requestContext` describes the last request to the *failed* lambda before the
failure destination is triggered:

* `requestId`: the AWS request ID of the last request to the *failed* lambda
(in this case   `arn:aws:lambda:us-west-1:746167823857:function:unum-catch-
SecondFunction-9OnzpWLAbhA9`)   before all retries are exhausted and failure
destination triggered.

* `functionArn`: AWS ARN of the *failed* lambda

* `condition`: why the failure destination is triggered

* `approximateInvokeCount`: How many time the *failed* lambda run

`requestPayload` is the input data to the failed lambda. Because
`unum-catch-SecondFunction-9OnzpWLAbhA9` is a Unum function, the input payload
includes a `Session` field.

`responseContext`: The response from *AWS Lambda*. This is the response a
client would get if *synchronously* invoking
`unum-catch-SecondFunction-9OnzpWLAbhA9` from the command line.

`responsePayload`: The response from *AWS Lambda*. This is the response a
client would get *to its `<outfile>`* (see `aws lambda invoke help`) if
*synchronously* invoking `unum-catch-SecondFunction-9OnzpWLAbhA9` from the
command line.

## Error Handling in Unum

Developers can express workflow catch and retry behaviors in Step Functions
and Unum handles them similarly.

Unum runtime wraps user code with `try .. catch`. If user code throws an
exception (that is a Python exception), Unum runtime catches the exception and
retries user code by asychronously invoking the same lambda (i.e., itself)
again and embedding retry metadata in the input payload. The retry metadata
has the following format:

```json
{
  "Retry Number": 1,
  "ErrorType": "User",
  "ErrorMessage":"<Excpetion description>",
  "StackTrace":""
}
```

Each retry will increment the "Retry Number" field by 1. The Unum runtime on
the retry execution will check if the "Retry Number" is less than or equal to
the user-specified maximum. If yes, it will attempt to run the user code
again. If not, Unum will trigger the catcher (if configured) or abort the
workflow execution.

In the *rare* case of the crash happening while Unum runtime is executing
(e.g., Lambda crashed), Unum uses Lambda failure destination to trigger the
*Unum failure destination lambda*. From the input payload, the Unum failure
destination lambda can know

1. which lambda crashed (from `requestContext: functionArn`)

2. was the crash due to Unum runtime bug or Lambda errors (from
`responsePayload`)

3. how many times has the failed lambda been retried (from `requestPayload`
because Unum retries will have retry metadata)

The failure destination lambda can then retries the lambda by invoking it
again if the number of the retries is still under the maximum limit. It
similarly adds or updates the retry metadata in the input payload.

From Lambda's perspective, if user code crashes, Unum runtime will handle the
retry and Lambda won't see any errors. Cloudwatch Logs won't record the
errors. If crashes happen outside of user code, Lambda will see the error,
Cloudwatch Logs will record the error and Lambda is the one that triggers the
Unum failure destination lambda.

Catch allows developers to trigger another lambda when errors happen. Unum
piggybacks on the branch support in the IR to support catch as a catcher is
just an edge in the directed graph, and uses a special `Error` keyword as the
`InputType`. For example, the following IR triggers an `Abort` function as the
catcher,

```yaml
Next:
  - Name: NextStepOnSuccess
    InputType: Scalar
  - Name: Abort
    InputType: Error
```

The Unum runtime will scan the IR for catchers and invoke the catcher when
retries are exhausted. Specifically, if the error happens in user code, the
egress on the execution where the error happens can invoke the catcher. If the
error happens outside of user code, the Unum failure destination lambda will
retry the failed lambda and Unum runtime on the retry execution will invoke
the catcher without running user code. That is the Unum failure destination
lambda do not need to know anything about the catcher; it simply retries the
failed lambda.

When a function fails after all retries, Unum records the failure message in
the intermediate data store as the that function's output.

For functions that fail without catchers, we have two choices:

1. We can have the failed function write to something like
`session/FINALRESULT/MyFunctionName` in the intermediate data store, then just
fail the workflow right there since there's nothing more to run *based on the
workflow defined by the developer*.

2. Still invoke the next function but with the error message as its input.

Step Functions' behavior is #1. Furthermore, #1 has the benefit of 

1. cost savings as workflows can abort right after an unrecoverable failure
without running downstream functions.

2. clear separation of normal workflow from error handling workflow logic. The
next function is not expected to handle the error of the previous function. If
error handling logic is desirable, developers can and should specify a
catcher.

### A quick discussion

An important assumption when reasoning about error handling is that the
orchestrator does not fail. For example, when a Step Functions definition
specifies that a state should retry X number of times, it relies on the Step
Functions not crashing to do the retry. Similarly, for `Catch` to work,
developers rely on Step Functions not crashing.

Compared with orchestrator design where the orchestrator is assumed to be
reliable, Unum assumes that the Unum runtime is bug-free and do not crash.
Based on this assumption, Unum runtime catches user code error as user code is
where most errors are expected to happen. Moreover, Unum assumes that the
underlying FaaS engine (e.g., Lambda) is mostly reliable. That is, function
instances rarely crash. And in the rare case that functions do crash Unum
additionally uses the failure destination triggers as a back-up. The Unum
failure destination lambda does very little and mainly invokes the failed
function again as a way to give control back to the Unum runtime.

This design is extensible in a few ways:

1. The error metadata can be an array of past errors instead of just the
immediate past error to provide more information and enable richer error
handling semantics if such implementation is necessary.

2. We can support a richer set of error types, such as `Error.User`,
`Error.DataLimitExceeded`, `Error.Runtime`, `Error.Timeout`, and we can have
wildcards such as `Error.ALL` that matches any error.
(`Error.DataLimitExceeded`, `Error.Runtime`, `Error.Timeout` have similar
counterparts in Step Functions. See "Error names" in [Error Handling in Step
Functions](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-
error-handling.html))

### Limitations and possible remedies

Step Functions retry are per error type (See "Complex retry scenarios" in
[Error handling in Step Functions](https://docs.aws.amazon.com/step-
functions/latest/dg/concepts-error-handling.html)). Unum can support this
semantics if Lambda simply invokes retry executions with the error message so
that Unum can figure out what was the cause of the failure. e.g., timeouts,
Lambda runtime issues. For now, Unum can wrap user code to distinguish whether
it crashed during user code or Unum runtime code.

Triggering of failure destination seems to be a lot slower than normal
asynchronous invocations.

Unum's argument is to show that we can build complex serverless workflows
without adding new services. This fundamentally requires Lambda to be
reasonably reliable. For example, invoking a function should run it at least
once. A failure destination lambda should actually run when the source
function fails.
