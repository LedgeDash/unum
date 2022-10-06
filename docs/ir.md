# Unum Intermediate Representation

## Overview

The Unum intermediate representation (IR) expresses serverless applications that consist of many FaaS functions. Applications are modeled as directed graphs where nodes are FaaS functions and edges are transitions between functions. The Unum IR expresses such a directed graph by encoding each node with its outgoing edges in a separate file. For example, an application that comprises of 5 functions would have 5 files in its Unum IR, one for each function that encodes the function's node in the direct graph as well as the node's outgoing edges.

Application developers can write the Unum IR directly for each function to build application. Alternatively, they can provide a Step Functions definition to the Unum frontend compiler, and the compiler can translate the state machine into a set of Unum IR files, one for each function in the application.

During execution, the [Unum runtime library](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md) reads the Unum IR and performs orchestration operations based on the IR. Orchestration operations include invoking the next unum function with the current function's result, checkpointing the current function's output, signaling a branches completion by updating the Completion Set data structure, etc. For more details, see [the unum Runtime documentation](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md).

### Transitions

Transitions between nodes in the Unum IR can be one-to-one, one-to-many or many-to-one. A one-to-one transition chains two functions together where the head node function is invoked when the tail node function's result becomes available. The input to the head node function is the output of the tail node function.

A one-to-many transition represents a fan-out where the output of the tail node function is "broadcasted" to many "branches". The head node function of each branch is invoked when the tail node function's result becomes available.

There are two flavors of one-to-many transitions in Unum. The first flavor is similar to AWS Step Functions' [Parallel state](https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-parallel-state.html) where the input to every branch's head node function is the output of the tail node function. In other words, every branch is invoked with the same input. This flavor of one-to-many transition is useful when you need to process the same data in different ways, where each branch has a different head node function and all branches can run in parallel. The other flavor of one-to-many transition is similar to AWS Step Functions' [Map state](https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-map-state.html) where the tail node function outputs an iterable (e.g., an array) and the input to each branch's head node function is one element of the iterable, in order. Thus, every branch is invoked with different input data. Moreover, each branch has the same head node function. In other words, you're applying the same computation on different data in parallel. This flavor of one-to-many transition is useful when you need to break up a large dataset into chunks and process each chunk in parallel.

A many-to-one transition represents a fan-in where a single head node function is invoked with the outputs of multiple tail node functions. In Unum, the tail nodes' outputs are grouped into an ordered array and the head node function invoked with this array as its input. An important feature of many-to-one transitions is that the head node function is invoked only when all tail node functions' outputs become available. 

## The IR Language

Each unum function has an unum configuration file (`unum-config.json`) that instructs the runtime what orchestration actions to take, that is whether it should invoke a function, which function(s) to invoke, and what input data to send.

An unum configuration is a JSON file with the following fields:

```
{
    "Name": "ThisFunctionName",
    "Next":
        {
                "Name": "FunctionName",
                "Conditional": "BooleanExpression"
        }, |
        [
            {
                "Name": "FunctionA",
                "Conditional": "BooleanExpressionA"
            },
            {
                "Name": "FunctionNameB",
                "Conditional": "BooleanExpressionB"
            },
            ...
            {
                "Name": "FunctionNameN",
                "Conditional": "BooleanExpressionN"
            }
        ],
    "NextInput": 
        "Scalar" |
        "Map"    |
        {
            "Fan-in": {
                "Values": [
                    "ExplicitPointerName",
                    "GlobPattern"
                ],
            "Wait": true | false
            }
        },
    "Fan-out Modifiers" :
        [
            "Pop",
            "$size = $size - 1",
            "$0 = $0+1",
            ...
        ],
    "Checkpoint": True | False,
    "Start": True | False,
}
```

## Next

`Next` specifies the function or functions that should be invoked next with my
user function's return value. It is either a single JSON object with a **Name** and a **Conditional** field or an array of such elements.

The **Name** field is the next function's name. It should match one of the names from the `unum-template.yaml` (See [unum Template Documentation](https://github.com/LedgeDash/unum-compiler/blob/main/docs/template.md) for more details).

The **Conditional** field is a boolean expression. A next function will be invoked only if its Conditional field evaluate to true.

[unum rumtime variables](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md#runtime-variables) can be used in the Conditional expression. For instance, we can make the last fan-out function to be the only one that performs a fan-in by setting:

```
{
    "Name": "NextFunction",
    "Conditional": "$0 == $size-1"
}
```



## NextInput

`NextInput` controls what value to invoke the next function(s) with.

`Scalar` instructs the runtime to send the entire return value as a whole
and that's the only value it needs to send to the next function.

`Map` means that the user function should return a list and for each element
of the list, the runtime should invoke a next function with the element as
input.

`Fan-in` is used for perform a fan-in where the next function expects not only my return value but the return value of another unum function (thus a fan-in). `Fan-in` has a `Values` field that is a list of return value names. Each name identifies a particular function's return value. The list contains all return values names that's part of the next function's input, including this function's own. When a function has `Fan-in` as its `NextInput`, it will first check if all values exist in the intermediary data store before invoking the next function.

A name in the `Values` list can be explicit name such as

1. `Hello-output.json`
2. `F-unumIndex-1.1.0-output.json`

Or it could contain unum runtime variables and glob patterns such as

1. `F-unumIndex-1.*-output.json`
2. `F-unumIndex-$1.0-output.json`

See the [unum Runtime Documentation](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md) for more details on function return value naming conventions, unum runtime variables and glob patters.

The `Wait` field in `Fan-in` controls whether the function will wait until all values in the `Values` field become available. If  `Wait` is true, the function will keep waiting until either all values become available or timeout by the FaaS system. While waiting, the function periodically checks the values' existence. When all values becomes available, it invokes the continuation. If `Wait` is false, the function will check only once if all values are available. If they are, the function will invoke the continuation; if not, the function simply terminates.

The `Wait` field can be used in combination with the `Conditional` field to control which function performs fan-in. For example, in a map fan-out, the fan-out function might have a configuration similar to the following

```
{
    "Name": "FanoutFunction",
    "Next":
        {
                "Name": "Fan-in Function",
                "Conditional": "$0 == $size -1"
        },

"NextInput": 
        {
            "Fan-in": {
                "Values": [
                    "FanoutFunction-unumIndex-*"
                ],
                "Wait": true
            }
        }
}
```

The `"Conditional": "$0 == $size -1"` makes sure that only the last function will invoke the continuation. The `Wait: true` make sure that the last function will actually invoke the continuation regardless of its completion order relative to other fan-out function instances.

## Checkpoint

`Checkpoint` controls whether to write the *user function's* return value to the intermediary data store.

Fan-in functions always have `Checkpoint` set to True.

Programmers can also set `Checkpoint` to True for debugging

TODO: Fault-tolerance

## Start

The entry function of a workflow should have the `Start` field set to True. In a unum workflow, only one function should have its `Start` field set to True.

To invoke an unum workflow, invoke its entry function. The entry function will create a session context in the intermediary data store. All subsequent functions during that invocation will write its return value under the session context. See the [unum Runtime Documentation](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md) for more details.

## Fan-out Modifiers

The `Fan-out Modifiers` is an ordered list of operators that can modify the `Fan-out` field in the input JSON during runtime. It controls the `Fan-out` field content of the *output*, i.e., the input to the next function.

`Pop`: The `Fan-out` field forms a stack structure, with the earliest `Fan-out` in the bottom `Outerloop` field (see the [unum Runtime Documentation](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md) for [examples](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md#nested-parallel--map-fan-out--fan-in)). The `Pop` operator removes the top element from the `Fan-out` stack. If there's only one element in the stack, the `Fan-out` field is removed.

`$size`: fan-out modifiers support unum variables. `$size` is an unum variable that refers to the `Size` field of the top element in the `Fan-out` stack.

The ability to modify the `Size` field helps support applications that use partial fan-in across parallel pipelines. For [example](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md#partial-fan-in-pipeline-parallelism).

`$N`: `$N` is another set of unum variables that refers to the current function's fan-out index at depth N. For instance, `$0` is the `Index` field of the top element in the `Fan-out` stack.

Being able to update the fan-out index enables fold operations on a set of fan-out functions. For [example](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md#fan-out-and-fold).



## End/Leaf Functions

If a function is the end of its workflow, it will not invoke another function as part of its continuation, and its `unum-config.json` will be an empty JSON object `{}`. End functions still need to have a `unum-config.json` files packaged with it.

-----------



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

![fan-out-generic](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/fan-out-temp.jpg)

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

![data-dep-parallel](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/data-dep-parallel.jpg)

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

![runtime-io-example-map-fanin-across-maps](https://raw.githubusercontent.com/LedgeDash/unum-compiler/main/docs/assets/runtime-io-example-map-fanin-across-maps.jpg)

S' `unum-config.json`.



