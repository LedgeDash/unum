
Step Functions quotas:

Maximum input or output size for a task, state, or execution: 262,144 bytes (256KB) of data as a UTF-8 encoded string

Lambda quotas:

Invocation payload (request and response): 6 MB (synchronous); 256 KB (asynchronous)

Step-Functions cannot handle large fan-ins. Users have to manually allocate a
data store and make their Lambdas return a pointer. unum functions can simply
return its results which is more natural, and unum automatically saves it in a
data store and passes a pointer instead of the actual data.