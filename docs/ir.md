# Unum Intermediate Representation

## Overview

The Unum intermediate representation (IR) expresses serverless applications that consist of many FaaS functions. Applications are modeled as directed graphs where nodes are FaaS functions and edges are transitions between functions. The Unum IR expresses such a directed graph by encoding each node with its outgoing edges in a separate file. For example, an application that comprises of 5 functions would have 5 files in its Unum IR, one for each function that encodes the function's node in the direct graph as well as the node's outgoing edges.

Application developers can write the Unum IR directly for each function to build applications. Alternatively, they can provide an AWS Step Functions definition to the Unum frontend compiler, and the compiler can translate the state machine into a set of Unum IR files, one for each function in the application.

During execution, the [Unum runtime library](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md) reads the Unum IR and performs orchestration operations based on the IR. Orchestration operations include invoking the next unum function with the current function's result, checkpointing the current function's output, signaling a branches completion by updating the Completion Set data structure, etc. For more details, see documentation on [the Unum runtime](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md).

### Transitions

<p align="center">
  <img src="https://raw.githubusercontent.com/LedgeDash/unum/main/docs/assets/ir-transitions.jpg">
</p>

Transitions between nodes in the Unum IR can be one-to-one, one-to-many or many-to-one. A one-to-one transition chains two functions together where the head node function is invoked when the tail node function's result becomes available. The input to the head node function is the output of the tail node function.

A one-to-many transition represents a fan-out where the output of the tail node function is "broadcasted" to many "branches". The head node function of each branch is invoked when the tail node function's result becomes available.

There are two flavors of one-to-many transitions in Unum. The first flavor is similar to AWS Step Functions' [Parallel state](https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-parallel-state.html) where the input to every branch's head node function is the output of the tail node function. In other words, every branch is invoked with the same input. This flavor of one-to-many transition is useful when you need to process the same data in different ways, where each branch has a different head node function and all branches can run in parallel. The other flavor of one-to-many transition is similar to AWS Step Functions' [Map state](https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-map-state.html) where the tail node function outputs an iterable (e.g., an array) and the input to each branch's head node function is one element of the iterable, in order. Thus, every branch is invoked with different input data. Moreover, each branch has the same head node function. In other words, you're applying the same computation on different data in parallel. This flavor of one-to-many transition is useful when you need to break up a large dataset into chunks and process each chunk in parallel.

A many-to-one transition represents a fan-in where a single head node function is invoked with the outputs of multiple tail node functions. In Unum, the tail nodes' outputs are grouped into an ordered array and the head node function is invoked with this array as its input. An important feature of many-to-one transitions is that the head node function is invoked only when all tail node functions' outputs become available. 

## The IR Language

In practice, each function itn an Unum application has an IR file that encodes the function's node in the directed graph as well as the node's outgoing edges. The Unum IR language uses YAML and has the following fields to encode nodes and edges,

```yaml
Name: this function's name
Next:
    Name: next/head function name
    Type: Scalar | Map | Fan-in
    Values: an array of invocation names (When Type: Fan-in)
    Conditional: boolean expression (Optional. Default True)
    Payload Modifiers: an array of modifier instructions (Optional. Default None)
Start: boolean (Optional. Default False)
Checkpoint: boolean (Optional. Default True)
```
By default, the Unum runtime expect this file to be named `unum_config.yaml` and each function of an Unum application should have its own `unum_config.yaml` that is package together with user-defined FaaS function code and the Unum runtime library. For more details, see documentation on [the Unum runtime](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md).

### Name

The `Name` field specifies the function's name which can be any valid ASCII strings. Each function must have a name that's unique within its application. The application's name is specified in the Unum template and not in each function's `unum_config.yaml`. When deploying applications, Unum by default names the deployed FaaS function `<application name>-<function name>`. That is if you deploy your application on AWS, your Lambda functions will have names of `<application name>-<function name>`. See [Unum template documentation](https://github.com/LedgeDash/unum/blob/main/docs/template.md) and [Unum CLI documentation](https://github.com/LedgeDash/unum/blob/main/docs/cli.md) for more details.

### Start

`Start` is set to True for entry functions of applications. Users invoke an application by invoking its entry function. At runtime, the Unum library checks if `Start` is true, and if yes, adds a `Session` field to the runtime payload that uniquely identifies each application invocation. See the [Unum runtime documtation](https://github.com/LedgeDash/unum/blob/main/docs/runtime.md) for details.

### Checkpoint

`Checkpoint` is a boolean field that controls whether a node's output is checkpointed into the data store. Checkpoints directly affect the execution guarantees of applications. When `Checkpoint` is set to false, application are executed at-least once; whereas when `Checkpoint` is true, applications are executed exactly-once.

### Next

The `Next` field specifies the outgoing edges. If there is only one outgoing edge (i.e., a chain or a one-to-one transition), the `Next` field contains only a single object. For example,

```yaml
Name: A
Next:
  Name: B
  Type: Scalar
Start: True
Checkpoint: True
```

If there are multiple outgoing edges (i.e., a fan-out or one-to-many transition), the `Next` field specifies an array of objects. For example,

```yaml
Name: A
Next:
  - Name: B
    Type: Scalar
  - Name: C
    Type: Scalar
Start: True
Checkpoint: True
```

The object that encodes an outgoing edge has up to five fields:

* `Name`: the function name of the head node function of this outgoing edge
* `Type`: specifies the type of this transition. The standard IR supports 3 different values for `Type`:
   - `Scalar`: The output of the tail node is treated as a single scalar entity when passed as input to the tail node function of this edge.
   - `Map`: The output of the tail node is treated as a iterable, and each element of the output is passed to one invocation of the tail node function as input. That is the tail node function is invoked x number of times where x equals the size of the iterable output of the tail node.
   - `Fan-in`: The output of the tail node is grouped together with the outputs from other functions and passed as input to the tail node function of this edge in the form of an ordered array. All values needed to invoke the head node function is specified in the additional `Values` field which is only used when `Type: Fan-in`.
* `Values`: Only used when `Type` is `Fan-in`. `Values` lists, *in order*, the invocation names of all tail node functions whose outputs are needed to invoked the head node.
* `Conditional`: A boolean expression that controls whether or not this edge is taken at runtime. The boolean expression can contain runtime variables such as the invocation name. An edge is executed, i.e., the head node function is invoked, only when its `Conditional` evaluates to true. By default, such as when `Conditional` is not even specified, `Conditional` is set to true.
* `Payload Modifiers`: A list of modifier instructions that can change the value of runtime variables and states of the execution. See below for more details.

The following examples illustrate how Unum uses the above object to encode and support a variety of transitions.

#### Chaining

To chain a B function to an A function, A's IR would look like,

```yaml
Name: A
Next:
  Name: B
  Type: Scalar
Start: True
```

#### Branching

To branch on A's result and invoke B if the result is above some threshold (e.g., 50) or otherwise invoke C, A's IR would look like,

```yaml
Name: A
Next:
  - Name: B
    Type: Scalar
    Conditional: "$out > 50"
  - Name: C
    Type: Scalar
    Conditional: "$out <= 50"
Start: True
```

`Conditional` is the field that specifies the branching logic. `$out` is a Unum runtime variable that refers to the output of the function.

#### Map

If A outputs a list and wants to further process each element of the list with B, A's IR would look like,

```yaml
Name: A
Next:
  Name: B
  Type: Map
Start: True
```

The number of B invocations would equal to the size of A's output list. Moreover, each B invocation would be assigned a unique index at runtime to distinguish the B function invocations that are on different branches. For instance, the B invocation that processes the 1st element in A's output list would be assigned a branch index of 0. In general, it's important that every function invocation can be uniquely identified, and assigning branches unique indexes is one mechanism that Unum employs to guarantee unique naming. See the [Unum runtime documtation](https://github.com/LedgeDash/unum/blob/main/docs/runtime.md) for details.

#### Fan-out

To fan-out A's output as a single scalar entity to multiple head node functions, A's IR would look like,

```yaml
Name: A
Next:
  - Name: B
    Type: Scalar
  - Name: C
    Type: Scalar
Start: True
Checkpoint: True
```

Similar to the Map case, each branch of a fan-out is assigned a unique branch index at runtime based on the order a branch appears in the `Next` field. For instance, function B in this case would be assigned index 0 and C index 1. Even though branches in fan-out have head node functions of different names, assigning branch index help distinguish invocations at runtime when fan-outs are nested. See the [Unum runtime documtation](https://github.com/LedgeDash/unum/blob/main/docs/runtime.md) for details.

#### Fan-in

To fan-in the outputs of multiple tail nodes into a single head node, both tail nodes need to use the edge object with `Fan-in` type. For example, if A and B fan-in to C, A and B would have IR that looks like,

```yaml
Name: A
Next:
  Name: C
  Type: Fan-in
  Values: [A, B]
```

```yaml
Name: B
Next:
  Name: C
  Type: Fan-in
  Values: [A, B]
```

Both A and B would specify C as the next node and the `Values` field lists the names of *invocations* whose outputs are required before the fan-in head node---C in this case---can be invoked. Note that the `Values` field must list the names in the same order in all tail node functions' IR, because the tail nodes' outputs are passed to the head node function in the order specified in the `Values` field.

Most likely, A and B are first created as branches of a fan-out. For instance, an S function first fan-out to A and B,

```yaml
Name: S
Next:
  - Name: A
    Type: Scalar
  - Name: B
    Type: Scalar
Start: True
Checkpoint: True
```

In this case, the A and B invocations will have branch indexes 0 and 1. For A and B to fan-in to C, the names in `Values` should include the branch index. For instance, the default runtime library expects branch indexes to appear after a `-UnumIndex-` string,

```yaml
Name: A
Next:
  Name: C
  Type: Fan-in
  Values: ["A-UnumIndex-0", "B-UnumIndex-1"]
```

```yaml
Name: B
Next:
  Name: C
  Type: Fan-in
  Values: ["A-UnumIndex-0", "B-UnumIndex-1"]
```

*The index is known a priori at compile time* because the directed graph that the IR express is static. For dynamic patterns such as Map, Unum supports wildcard characters and globbing in the IR which expands at runtime. For instance, if S maps to many branches of A and the A's fan-in to B, A's IR would look like,

```yaml
Name: A
Next:
  Name: B
  Type: Fan-in
  Values: ["A-UnumIndex-*"]
```

If S' output list has size 3, there will be 3 A invocations and `[A-UnumIndex-*]` would expand to `[A-UnumIndex-0, A-UnumIndex-1, A-UnumIndex-2]` at runtime. The globbing process uses Unum's payload metadata at runtime.


See the [Unum runtime documtation](https://github.com/LedgeDash/unum/blob/main/docs/runtime.md) for details.

Additionally, you might want to further manipulate the payload metadata to indicate that the fan-out has ended and clear the metadata to be,

```json
{
    "session": "deadbeef",
}
```

To do this, Unum supports payload modifiers which are instructions that modifies the payload metadata. For instance, to remove a fan-out field from the payload, the standard library supports a `Pop` instruction. To use the `Pop` instruction, A's IR would look like,


```yaml
Name: A
Next:
  Name: B
  Type: Fan-in
  Values: ["A-UnumIndex-*"]
  Payload Modifiers: ["Pop"]
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



