# unum Intermediary Representation

Reverse dependency DAG, expressed distributedly with the unum configuration language.

TODO:

1. design principles of the unum IR.
   1. What information does it try to capture
   2. What component does it try to keep abstract (e.g., user function code. The )
2. What is the implementation? = `unum-config.json`


# unum Configuration Language

Each unum function has an unum configuration file that instructs the runtime
what orchestration actions to take, that is whether it should invoke a
function, which function(s) to invoke, and what input data to send.

An unum configuration is a JSON file with the following fields:

```
{
    "Next": "next function's name" | [<function names>],
    "NextInput": "Scalar" | "Map" | "Fan-in",
    "WaitFor": "Map" | [<function names>]
}
```



```
{
    "Next": "next function's name" | [<function names>],
    "NextInput": "Scalar" | "Map" | "Fan-in"
    "Checkpoint": True | False,
    "Start": True | False,
    "Fan-out Cancel" : True | False
}
```



```
"Fan-in": {
        "Values": [
        	"Filename ending with .json" |
        	"Function name if it's unique in the workflow" |
        	"Filename-Index-*-output.json" |
        	"Filename-Index-1.*-output.json"
        ],
    }
```

`Next` specifies the function or functions that should invoke next with my
user function's return value. The value is either a string of a function name,
or a list of function names. An application's functions' names are defined in
the application's unum template (`unum-template.yaml`).

`NextInput` controls how the unum runtime forwards the user function's return
value to the next function(s).

* `Scalar` instructs the runtime to send the entire return value as a whole
  and that's the only value it needs to send to the next function.
* `Map` means that the user function should return a list and for each element
  of the list, the runtime should invoke a next function with the element as
  input.
* `Fan-in` is used in combination with the `WaitFor` field when the next
  function expects not only my return value but the return value of another
  unum function (thus a fan-in). When the `NextInput` field is `Fan-in`, the
  function will first wait for the functions in the `WaitFor` field to
  complete before invoking the next function, and it will send both its return
  value and the return values of the functions in the `WaitFor` field.

The `WaitFor` field is used for fan-in and it specifies which other unum
function(s) I should wait for before invoking the next function.

* `Map`
* `[function names]`

`WaitFor` also supports simple programming constructs that enable pipeline
parallism. Applications can express data dependencies across pararllel
pipelines by specifying the index. For example, `$MyIndex`.


|  | Scalar | Map |
|-|-|-|
| F1 | invoke F1 with user function's return value | User function return a list. Invoke an instance of F1 for each element of the list |
| [F1, F2] | invoke both F1 and F2 with user function's return value | User function return a list. Invoke an instance of F1 and an instance of F2 for each element of the list |







----------

Cancel `Fan-out`:

The issue arises in nested fan-outs. The question is should unum cross off the outmost fan-out field in the payload ***before sending it to the next invokee***.

We have two choices in how to express when to cancel the fan-out payload field:

1. derive statically at compile-time and have a `Fan-out Cancel` field in the function's `unum-config.json`. When `Fan-out Cancel` is in the `unum-config.json`, the function removes the `Fan-out` field from the payload when invoking the next function. If an `Outerloop` field exists, the `Fan-out` field is replaced with the `Outerloop` field's contents.
2. When a function's `NextInput` is `Fan-in`, see if it is `Fan-in: {All Map}` or `Fan-in: [all fan-out functions in a parallel]`. Only when a fan-in covers all fan-out functions, would unum cancel the `Fan-out` field in the input paylod.

Both cases rely on functions' `unum-config`, meaning static, compile-time behavior. Given that both choices are compile time behaviors, I think the first design is better, because it avoids overloading the `NextInput` field. Fan-out  cancellation behavior doesn't have to be "derived" from the `NextInput` field (possibly in combination with other fields); Instead, there's a field specifically for fan-out cancellation. 

In fact, this all points to the complexity of fan-in. This should all be captured in the `NextInput: Fan-in` field.

To summarize a bit at this point. The `NextInput: Fan-in` field in the `unum-config.json` should look something like:

```json
"NextInput": {
    "Fan-in": {
        "WaitFor": ["Filename ending with .json" | "Function name if it's unique in the workflow" | "Filename-Index-*-output.json" | "Filename-Index-1.*-output.json"],
        "Fan-out Cancel": True |False,
    }
}
```

The previous `Map` value for `Fan-in` is not necessary and can be replaced with `myFunctionName-Index-*-output.json`. The `*` wildcard combined with the same `myFunctionName`, ***combined with the payload `Fan-out` field with `Size`*** is enough to support fan-in on a map.



--------------

## Branching and Conditional

Programmable constructs:

1. Fan-out indexes
   1. $0, $1, $2
2. Fan-out size: $size
3. User function's results, $ret

-----------------------









## Use Cases

### Chaining

A common use case for FaaS are pipeline applications where functions form a
chain with each stage invoked with the previous stage's output.

To chain two functions together with unum, set the unum configuration of the first function as follows:

* `NextInput` = `Scalar`
* `Next` = second function's name

This instructs the unum runtime in the first function to invoke the second
function with the first function's output when it completes.

Examples from unum appstore:

* [hello-world](https://github.com/LedgeDash/unum-appstore/tree/main/hello-world),
* [iot-pipeline](https://github.com/LedgeDash/unum-appstore/tree/main/iot-pipeline),
* [parallel-pipeline](https://github.com/LedgeDash/unum-appstore/tree/main/parallel-pipeline)


### Fan-out (static and dynamic)

There are two types of fan-out patterns: (1). fan out to a fixed number of
branches (static) (2). fan out to a variable number of branches (dynamic).
unum supports both.

The function performing a fan-out is called the initiator. Functions in the
fan are called the fan-out functions.

![fan-out-generic](https://github.com/LedgeDash/unum-compiler/blob/main/docs/assets/fan-out-temp.jpg)

**Static**

To fan out a function's output to a fixed number of functions, list the
fan-out functions by name in the initiator function's `Next` field and set the
initiator's `NextInput` to `Scalar`.

For example, an image process workflow for a social network application might
consists of the following functions where it first performs some preprocess on
a user-uplaoded image, then *in parallel*, generates a thumbnail and detects
if there are faces in the picture. In this case, the preprocess function has
the following unum configuration:

```json
{
	"NextInput":"Scalar",
	"Next": ["Thumbnail", "FaceDetection"]
}
```

This configuration statically defines the two fan-out branches after the
preprocess function to be `Thumbnail` and `FaceDetection`. The unum runtime on
the preprocess function will invoke a `Thumbnail` and a `FaceDetection`
funtion after the preprocess function finishes.

Note that you could include the same function multiple times in the `Next`
list and the function will be invoked the same number of time as its name
appears in the list.

Examples from unum appstore:

* [image-process](https://github.com/LedgeDash/unum-appstore/tree/main/image-process),
* [text-process](https://github.com/LedgeDash/unum-appstore/tree/main/iot-pipeline)

**Dynamic**

unum's dynamic fan-out is similar to [the Map state in AWS Step
Functions](https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-map-state.html)
where the state expects an array as input and for each item in the array, it
executes one instance of its `Iterator` state.

An unum function whose `NextInput` field is `Map` also expects its user
function to return an array, and for each item in the array, it invokes one
instance of the `Next` function.

The size of the `Map` fan-out depends on the array size which is a runtime
behavior.

An unum function whose `NextInput` field is `Map` can have a list functions in
its `Next` field. For each array item, the initiator invokes one instance of
each fan-out function in the `Next` list.

Examples from unum appstore:

* [parallel-pipeline](https://github.com/LedgeDash/unum-appstore/tree/main/parallel-pipeline),
* [map](https://github.com/LedgeDash/unum-appstore/tree/main/map),
* [wordcount](https://github.com/LedgeDash/unum-appstore/tree/main/wordcount),
* [excamera](https://github.com/LedgeDash/unum-appstore/tree/main/excamera)

### Fan-in


Examples from unum appstore:
* [image-process](https://github.com/LedgeDash/unum-appstore/tree/main/image-process),
* [text-process](https://github.com/LedgeDash/unum-appstore/tree/main/iot-pipeline),
* [parallel-pipeline](https://github.com/LedgeDash/unum-appstore/tree/main/parallel-pipeline),
* [map](https://github.com/LedgeDash/unum-appstore/tree/main/map),
* [wordcount](https://github.com/LedgeDash/unum-appstore/tree/main/wordcount),
* [excamera](https://github.com/LedgeDash/unum-appstore/tree/main/excamera)


### Pipeline parallelism (Fan-out + Chain)

Each branch of a fan-out (static or dynamic) can be a chain of functions.
Chains are expressed the same way as in the [Chaining section](###chaining),
that is as if the chain is not a branch of fan-out. This means programmers can
compose fan-out and chains together to form parallel pipelines.

#### Data Dependencies across Pipelines

unum allows applications to express data dependencies across parallel
pipelines.

![data-dep-parallel](https://github.com/LedgeDash/unum-compiler/blob/main/docs/assets/data-dep-parallel.jpg)

For static fan-out, functions in each branch can list a subset of all branches
in its `WaitFor` field. In the example above, function A would set

```json
{
	"Next": "E",
	"NextInput": "Fan-in",
	"WaitFor": ["B"]
}
```

And C would set

```json
{
	"Next": "F",
	"NextInput": "Fan-in",
	"WaitFor": ["D"]
}
```

![data-dep-map](https://github.com/LedgeDash/unum-compiler/blob/main/docs/assets/data-dep-map.jpg)

For dynamic fan-out, because the branches are usually different instances of
the same function, data dependencies are specified with *branch indexes*. For
example, each branch could wait for the next branch in the fan-out.

unum provides some programmable constructs for the `WaitFor` field to express
data dependencies in dynamic fan-outs. To wait for the next branch in the
fan-out, set the `WaitFor` field to `$MyIndex + 1`.

<!-- In the above example, the F function would have 

```json
{
	"Next": "I",
	"NextInput": "Fan-in",
	"WaitFor": ["$MyInput + 1"]
}
​``` -->

Examples from unum appstore:
* [parallel-pipeline](https://github.com/LedgeDash/unum-appstore/tree/main/parallel-pipeline),
* [excamera](https://github.com/LedgeDash/unum-appstore/tree/main/excamera)
* TODO: static fan-out with chains
* TODO: the parallel example in the graph
* TODO: the map example in the graph

### Nest Fan-out and Fan-in

TODO

<!-- ## Mapping to Step Functions States

This is a rough
|  | Scalar | Map |
|-|-|-|
| F1 | Chain | Map |
| [F1, F2] | Parallel | Parallel with 2 branches. Each branch being a Map. | -->


### Cases Beyond Step Functions

Fan-in to multiple next functions. Step function always fan in to a single node.

Map user function's output + waitfor/fan-in with another function

Invalid combination: NextInput: scalar, Waitfor:map.

1. A single function can map to multiple functions with `NextInput: Map` and `Next: ["F1","F2"]`.

```

![runtime-io-example-map-fanin-across-maps](D:\Dropbox (Princeton)\Dev\unum-compiler\docs\assets\runtime-io-example-map-fanin-across-maps.jpg)

S' `unum-config.json`.



