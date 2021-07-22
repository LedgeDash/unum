# Data store (wip)

The intermediary data store is configured at the workflow granularity. All functions in a workflow share the same intermediary data store.

Programmers specify an intermediary data store in the workflow's `unum-template.yaml`under `Globals`. Two values need to be given:

1. `UnumIntermediaryDataStoreType`: `s3 | dynamodb | redis | ...`
2. `UnumIntermediaryDataStoreName`: `s3 bucket name | dynamodb table name | redis server name | ...`



The data store needs to be pre-allocated before invoking the workflow. For example, if the data store is s3, the bucket with the name in `UnumIntermediaryDataStoreName` needs to exist before the workflow is invoked. If the data store doesn't exist, writing to it will fail and the unum runtime will raise an exception. Depending on the underlying FaaS system and configuration, the function might be retried.



A unum function instance initializes its data store connection during cold start. Subsequent warm requests do not incur reinitialization costs.







APIs

`create_session_context()`





`write_return_value(session, ret)`





`read_input(ptr)`

Data store pointers in the `Value` field are abstract from the unum runtime's perspective. The unum runtime pass the content of this field to the data store library and receive the actual data as return values.

used by `ingress()` to acquire the input data to the user function.



# Consistency

Scenarios:

1. fan-in function is invoked with a list of pointers to an s3 bucket. This means that the invoker (which is a fan-out function) has seen all of the necessary files exist in s3. Can the fan-in function see the same set of files immediately?
2. Do we have a single fan-out function invoke the fan-in function? Or do we

## Eventual Consistency

## Strong Consistency

How strong consistency simplifies building unum



