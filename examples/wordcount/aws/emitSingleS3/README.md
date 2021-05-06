This directory contains one implementation of MapReduce wordcount over AWS
Lambda and S3. This implementation explicitly use s3 as the intermediary
datastore.

A primary goal is to separate component function logic from orchestration
logic. We can use either Step Functions or hand-tuned triggers to compose the
workflow *without modifying the component functions*.

# Component Functions

There are 4 component functions in this FaaS workflow:
1. mapper
2. partition
3. reducer
4. summary

The mapper, partition and reducer functions explicitly use s3 as the
intermediary datastore.

The following subsections explain each component function in detail.

## Mapper

The `mapper` function takes as inputs:
1. a string of the raw texts
2. a s3 bucket name

Programmers provide `user_map.py`. `mapper.py` calls the user-defined map
function in `user_map.py` on the raw text. In this wordcount applicatoin, the
user-defined map function calls the `emit(word)` function for each word in the
text. `emit` is a local function provided by the mapreduce runtime
(`mapreduce.py`).


A call to `emit` creates an S3 object named `reducer{id}/{word}/{uuid}` for
each word occurrence. `{id}` in `reducer{id}` is computed from

```python
reducerId = int(hashlib.sha256(word.encode('utf-8')).hexdigest(), 16) % numReducer
```

Given the same input, `hashlib.sha256` produces the same result across
different Python invocations (in our case, different Lambda instances).
**Python's built-in `hash()` function does not guarantee this.**

*Therefore, it is mappers who actually execute partitioning logic when they
call the `emit` function in the mapreduce runtime.*

Each mapper outputs the following JSON string:

```json
{
        "bucket": "{destinationBucket-name/arn}",
        "numReducer": "{number of Reducer}"
    }
```

This is a coarse-grain equivalence to each mapper sending its share of results
to the partition function.

## Partition

The `partition` function is not written by MapReduce programmers. It is part of
the MapReduce runtime. Our partition function mimicks the original behavior in
MapReduce.

The `partition` function receives an array as input. Each element of the array
is an output from a mapper instance. The output is not the actual data in JSON,
such as

```
(wordA,1)
(wordB,1)
(wordC,1)
(wordA,1)
(wordC,1)
(wordA,1)
....
```

Rather, it's a pointer to an S3 directory. In the S3 directory, there is one
directory for each reducer. Under each reducer's directory, there is one
directory per word. Under each word's directory, there is one unique file per
occurrence.

As described above, mappers already partition their output data by creating S3
objects with correctly partitioned prefixes. Therefore, the `partition`
function's partitioning step is a noop. Instead of actually performing
partition, it reads from the S3 bucket and returns a list of directories, one
for each reducer.

## Reduce

Input to a reducer is a s3 directory, e.g., `myBucket/reducer0`. Inside the
directory, there is one directory per word. Under each word's directory, there
is one unique file per occurrence.

The mapreduce runtime reads from the s3 directory (e.g., `reducer0`), and for
each word, it creates a list of 1's, one for each unique file under the word's
directory.

The user-defined reduce function takes as input a word and a list of 1's, each
representing one occurrence and returns the sum of occurrences as output.

The reducer outputs a map whose keys are words and values are the sum of
occurrences.

## Summary

Input to the `summary` function is a list of dict. Each dict is the output of one
reducer.

The `summary` function simply takes the union of all dicts and return that as
a dict.

# Lambda S3 permissions

The mapper, reducer and partition functions need to have permission to access
objects in S3. The permission is given via the `AmazonS3FullAccess` policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": "*"
        }
    ]
}
```

I attach this policy to an execution role
(`arn:aws:iam::908344970015:role/lambda-ex`) and create mapper Lambdas with
this role.


# Orchestrations

## Step Functions

The step function definition is in `step_function/definition.json`.

## Trigger-based

### HTTP Sync + Datastore

A `unum_map` Lambda that serves as the frontend of the workflow. Input data,
such as `6Jokes-chunks-small.json` is sent first to a `unum_map` instance.

`unum_map` expects the input data to be an array. For each element of the
array, `unum_map` invokes an instance of the fan-out Lambda.

Note that `unum_map` does not compute on the application input data. It simply
passes it to the fan-out invokee Lambdas.

From the array size, `unum_map` knows how many fan-out Lambdas to invoke.

`unum_map` passes the total number of invokees and an index to each invokee.

Additionally, `unum_map` creates a directory with unique name in a separate S3
bucket. This directory is to hold the *return values* of each mapper.
`unum_map` Lambda passes this s3 directory to each invokee as well.

*Note that s3 is just one option for temporarily storing functions' return
values. We could also use other data stores such as DynamoDB or Redis which
will likely offer better performances.*

Furthermore, it is worth noting that function *return values* are treated
differently from functions' *explicit side-effects*. In this word count case,
mappers emitted outputs (those `(word, 1)` data) are explicit side-effects of
the mapper functions. Thus, the intermediary S3 bucket that mappers write
those intermediary data to is managed by the application (more specifically,
the client, because the bucket name is passed in as an input parameter). *The
orchestration only manages functions' return values.*

We add a wrapper of ingress and egress functions to each component function.
The egress wrapper takes the component function's return value, JSON
serializes it and writes it to the s3 directory created by `unum_map`.


The `mapper` instance whose index is the same as the fan-out size will check
if all `mapper` instances have completed and written to the s3 directory. It
periodically polls the directory list. When all mapper instances complete,
this last mapper invokes a `partition` function and passes it the s3
directory. Additionally, this last mapper will tell the `partition` function
that it's getting invoked after a fan-out stage and that it (the `partition`
function) is the fan-in ponit.

The next Lambda to invoke is stored in a config file names `.next` and
packaged with the mapper function.

The ingress of the `partition` function will read from the s3 directory and
format the data into an ordered JSON array. Then it will invoke the
user-defined `partition` function.

The `.next` config for `partition` will specify that it should fan-out to
reducers. Therefore, the `partition` function should return a list.

The egress of `partition` will
1. create a unique s3 directory for reducers to write their outputs
2. invoke one reducer for each element in the array
3. pass the total number of reducers and an index to each reducer upon
   invocation.


The `.next` config for reducers will know that it's fanning in to the
`summary` function.


`http_sync_s3` is an example. Each directory is not function.


## HTTP only??

## S3 Triggers only??

*below are just thoughts*

All Lambdas are triggered through S3 triggers. Lambdas cannot invoke other
Lambdas via HTTP.

There's no front-end `unum_map` Lambda. Instead, the client uploads N files
onto a s3 directory. The bucket is configured to invoke a mapper upon object
creation. Additionally, the client uploads a `.unum_map` file that specifies
the totaly number of chunks (the fan-out size) and the s3 bucket that mapper
functions should write their *return values* to (let's call this bucket
`mapper-output`). mappers read `.unum_map` and writes the fan-out size in a
`.sync` file into `mapper-output`.

The `mapper-output` bucket is configured to invoke a `partition` Lambda upon
object creation. The egress of the `partition` Lambda reads the `.unum_map` to
know the fan-out size and checks if all mappers have completed. If yes, it
will read from the s3 directory and format the data into an ordered JSON
array. Then it will invoke the user-defined `partition` function.

If no, it will terminate immediately.

There is a chance that multiple `partition` functions will check and see that
all mappers have completed and cause duplicated invocations. This is not
really a problem for word count because the `partition` and `reducer`
functions are idempotent.

TODO: figure out ways to avoid this problem. Maybe write `.lock` files into
the same bucket as a synchronization point

The `partition` function then creates R objects into another s3 bucket (let's
call this bucket `reducer-input`). Each creation will invoke a reducer
instance. Similary, `partition` writes a `.unum_map` file into `reducer-input`
to specify the fan-out size.


## DynamoDB Triggers only??