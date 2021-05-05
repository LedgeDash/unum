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