# Unum Runtime

## Input Payload Format

Every unum function is invoked with a JSON input of the following structure.

```json
{
    "Data": {
        "Source": "http | dynamodb",
        "Value": "data value as a JSON object | [data store pointers]"
    },
    "Session": "uuid4 string",
    "Fan-out": {
        "Index": 1,
        "Size": 3,
        "OuterLoop": {
            "Index": 2,
            "Size": 5,
	    "OuterLoop": {
	        "Index": 0,
		"Size": 3
	    }
        }
    }
}
```

The input contains two types of information

1. Input data for the user-defined function
2. Unum runtime metadata

The `Data` field contains the input data to the user-defined function. Data is either passed directly in the payload or passed by reference as pointers to an intermediate data store. The current implementation supports DynamoDB as the intermediate data store. However, users can extend the runtime library to support other data stores that better suits their applications' needs. 

The rest of the fields are Unum's runtime metadata. The main purpose of the runtime metadata is to uniquely identify each function invocation. Unum names each invocation using a combination of the function name, session ID and fan-out indexes.

## Data

**[REQUIRED]**

### Source

Source specifies where the data is coming from. It can be `http`, `s3`, `dynamodb`.

If `Source` is `http`, data in the `Value` field should be a JSON object that the unum runtime passes directly to the user function as input.

If `Source` is not `http`, data in the `Value` field is one or more pointers to an unum data store whose type is specified in `Source`. The content of `Value` depends on the data store type. For example, if `Source: s3`, `Value` would be one or more keys.

`s3`, `dynamodb` are unum intermediary data stores that are normally used in the case of fan-in.

Note that the `Source` field will match the data store type statically specified in `unum-template.yaml`. In the case of s3, the bucket name is configured in the `unum-template.yaml` and the `Value` field is a key under that bucket.

### Value

Contents of the `Value` field depends on the `Source` field.

If `Source: http`, data in the `Value` field is a JSON object that the unum runtime passes directly to the user function as input. The unum runtime does *not* interpret what's in the `Value` field.

If `Source` is not `http`, the `Value` field is one or more pointers to an unum data store. The runtime reads the data via the pointers *in order* and then pass the ordered list to the user function. 



Typically non-http data is received by fan-in functions.

Pointers can be explicit names such as,

1. [`B-unumIndex-0-output.json`, `C-unumIndex-1-output.json`]

2. [`D-unumIndex-1.0-output.json`, `E-unumIndex-1.1-output.json`].

Or they can be glob patterns such as,

1. [`F-unumIndex-*-output.json`].
2. [`F-unumIndex-$2.$1.*-output.json`]
3. [`F-unumIndex-$2.*.0-output.json`]

Glob patterns are commonly used in Map fan-ins. For instance, `F-unumIndex-*-output.json` represents the return values of all of the `F` functions in a map fan-out. The unum runtime on the fan-in function will also look at the `Fan-out` field to determine how many files it needs to read, instead of relying on listing all files in the data store. This is because on eventually consistent data stores, the fan-in function may not see all files immediately. If the fan-in function does not find all of the inputs, it will keep retrying until either it finds all inputs or times out (see [Retries and Timeouts](#Retries_and_Timeouts)).

Note that the the `Value` array is *ordered*. The runtime passes the data to the user function in the order listed in the array. When a glob pattern is used, the runtime sorts the values by their indexes in ascending order.

Data store pointers in the `Value` field are abstract from the unum runtime's perspective. The unum runtime pass the content of this field to the data store library and receive the actual data as return values. This means that the invoker need to encode the session context into the `Value` field.



## Session

**[OPTIONAL]**

The session field is created by the entry function. *All downstream functions' input have this field with the same value*.

The session value is *only used for writing functions' return value to the unum data store*. It is not used when reading from the data store.

The session value is abstract from the unum runtime's perspective. The unum runtime pass the content of this field to the data store library on writes.

A session ID is created for each workflow invocation and shared by all function invocations in the workflow. It directly maps to a unique section of the intermediary data store where all function instances of the workflow invocation write their results. Depending on the type of the data store, the section may be a s3 prefix, a Dynamodb item or a Redis hash.




## Fan-out


A fan-out index is assigned to each fan-out function. When a function is not part of a fan-out, its input JSON does not contain this field. A fan-out index helps distinguish runtime function instances, especially when there are multiple running instances of the same function.

**[OPTIONAL]**

Added by [fan-out initiators](#configurationLanguage) to the input to their fan-out functions.

With nested fan-outs, the existing `Fan-out` field from the input is moved to a nested `OuterLoop` field. The `Fan-out` and `OuterLoop` fields forms a stack structure.

Only function's whose `unum-config.json` has `Fan-out Cancel: True` can pop the top-level `Fan-out` field from *its input* when preparing *input for its invokee*. Otherwise, the function has to propagate the `Fan-out` field to its invokee *as is*.

### Type 

`Map`: For each element of an array, invoke an instance of the same function

`Parallel`: For each function in the `Next` field (`unum-config.json`), invoke an instance with the same input.

### Index

For Map fan-out, each function instance is assigned an index that is the same as its input's index in the array.

For Parallel fan-out, each function is assigned an index that is the same as its index in the `Next` array.

Index starts at 0.

### Size

For Map fan-out, `Size` is the input data array length.

For Parallel fan-out, `Size` is the `Next` array length

### OuterLoop

For nested fan-outs (whether Map or Parallel or a mixture of both), the outer-loop is saved in a `OuterLoop` field inside the `Fan-out` object. 

`OuterLoop` forms a stack structure where the top-level fan-out object is the most immediate one and the bottom is the oldest one. `Fan-out Cancel` in the `unum-config.json` is a stack pop and a fan-out is a stack push.

## Modifiers

TODO

Feature added for testing.

Modifiers are used for testing individual functions or a partial section of a workflow.



## Examples

### Request from client to the entry function to invoke a workflow

To start an unum workflow, clients invoke the entry function.

Inputs to entry functions need to be sent via HTTP. `Value` can be any valid JSON objects and it is passed as is to to the user function. The unum runtime does not inspect or interpret the `Value` field content. For instance,

```
{
    "Data": {
        "Source": "http",
        "Value": "Hello!"
    }
}
```

```
{
    "Data": {
        "Source": "http",
        "Value":  [
			{"2021-02-20T08:30:00.000":120},
			{"2021-02-20T09:30:00.000":25.0},
			{"2021-02-20T10:30:00.000":211.2},
			{"2021-02-20T11:30:00.000":10}
		]
    }
}
```

```
{
    "Data": {
        "Source": "http",
        "Value": {}
    }
}
```

It is possible to pass pointers to data stores. For example,

```
{
    "Data": {
        "Source": "http",
        "Value": {
            "bucket": "image-process-data",
            "key": "example.jpg"
        }
    }
}
```

But the `Source` is still `http` because the data is not going through an unum intermediary data store. It is up to the user function to interpret what's in the `Value` field.



### Chain of  Functions

![runtime-io-example-chain](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-chain.jpg)

An example chain workflow with two functions, A, B and C.

Function A can invoke B with input of the following content

```
{
    "Data": {
        "Source": "http",
        "Value": [
			{"2021-02-20T08:30:00.000":120},
			{"2021-02-20T09:30:00.000":25.0},
			{"2021-02-20T10:30:00.000":211.2},
			{"2021-02-20T11:30:00.000":10}
		]
    }
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
}
```

For a chain of functions, inputs are always passed via HTTP. 

`Value` is any JSON-serializable object that A's user function returns (see [User Function I/O](#User_Function_I/O)).

`Session` field is added by A which is the entry function of the workflow. The meaning of the `Session` value depends on the data store used (whether it is s3, dynamodb, etc.) and is abstract from the unum runtime's perspective. The runtime simply passed the `Session` value to the data store library when writing its return value.

`Session` is propagated to all downstream functions. When B invokes C, B will pass the `Session` field as is to C:

```
{
    "Data": {
        "Source": "http",
        "Value": {"Recommended Action": "Off"}
    }
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
}
```



### Parallel fan-out + fan-in

![runtime-io-example-parallel](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-parallel.jpg)

An example of parallel fan-out and fan-in.

A's `unum-config.json`:

```
{
    "Next": ["B", "C","D"],
    "NextInput": "Scalar",
    "Start": True
}
```

A's input to B,

```
{
    "Data": {
        "Source": "http",
        "Value": {
            "bucket": "image-process-data",
            "key": "example.jpg"
        }
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 3,
    }
}
```

A's input to C,

```
{
    "Data": {
        "Source": "http",
        "Value": {
            "bucket": "image-process-data",
            "key": "example.jpg"
        }
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 1,
        "Size": 3,
    }
}
```

A's input to D,

```
{
    "Data": {
        "Source": "http",
        "Value": {
            "bucket": "image-process-data",
            "key": "example.jpg"
        }
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 2,
        "Size": 3,
    }
}
```

If B ends up being the function that invokes E.

B's `unum-config.json`:

```
{
    "Next": "E",
    "NextInput": {
        "Fan-in": {
            "Values" : [
                "B-unumIndex-0-output.json",
                "C-unumIndex-1-output.json",
                "D-unumIndex-2-output.json",
            ]
        }
    }
}
```

B's input to E,

```
{
    "Data": {
        "Source": "s3",
        "Value": [
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/B-unumIndex-0-output.json",
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/C-unumIndex-1-output.json",
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/D-unumIndex-2-output.json",
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 3,
    }
}
```

Note that E will inherit B's `Fan-out` field.

E's `unum-config.json`

```
{
    "Next": "F"
    "NextInput": "Scalar"
    "Fan-out Modifiers": ["Pop"]
}
```

`Fan-out Cancel : True` will instruct the runtime to pop the top-level `Fan-out` field. Therefore, E's input to F is

```
{
    "Data": {
        "Source": "http",
        "Value": {"Data": "E's result"}
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544"
}
```



### Map fan-out  + fan-in

![runtime-io-example-map](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-map.jpg)

An example of Map fan-out and fan-in

F's `unum-config.json`

```
{
    "Next": "G",
    "NextInput": "Map",
    "Start": True
}
```

F's user function is expected to return an array. For each element of the array, the unum runtime on F will invoke a G instance.

Let's say that F's user function returns an array of length 20, then F's input to the $i^{th}$ G instance look like,

```
{
    "Data": {
        "Source": "http",
        "Value": "ith element of the array"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": i,
        "Size": 20,
    }
}
```

G's `unum-config.json`

```
{
    "Next": "H",
    "NextInput": {
        "Fan-in": {
            "Values" : [
               "G-unumIndex-*-output.json"
            ]
        }
    }
}
```

All of the G's instances have the same `unum-config.json` as they're the same function.

The `*` in the `Values` field is a glob pattern that represents all of the G instances' results.



If the $i^{th}$ G instance ends up invoking H, it will send the following input to H,

```
{
    "Data": {
        "Source": "s3",
        "Value": [
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/G-unumIndex-*-output.json"
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": i,
        "Size": 20,
    }
}
```

We can *statically control* which G would perform the fan-in with the `Conditional` field in `Next`. For instance, if we want the last G instance in the fan-out to invoke H, then G's `unum-config.json` can be written as:

```
{
    "Next": {
        "Function": "H",
        "Conditional": "$0 == $size - 1"
    },
    "NextInput": {
        "Fan-in": {
            "Values" : [
               "G-unumIndex-*-output.json"
            ]
        }
    }
}
```

See more details in [the unum Configuration Language]()

H's `unum-config.json`

```
{
    "Next": "M"
    "NextInput": "Scalar"
    "Fan-out Modifiers": ["Pop"]
}
```

H's input to M,

```
{
    "Data": {
        "Source": "http",
        "Value": {"Data": "H's result"}
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544"
}
```

The `Fan-out` field is removed.



### Parallel fan-out to chains of functions + fan-in

![runtime-io-example-parallel-chain-diff](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-parallel-chain-diff.jpg)

The branches of a parallel fan-out can be chains of functions. In the example above, we build on top of [the previous parallel fan-out example](#Parallel fan-out + fan-in) and add an additional function to each branch to form three chains.

A's `unum-config.json` remains the same as the previous example as unum configuration only specifies orchestration actions about the immediate next step, which is local to the function.

```
{
    "Next": ["B", "C","D"],
    "NextInput": "Scalar",
    "Start": True
}
```

A's inputs to B, C, and D are also structurally identical to the previous example. B will be assigned with index 0, C with 1 and D with 2.

A's input to B,

```
{
    "Data": {
        "Source": "http",
        "Value": {
            "bucket": "image-process-data",
            "key": "example.jpg"
        }
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 3,
    }
}
```

A's input to C,

```
{
    "Data": {
        "Source": "http",
        "Value": {
            "bucket": "image-process-data",
            "key": "example.jpg"
        }
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 1,
        "Size": 3,
    }
}
```

A's input to D,

```
{
    "Data": {
        "Source": "http",
        "Value": {
            "bucket": "image-process-data",
            "key": "example.jpg"
        }
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 2,
        "Size": 3,
    }
}
```

B's `unum-config.json`

```
{
    "Next": "E",
    "NextInput": "Scalar"
}
```

B's input to E will propagate the `Fan-out` field so that E knows that it is in the first branch of a parallel fan-out.

```
{
    "Data": {
        "Source": "http",
        "Value": "B's result"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 3,
    }
}
```

C and D's `unum-config.json` will look nearly identical to B's `unum-config.json` with the only exception being the `Next` field.

Moreover, C and D's input to F and G will also propagate their respective `Fan-out` field.

If G ends up performing the fan-in to H, 

G's `unum-config.json`,

```
{
    "Next" : "H",
    "NextInput" : {
        "Fan-in": {
            "Values" : [
                "E-unumIndex-0-output.json",
                "F-unumIndex-1-output.json",
                "G-unumIndex-2-output.json"
            ]
        }
    }
}
```

Again, because parallel fan-out are statically defined, we can know a priori the index number for E, F, and G.

G's input to H,

```
{
    "Data": {
        "Source": "s3",
        "Value": [
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/E-unumIndex-0-output.json",
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/F-unumIndex-1-output.json",
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/G-unumIndex-2-output.json",
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 2,
        "Size": 3,
    }
}
```

Similarly, H will pop the `Fan-out` field before invoking I.



![runtime-io-example-parallel-chain-diff](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-parallel-chain-same.jpg)

Branches can share the same function as long as the configuration is the same. In the example above, B, C, and D all invoke the same E function as the second stage of their respective chain.

B, C and D will have the same `unum-config.json`:

```
{
    "Next": "E",
    "NextInput": "Scalar"
}
```

Their input to E will obviously differ in the `Value` as well as in the fan-out `Index`.

There are a couple of way of specifying E's `unum-config.json`. Because parallel fan-outs are statically defined, we can know a priori the number of Es and their indexes. We can therefore list the values explicitly in the `unum-config.json`.

```
{
    "Next" : "H",
    "NextInput" : {
        "Fan-in": {
            "Values" : [
                "E-unumIndex-0-output.json",
                "E-unumIndex-1-output.json",
                "E-unumIndex-2-output.json"
            ]
        }
    }
}
```

If the last E ends up invoking H, then H's input will be,

```
{
    "Data": {
        "Source": "s3",
        "Value": [
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/E-unumIndex-0-output.json",
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/E-unumIndex-1-output.json",
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/E-unumIndex-2-output.json",
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 2,
        "Size": 3,
    }
}
```

Alternatively, we can use a glob pattern with `*` and the runtime will look at the `Size` field to figure out the total number of E's results to wait for.

```
{
    "Next" : "H",
    "NextInput" : {
        "Fan-in": {
            "Values" : [
                "E-unumIndex-*-output.json"
            ]
        }
    }
}
```

H's input,

```
{
    "Data": {
        "Source": "s3",
        "Value": [
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/E-unumIndex-*-output.json"
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 2,
        "Size": 3,
    }
}
```

As mentioned, the runtime on H will use the `Size: 3` to figure out the total number of `E-unumIndex-*-output.json` that it needs to read.

![runtime-io-example-parallel-chain-diff-length](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-parallel-chain-diff-length.jpg)

The length of the chains doesn't have to be the same either.

D's `unum-config.json`

```
{
    "Next" : "H",
    "NextInput" : {
        "Fan-in": {
            "Values" : [
                "E-unumIndex-0-output.json",
                "E-unumIndex-1-output.json",
                "D-unumIndex-2-output.json"
            ]
        }
    }
}
```



E's `unum-config.json`

```
{
    "Next" : "H",
    "NextInput" : {
        "Fan-in": {
            "Values" : [
                "E-unumIndex-0-output.json",
                "E-unumIndex-1-output.json",
                "D-unumIndex-2-output.json"
            ]
        }
    }
}
```

D's input to H

```
{
    "Data": {
        "Source": "s3",
        "Value": [
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/E-unumIndex-0-output.json",
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/E-unumIndex-1-output.json",
            "fd9113b2-ac65-4d71-86de-f37a57c3c544/D-unumIndex-2-output.json",
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 2,
        "Size": 3,
    }
}
```



### Map fan-out to chains of functions + fan-in

![runtime-io-example-map-chains](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-map-chains.jpg)

While branches of parallel fan-outs can consist of distinctive functions, iterations of a map fan-out are identically defined. In this example, the G function has the following `unum-config.json`,

```
{
    "Next": "H",
    "NextInput": "Scalar"
}
```

and H has the following `unum-config.json`,

```
{
    "Next": "M",
    "NextInput": {
        "Fan-in": {
            "Values" : [
               "H-unumIndex-*-output.json"
            ]
        }
    }
}
```

G functions will propagate the `Fan-out` field to H instances. For example, the ith G instance will invoke an H function with the following input

```
{
    "Data": {
        "Source": "http",
        "Value": "Gi's result"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": i,
        "Size": 20,
    }
}
```



### Nested Parallel fan-out + fan-in

![runtime-io-example-nestedparallel-unique](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-nestedparallel-unique.jpg)

unum supports nested fan-outs. 

A's `unum-config.json`

```
{
    "Next": ["B", "C"],
    "NextInput": "Scalar",
    "Start": True
}
```

```
{
    "Data": {
        "Source": "http | s3 ",
        "Value": {}
        
    }
    "Session": {"an ID passed to the intermediary data store"},
	"Fan-out": {
        "Type": "Map | Parallel",
        "Index": 1,
        "Size": 3,
        "OuterLoop": {
            "Type": "Map | Parallel",
            "Index": 2,
            "Size": 5
        }
    }
	"Modifiers" : {
        "Invoke": "One-off | One-off-client | Downstream",
    }
}
```



A's input to B

```
{
    "Data": {
        "Source": "http",
        "Value": "A's result"
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 2,
    }
}
```



A's input to C

```
{
    "Data": {
        "Source": "http",
        "Value": "A's result"
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 1,
        "Size": 2,
    }
}
```



B's `unum-config.json`

```
{
    "Next": ["D", "E"],
    "NextInput": "Scalar"
}
```

B's input to D

```
{
    "Data": {
        "Source": "http",
        "Value": "B's result"
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 2,
        "OuterLoop": {
            "Type": "Parallel",
            "Index": 0,
            "Size": 2
        }
    }
}
```



B's input to E

```
{
    "Data": {
        "Source": "http",
        "Value": "B's result"
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 1,
        "Size": 2,
        "OuterLoop": {
            "Type": "Parallel",
            "Index": 0,
            "Size": 2
        }
    }
}
```



C's `unum-config.json`

```
{
    "Next": ["F", "G"],
    "NextInput": "Scalar"
}
```

C's input to F

```
{
    "Data": {
        "Source": "http",
        "Value": "C's result"
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 2,
        "OuterLoop": {
            "Type": "Parallel",
            "Index": 1,
            "Size": 2
        }
    }
}
```



C's input to G

```
{
    "Data": {
        "Source": "http",
        "Value": "C's result"
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 1,
        "Size": 2,
        "OuterLoop": {
            "Type": "Parallel",
            "Index": 1,
            "Size": 2
        }
    }
}
```



E's `unum-config.json`

```
{
    "Next": "H",
    "NextInput": {
        "Fan-in": {
            "Values" : [
               "D-unumIndex-0.0-output.json",
               "E-unumIndex-0.1-output.json"
            ]
        }
    }
}
```

Alternatively,

```
{
    "Next": "H",
    "NextInput": {
        "Fan-in": {
            "Values" : [
               "D-unumIndex-$1.0-output.json",
               "E-unumIndex-$1.1-output.json"
            ]
        }
    }
}
```

E's input to H

```
{
    "Data": {
        "Source": "s3",
        "Value": [
        	"D-unumIndex-0.0-output.json",
        	"E-unumIndex-0.1-output.json"
        ] 
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 1,
        "Size": 2,
        "OuterLoop": {
            "Type": "Parallel",
            "Index": 0,
            "Size": 2
        }
    }
}
```

Alternatively,

```
{
    "Data": {
        "Source": "s3",
        "Value": [
        	"D-unumIndex-$1.0-output.json",
        	"E-unumIndex-$1.1-output.json"
        ] 
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 1,
        "Size": 2,
        "OuterLoop": {
            "Type": "Parallel",
            "Index": 0,
            "Size": 2
        }
    }
}
```

The unum runtime will expand $1 to 0 based on the `OuterLoop[Size]` value.

H's `unum-config.json`

```
{
    "Next": "J"
    "NextInput": {
    	"Fan-in" : {
    		"Value" : [
    			"H-unumIndex-0-output.json",
    			"I-unumIndex-1-output.json"
    		]
    	}
    },
    "Fan-out Modifiers": ["Pop"]
}
```

H's input to J

```
{
    "Data": {
        "Source": "s3",
        "Value": [
        	"H-unumIndex-0-output.json",
        	"I-unumIndex-1-output.json"
        ] 
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 2
    }
}
```

The unum runtime pop off the top-level `Fan-out` field and replace it with the previous `OuterLoop` field.

![nested-parallel-same](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/nested-parallel-same.jpg)

In the previous example, all functions are uniquely named. It is possible for nested branches to use the same function. In the above example, both B and C fan-out to D and E function which in turn fan-in to function F and then G.

D's `unum-config.json`

```
{
    "Next": "F"
    "NextInput": {
    	"Fan-in" : {
    		"Value" : [
    			"D-unumIndex-$1.0-output.json",
    			"E-unumIndex-$1.1-output.json"
    		]
    	}
    }
}
```

F's `unum-config.json`

```
{
    "Next": "G"
    "NextInput": {
    	"Fan-in" : {
    		"Value" : [
    			"F-unumIndex-0-output.json",
    			"F-unumIndex-1-output.json"
    		]
    	}
    },
    "Fan-out Modifiers": ["Pop"]
}
```

B's input to D

```
{
    "Data": {
        "Source": "http",
        "Value": "B's result"
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 2,
        "Outerloop": {
            "Type": "Parallel",
            "Index": 0,
            "Size": 2
        }
    }
}
```



Blue D's input to F

```
{
    "Data": {
        "Source": "s3",
        "Value": [
    			"D-unumIndex-$1.0-output.json",
    			"E-unumIndex-$1.1-output.json"
    		]
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 2,
        "Outerloop": {
            "Type": "Parallel",
            "Index": 0,
            "Size": 2
        }
    }
}
```

The unum runtime on F will expand `$1` to 0.

Orange D's input to F

```
{
    "Data": {
        "Source": "s3",
        "Value": [
    			"D-unumIndex-$1.0-output.json",
    			"E-unumIndex-$1.1-output.json"
    		]
        
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 2,
        "Outerloop": {
            "Type": "Parallel",
            "Index": 1,
            "Size": 2
        }
    }
}
```

The unum runtime on F will expand `$1` to 1.

Note that the following is invalid unum workflow because the blue D and E fan-in to function H which makes them different functions from the orange D and E and should thus be named differently.

![nested-parallel-incorrect](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/nested-parallel-incorrect.jpg)



### Nested Map fan-out + fan-in

![runtime-io-example-nestedmap](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-nestedmap.jpg)

In the example above, F first fan-out to 20 instances of Gs. Each G then fan-out to varying numbers of Hs.

F's user function returns an array. G's user function returns an array.

M's input is an array of H's return values. N's input is an array of M's return values.

F's `unum-config.json`

```
{
    "Next": "G",
    "NextInput": "Map",
    "Start": True
}
```

Input to the 5th G instance

```
{
    "Data": {
        "Source": "http",
        "Value": "5th item of F's result array"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 5,
        "Size": 20
    }
}
```



G's `unum-config.json`

```
{
    "Next": "H",
    "NextInput": "Map"
}
```

5th G's input to the 2nd H instance

```
{
    "Data": {
        "Source": "http",
        "Value": "2nd item of the 5th G's result array"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 2,
        "Size": 3,
        "Outerloop": {
            "Type": "Map",
            "Index": 5,
            "Size": 20
        }
    }
}
```



H's `unum-config.json`

```
{
    "Next": "M",
    "NextInput": {
    	"Fan-in" : {
    		"Value" : ["H-unumIndex-$1.*-output.json"]
    	}
    }
}
```

`$1` refers to *this* instance's first `Outerloop` index. `*` will expand to all indexes at the `$0` place. In the case of 2nd H instance of the 5th G instance, `*` will expand to `[0,1,2]` because the size of the last fan-out is 3.

M's `unum-config.json`

```
{
    "Next": "N",
    "NextInput": {
    	"Fan-in" : {
    		"Value" : ["M-unumIndex-*-output.json"]
    	}
    },
    "Fan-out Modifiers": ["Pop"]
}
```



Input to the 5th M instance

```
{
    "Data": {
        "Source": "s3",
        "Value": [
        	"fd9113b2-ac65-4d71-86de-f37a57c3c544/H-unumIndex-$1.*-output.json"
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 2,
        "Size": 3,
        "Outerloop": {
            "Type": "Map",
            "Index": 5,
            "Size": 20
        }
    }
}
```

The runtime on the 5th M will expand `$1` to 5 and `*` to `[0,1,2]`.

Because M has `"Fan-out Modifiers": ["Pop"]` in its `unum-config.json`, M will pop the `Fan-out` when creating the input to N:

```
{
    "Data": {
        "Source": "s3",
        "Value": [
        	"fd9113b2-ac65-4d71-86de-f37a57c3c544/M-unumIndex-*-output.json"
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 5,
        "Size": 20
    }
}
```



### Nested Parallel + Map fan-out + fan-in

![runtime-io-example-nested-parallel-map](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-nested-parallel-map.jpg)

We will follow the A->B->F.0.0 branch to illustrate how the runtime executes this workflow.

A’s unum-config.json

```
{
    "Next": ["B", "C"],
    "NextInput": "Scalar"
}
```

B's input

```
{
    "Data": {
        "Source": "http",
        "Value": "A's result"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 2
    }
}
```



C's input

```
{
    "Data": {
        "Source": "http",
        "Value": "A's result"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Parallel",
        "Index": 1,
        "Size": 2
    }
}
```



B’s unum-config.json

```
{
    "Next": "F",
    "NextInput": "Map"
}
```

B will nest the previous `Fan-out` field when invoking F. 

0th F's input

```
{
    "Data": {
        "Source": "http",
        "Value": "0th element of B's result array"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 0,
        "Size": 10,
        "Outerloop": {
            "Type": "Parallel",
            "Index": 0,
        	"Size": 2
        }
    }
}
```



F’s unum-config.json

```
{
    "Next": ["D", "E"],
    "NextInput": "Scalar"
}
```

F will further nest the `Fan-out` field when invoking D and E.

D's input (invoked by the 0th F)

```
{
    "Data": {
        "Source": "http",
        "Value": "F's result"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
    "Fan-out": {
    	"Type": "Parallel",
        "Index": 0,
        "Size": 2,
        "Outerloop": {
        	"Type": "Map",
            "Index": 0,
            "Size": 10,
            "Outerloop": {
                "Type": "Parallel",
                "Index": 0,
                "Size": 2
            }
        }
    }
}
```

E's input (invoked by the 0th F)

```
{
    "Data": {
        "Source": "http",
        "Value": "F's result"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
    "Fan-out": {
    	"Type": "Parallel",
        "Index": 1,
        "Size": 2,
        "Outerloop": {
        	"Type": "Map",
            "Index": 0,
            "Size": 10,
            "Outerloop": {
                "Type": "Parallel",
                "Index": 0,
                "Size": 2
            }
        }
    }
}
```



D’s unum-config.json

```
{
    "Next": "M",
    "NextInput": {
    	"Fan-in" : {
    		"Value" : [
    			"D-unumIndex-$2.$1.0-output.json",
    			"E-unumIndex-$2.$1.1-output.json"
    		]
    	}
    }
}
```

E’s unum-config.json

```
{
    "Next": "M",
    "NextInput": {
    	"Fan-in" : {
    		"Value" : [
    			"D-unumIndex-$2.$1.0-output.json",
    			"E-unumIndex-$2.$1.1-output.json"
    		]
    	}
    }
}
```

M's input (assuming a D invoked it)

```
{
    "Data": {
        "Source": "s3",
        "Value": [
        	"D-unumIndex-$2.$1.0-output.json",
    		"E-unumIndex-$2.$1.1-output.json"
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
    "Fan-out": {
    	"Type": "Parallel",
        "Index": 0,
        "Size": 2,
        "Outerloop": {
        	"Type": "Map",
            "Index": 0,
            "Size": 10,
            "Outerloop": {
                "Type": "Parallel",
                "Index": 0,
                "Size": 2
            }
        }
    }
}
```



M’s unum-config.json

```
{
    "Next": "N",
    "NextInput": {
    	"Fan-in" : {
    		"Value" : ["M-unumIndex-$1.*-output.json"]
    	}
    },
    "Fan-out Modifiers": ["Pop"]
}
```



N's input

```
{
    "Data": {
        "Source": "s3",
        "Value": [
        	"M-unumIndex-$1.*-output.json"
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
    "Fan-out": {
        "Type": "Map",
        "Index": 0,
        "Size": 10,
        "Outerloop": {
            "Type": "Parallel",
            "Index": 0,
            "Size": 2
        }
    }
}
```

Note that M pops the top-level `Fan-out` off when constructing N's input.

N’s unum-config.json

```
{
    "Next": "P",
    "NextInput": {
    	"Fan-in" : {
    		"Value" : ["N-unumIndex-*-output.json"]
    	}
    },
    "Fan-out Modifiers": ["Pop"]
}
```

It is possible to know the number of N instances a priori. Therefore, we can also write the configuration as,

```
{
    "Next": "P",
    "NextInput": {
    	"Fan-in" : {
    		"Value" : [
    			"N-unumIndex-0-output.json",
    			"N-unumIndex-1-output.json"
    		]
    	}
    },
    "Fan-out Modifiers": ["Pop"]
}
```

P's input

```
{
    "Data": {
        "Source": "s3",
        "Value": [
        	"N-unumIndex-0-output.json",
    		"N-unumIndex-1-output.json"
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
    "Fan-out": {
        "Type": "Parallel",
        "Index": 0,
        "Size": 2
    }
}
```



P’s unum-config.json

```
{
    "Next": "Q",
    "NextInput": "Scalar",
    "Fan-out Modifiers": ["Pop"]
}
```

Q's input

```
{
    "Data": {
        "Source": "http",
        "Value": "P's result"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544"
}
```



### Partial fan-in (pipeline parallelism)

![runtime-io-example-map-partial-fanin](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-map-partial-fanin.jpg)

F's `unum-config.json`

```
{
    "Next": "G",
    "NextInput": "Map",
    "Start": True
}
```

1st G's (`G.1`) input

```
{
    "Data": {
        "Source": "http",
        "Value": "1st element of F's result array"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 1,
        "Size": 5
    }
}
```



G's `unum-config.json`

```
{
    "Next": {
    	"H": {
    		"Conditional": "$0 < $size-1"
    	}
    },
    "NextInput": {
    	"Fan-in" : {
    		"Value" : [
    			"G-unumIndex-$0-output.json",
    			"G-unumIndex-$0+1-output.json"
    		]
    	}
    },
    "Fan-out Modifiers": ["$size = $size - 1"]
}
```

`G.0`- `G.3` will invoke `H.0`-`H.3`. `G.4` will not invoke an H function.

H.1's input:

```
{
    "Data": {
        "Source": "s3",
        "Value": [
    			"fd9113b2-ac65-4d71-86de-f37a57c3c544/G-unumIndex-$0-output.json",
    			"fd9113b2-ac65-4d71-86de-f37a57c3c544/G-unumIndex-$0+1-output.json"
    		]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 1,
        "Size": 4
    }
}
```

The `Size` value in the `Fan-out` field is decreased by 1 because G's configuration has `$size = $size - 1` as a Fan-out Modifier.

H's `unum-config.json`

```
{
	"Next": "M",
	"NextInput": {
    	"Fan-in" : {
    		"Value" : [
    			"H-unumIndex-*-output.json"
    		]
    	}
    },
    "Fan-out Modifiers": ["Pop"]
}
```

M's input (assuming `H.3` invokes it),

```
{
    "Data": {
        "Source": "s3",
        "Value": [
    			"fd9113b2-ac65-4d71-86de-f37a57c3c544/H-unumIndex-*-output.json"
    		]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 3,
        "Size": 4
    }
}
```



### Fan-out and Fold

![runtime-io-example-map-fold](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-map-fold.jpg)

F's `unum-config.json`

```
{
	"Next": "H",
	"NextInput": "Map",
	"Start": True
}
```



0th H instance's input

```
{
    "Data": {
        "Source": "http",
        "Value": "0th element of F's result array"
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 0,
        "Size": 4
    }
}
```

H's `unum-config.json`

```
{
	"Next": {
		"M": {
			"Conditional": "$0 == 0"
		}
	},
	"NextInput": {
    	"Fan-in" : {
    		"Value" : [
    			"H-unumIndex-$0-output.json",
    			"H-unumIndex-$0+1-output.json"
    		]
    	}
    }
}
```

The `Conditional` precludes any H instances other than `H.0` from invoking the M function.

M.0's input

```
{
    "Data": {
        "Source": "s3",
        "Value": [
        	"fd9113b2-ac65-4d71-86de-f37a57c3c544/H-unumIndex-$0-output.json",
    		"fd9113b2-ac65-4d71-86de-f37a57c3c544/H-unumIndex-$0+1-output.json"
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 0,
        "Size": 4
    }
}
```

The runtime will expand the `Value`to `["fd9113b2-ac65-4d71-86de-f37a57c3c544/H-unumIndex-0-output.json", "fd9113b2-ac65-4d71-86de-f37a57c3c544/H-unumIndex-1-output.json"]`.

M's `unum-config.json`

```
{
	"Next": {
		"M": {
			"Conditional": "$0 < $size-2"
		}
	},
	"NextInput": {
    	"Fan-in" : {
    		"Value" : [
    			"M-unumIndex-($0-1)-output.json",
    			"H-unumIndex-($0+1)-output.json"
    		]
    	}
    },
    "Fan-out Modifiers": ["$0 = $0+1"]
}
```

The `Conditional: "$0 < $size-2"` will stop the recursion at the 2nd to last iteration.

The `"$0 = $0+1"` will increment the `Index` value in the `Fan-out` field. M.0 will invoke M.1 with the following input,

```
{
    "Data": {
        "Source": "s3",
        "Value": [
        	"fd9113b2-ac65-4d71-86de-f37a57c3c544/M-unumIndex-($0-1)-output.json",
    		"fd9113b2-ac65-4d71-86de-f37a57c3c544/H-unumIndex-($0+1)-output.json"
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 1,
        "Size": 4
    }
}
```

The runtime will expand the `Value` to `["fd9113b2-ac65-4d71-86de-f37a57c3c544/M-unumIndex-0-output.json", "fd9113b2-ac65-4d71-86de-f37a57c3c544/H-unumIndex-2-output.json"]`

Input to M.2

```
{
    "Data": {
        "Source": "s3",
        "Value": [
        	"fd9113b2-ac65-4d71-86de-f37a57c3c544/M-unumIndex-($0-1)-output.json",
    		"fd9113b2-ac65-4d71-86de-f37a57c3c544/H-unumIndex-($0+1)-output.json"
        ]
    },
    "Session": "fd9113b2-ac65-4d71-86de-f37a57c3c544",
	"Fan-out": {
        "Type": "Map",
        "Index": 2,
        "Size": 4
    }
}
```

The runtime will expand the `Value` to `["fd9113b2-ac65-4d71-86de-f37a57c3c544/M-unumIndex-1-output.json", "fd9113b2-ac65-4d71-86de-f37a57c3c544/H-unumIndex-3-output.json"]`

M.2 will not invoke another M instance because 2 < 4-2 is false.

## Conditional 

 unum uses the `Conditional` field to control whether a continuation gets invoked or not. Programmers can use the `Conditional` field to encode termination condition or branching.

`Conditional` does not change the input to the continuation.

### Termination

Terminate on `$ret`

Terminate on index `$0`

### Branch

Branches encoded as a list.

# Runtime Variables

`$n`: the Index value of the nth element in the Fan-out stack. For instance, `$0`: top level Fan-out field's Index

`*`: wildcard that matches all index numbers at a particular fan-out level. The expanded range is determined by the `Size` field of the level.

`$size`: the size of the top level Fan-out stack element

`$ret`: return value of the user function

## Examples

Runtime variables can be used in return value names:

`F-unumIndex-$1.4-output.json`

`F-unumIndex-*-output.json`

They can also be used in Conditional boolean expressions in the `unum-config.json`.

`$0 == $size-1`

`$ret == "MagicStringValue"`



------------

# unum Function Invocation

In general, FaaS systems provide APIs to invoke functions synchronously or asynchronously. The APIs are implemented by the FaaS system and may rely on platform-specific mechanisms. Nevertheless, the semantics of the invoke API is the same across all FaaS systems: create a clean sandbox, load it with the specified function's code and dependencies and execute the function with specified input data. 

Depending on the platform, the sandboxing mechanism could vary, the process of load functions may differ, and the implementation of input passing is likely provider-dependent. But regardless of the specific implementation, it is always the case that the invoker and invokee run in separate sandboxes and share nothing. It is also the case that the invoker can choose to wait for invokees to complete (synchronous invocation) or not (asynchronous invocation). If the invoker waits for the invokees to complete, the invoker will get the invokees' return values, whereas if the invoker doesn't wait, it cannot acquire the invokees' return values.

*This is an important difference from the RPC and traditional asynchronous IO semantics where the client (or caller) can call an RPC asynchronously and later query the results of the async call*. FaaS systems, on the other hand, do not have long-running, server-like processes. Each function runs to completion in response to an event and then exits. State persistence is not provided by the FaaS system.

***unum uses the asynchronous invoke API of the underlying FaaS system***. For example, AWS Lambda supports asynchronous invocation via an event queue mechanism. AWS provides an API in the `aws-sdk` that individual Lambdas can use to asynchronously invoke other Lambdas. unum uses this API from the `aws-sdk`.

unum does not use storage triggers at all and therefore don't need to support storage-specific event formats.

unum uses its own input data format in JSON.

# unum Workflow Invocation

To invoke an unum workflow, invoke the entry function of the workflow. Each workflow can only have one entry function. The entry function is specified in the `unum-template.yaml` file when defining a workflow and its `unum_config.json` also has a special field (`"Start"`).

The entry function will create a session context in the intermediary data store for each workflow *invocation*. Any subsequent functions of the workflow in that invocation that need to store their return values will write to this context. The purpose of the session context is to distinguish outputs by the same function from different invocations.

The implementation of context depends on the data store. For example, if the intermediary data store is s3, this means the entry function will create an unique s3 prefix every time it is invoked. Subsequent functions write their return values to this prefix. For more details, see the [Intermediary Data Store section](#IntermediaryDataStore).

*Session context is created lazily*. For workflows whose functions never need to store their return values, a session context is never actually created. For example, if the intermediary data store is s3, this means that the unique prefix is never created in the bucket.

## Entry Function from Step Functions

TODO

# User Function I/O

***Two types of inputs***:

1. A Python dict
2. A list of Python dicts

Output: Any Python object that's JSON-serializable (by the default Python `json` library). This is the [same requirement for AWS Lambda function](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html).





-------------

An unum workflow has a single entry function. This is identical to Step Functions and Durable Functions.

Workflow entry function is marked

1. in the `unum-template.yaml`  with `Start: true`. 
2. in the function's `unum-config.json` file with `Start: True`.

If programmers write unum IR directly, they need to make sure that the `unum-template.yaml` has `Start: true` under one of the functions. They can optionally add `Start: True` into the *same* function's `unum-config.json`, but it's not required. *`unum-cli build` will use the `unum-template.yaml` file to add a `Start: True` to the entry function's `unum-config.json` if that's not already present.* **`unum-cli build` also validates that only one of the functions of the workflow has `Start: True` in its `unum-config.json`.** If the programmer added `Start: True` to multiple functions, either directly or through `unum-template.yaml`, `unum-cli build` will fail.

Note that once a workflow is deployed, the unum runtime doesn't validate that the entry function has `Start: True` in its `unum-config.json`. From the runtime's perspective, `Start: True` in a function's `unum-config.json` is how it learns that the function is the entry function.

As we discussed in unum Workflow Invocation, clients trigger an unum workflow by calling the workflow's entry function. If a workflow is deployed with `Start: True` in none of its functions, invoking it will fail immediately without executing any user code.




The entry function allocates a *session context* for each workflow invocation. The session context is passed downstream to all functions in the workflow as part of the input payload (See the payload structure above). When a function needs to write its return value to the unum intermediary data store, it writes under the session context.

The session context is implemented differently based on the intermediary data store type. For example, on S3, a session context is an S3 prefix. All functions of the workflow create objects under the prefix. See the [unum Data Store documentation]() for details.



From unum runtime's perspective, a session context is abstract and just a token that it passes to the data store library. The runtime doesn't care if the session context is an s3 context or a dynamodb item ID.



------------



`Checkpoint` is a workflow-level configuration. Programmers turn checkpoint on and off in the workflow's `unum-template.yaml` file by specifying `Checkpoint: true` under `Globals`. If `Checkpoint: true`, each function has `Checkpoint: True` in its `unum-config.json` file. If `Checkpoint: false`, each function has `Checkpoint: False` in its `unum-config.json` file.

When `Checkpoint: true`, each function writes its output to the intermediary data store as **the first step** during egress, *before invoking the next function*.



-----------------------------

## Function return value naming convention

`FunctionName{-unumIndex-n{.m{.p{...}}}}-output.json`

unum assigns a unique ID to each function *instance*'s return value in a workflow invocation. A return value is identified by its function name, and if the instance is a fan-out function, its fan-out index. 

### Glob patterns

Currently only supports `*` in the `Index` section.



# Error Handling, Retries and Timeouts

Any uncaught exceptions, either raised by the user function code or unum runtime, will cause Lambda to retry the function. The exception will be recorded in Cloudwatch logs.

unum doesn't change the Lambda's default retry behavior (even though [Lambda just added the ability to do so](https://aws.amazon.com/about-aws/whats-new/2019/11/aws-lambda-supports-max-retry-attempts-event-age-asynchronous-invocations/?nc1=h_ls)). If the user function raises an exception, Lambda will retry it.



*Should unum runtime raise uncaught exceptions?* Raising uncaught exceptions only causes Lambda to retry the function. This is not what unum wants because retrying have no hope of succeeding and will just encounter the exact same problem again.
Therefore, unum should instead do its own error reporting and handling.

What we need for the error handling mechanism?

1. Need to be able to look up the error after the function exits

Solution: use the unum data store for storing ***unum runtime errors***. For example, on s3, for each session, create a sub-prefix "errors/". All runtime errors are written there.

***The only exception (no pun intended) to this rule is if the the unum data store doesn't exist, in which case the runtime raises an exception.*** On Lambda, this exception will be recorded in Cloudwatch log and cause function to be retried (twice by Lambda's default configuration).



Fan-in function retry when not finding all inputs. unum does *not* impose a time out. However, the function might exceed the platform's runtime limit. When it does, retry and error handling behavior is determined by the platform.



If a function fails to write to the data store due to the data store not existing, the function will raise an exception. 
