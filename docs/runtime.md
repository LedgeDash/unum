# unum Function Invocation

In general, FaaS systems provide APIs to invoke functions synchronously or asynchronously. The APIs are implemented by the FaaS system and may rely on platform-specific mechanisms. Nevertheless, the semantics of the invoke API is the same across all FaaS systems: create a clean sandbox, load it with the specified function's code and dependencies and execute the function with specified input data. 

Depending on the platform, the sandboxing mechanism could vary, the process of load functions may differ, and the implementation of input passing is likely provider-dependent. But regardless of the specific implementation, it is always the case that the invoker and invokee run in separate sandboxes and share nothing. It is also the case that the invoker can choose to wait for invokees to complete (synchronous invocation) or not (asynchronous invocation). If the invoker waits for the invokees to complete, the invoker will get the invokees' return values, whereas if the invoker doesn't wait, it cannot acquire the invokees' return values.

*This is an important difference from the RPC and traditional asynchronous IO semantics where the client (or caller) can call an RPC asynchronously and later query the results of the async call*. FaaS systems, on the other hand, do not have long-running, server-like processes. Each function runs to completion in response to an event and then exits. State persistence is not provided by the FaaS system.

***unum uses the asynchronous invoke API of the underlying FaaS system***. For example, AWS Lambda supports asynchronous invocation via an event queue mechanism. AWS provides an API in the `aws-sdk` that individual Lambdas can use to asynchronously invoke other Lambdas. unum uses this API from the `aws-sdk`.

unum does not use storage triggers at all and therefore don't need to support storage-specific event formats.

unum uses its own input data format in JSON.

# unum Workflow Invocation

To invoke an unum workflow, invoke the entry function of the workflow. Each workflow can only have one entry function. The entry function is specified in the `unum-template.yaml` file when defining a workflow and its `unum_config.json` also has a special field (`"Start"`).

The entry function will create a session context in the intermediary data store for each workflow *invocation*.

## Entry Function from Step Functions

TODO

# User Function I/O

***Two types of inputs***:

1. A Python dict
2. A list of Python dicts

Output: Any Python object that's JSON-serializable (by the default Python `json` library). This is the [same requirement for AWS Lambda function](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html).

# unum I/O

Empty unum input:

```json
{
	"Data": {
		"Source": "http",
		"Value": ""
	}
}

```

unum input with S3 as intermediary data store:

```json
"Data": {
	"Source":"s3",
	"Value": {
		"Bucket": "<bucket-name>",
		"Prefix": "<prefix>"
	}
}
```

The `Data` field is only for unum's intermediary data. It is not for application data.

The `Source` field is only for unum and it specifies the where the intermediary data is coming from.

The unum runtime does not interpret the raw data. For example, if `Source` is `http`, the unum runtime simply passes what's in the `Value` field to the user function. If the `Source` is `s3`, the unum runtime reads the s3 file and passes the file content as a Python dict to the user function.

From an user function's perspective, it just gets the input data as raw. The unum runtime reads the data from the intermediary data store, makes it into the unum format (See [User Function I/O](#UserFunctionI/O)) and pass it to the user function.

## Intermediary Data Store

Any addressable storage. Queues won't work because they cannot address specific messages. Pub/sub messaging services such as SNS are examples. A subscriber cannot read a specific message from the data store (or a queue service in this case).

s3 | dynamodb | redis | 

***User needs to specific which data store to use at compile time in the `unum-template.yaml`. The intermediary data store is a per-workflow configuration.***

## Input Scenarios

### User invocation of the entry function

It's up to the user how to pass data to the entry function. It can be any of the supported



## Difference from storage triggers

Storage triggers such as S3 events are orthogonal to unum. ***unum doesn't use storage triggers to invoke functions***.

Storage triggers have very specific event format. unum does not need to deal with that. ***<u>The `Source` field in the unum input above is not related to storage triggers at all</u>***. The `Source` field specifies the location of the data.

### Difference from workflow composition with storage triggers

No more tying the invokee's input to a specific storage event format. 

