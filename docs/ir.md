# Unum Intermediate Representation

## Overview

The Unum intermediate representation (IR) expresses serverless applications that consist of many FaaS functions. Applications are modeled as directed graphs where nodes are FaaS functions and edges are transitions between functions. The Unum IR expresses such a directed graph by encoding each node with its outgoing edges in a separate file. For example, an application that comprises of 5 functions would have 5 files in its Unum IR, one for each function that encodes the function's node in the direct graph as well as the node's outgoing edges.

Application developers can write the Unum IR directly for each function to build applications. Alternatively, they can provide an AWS Step Functions definition to the Unum frontend compiler, and the compiler can translate the state machine into a set of Unum IR files, one for each function in the application.

During execution, the [Unum runtime library](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md) reads the Unum IR and performs orchestration operations based on the IR. Orchestration operations include invoking the next unum function with the current function's result, checkpointing the current function's output, signaling a branches completion by updating the Completion Set data structure, etc. For more details, see documentation on [the Unum runtime](https://github.com/LedgeDash/unum-compiler/blob/main/docs/runtime.md).

### A Note on Implementation and Customization

An important point of Unum is to demonstrate what you can achieve on the application-level for orchestrating serverless applications. The general idea of the Unum IR is to use a platform-agnostic representation that encodes serverless applications as directed graphs. Moreover, the representation encodes in a decentralized manner where each node is encoded along with its outgoing edges. Such a design not only allows Unum to support existing higher-level programming interfaces such as AWS Step Functions, but also enables orchestration to execute with a logically-centralized controller.

Therefore, it is worth noting that the implementation of Unum IR described in this document is one possible implementation of the general idea. This implementation may not be the best or richest realization of the idea, but the point is that developers, without the help or control of cloud providers, can create other implementations of this idea to build and run complex serverless applications.

The goal of this document is to demonstrate this implmetation and show how one would create an IR that is capable of support a superset of applications possible with AWS Step Functions. We hope this work will inspire developers to create other custom-made IRs that are optimized for their applications' use cases.

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

To fan-in the outputs of multiple tail nodes into a single head node, all tail nodes need to use the `Fan-in` type when specifying their outgoing edges. For example, if A and B fan-in to C, A and B would have IR that looks like,

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

*The index is known a priori at compile time* because the directed graph that the IR expresses is static.

For dynamic patterns such as Map, Unum supports wildcard characters and globbing in the IR which expands at runtime. For instance, if S maps to many branches of A and the A's fan-in to B, A's IR would look like,

```yaml
Name: A
Next:
  Name: B
  Type: Fan-in
  Values: ["A-UnumIndex-*"]
```

If S' output list has size 3, there will be 3 A invocations and `[A-UnumIndex-*]` would expand to `[A-UnumIndex-0, A-UnumIndex-1, A-UnumIndex-2]` at runtime. The globbing process uses Unum's payload metadata at runtime. Specifically, in this example, the runtime library would perform globbing using the `Fan-out` field in the input payload to the A invocations. Each A invocation would receive an input that looks like,

```json
{
    "Session": "8cef2097-f6fa-4fa2-bc70-7aa7bbbc23d9",
    "Fan-out": {
        "Size": 3,
        "Index": 0
    }
}
```

The `Fan-out` field is added by S when invoking the A functions. The runtime on A would expand `A-UnumIndex-*` using the `Size` field knowing that there are in total 3 A invocations. See the [Unum runtime documtation](https://github.com/LedgeDash/unum/blob/main/docs/runtime.md) for details on how the runtime interprets and executes the IR.

Additionally, Unum supports payload modifiers which are instructions that modifies the payload metadata. They enable further manipulating the payload metadata. For instance, to remove a fan-out field from the payload, the standard library supports a `Pop` instruction. To use the `Pop` instruction, A's IR would look like,

```yaml
Name: A
Next:
  Name: B
  Type: Fan-in
  Values: ["A-UnumIndex-*"]
  Payload Modifiers: ["Pop"]
```

The `Pop` instruction would remove the `Fan-out` field from the input payload when A's fan-in to B such that B's input would look something like the following without a `Fan-out` field,

```json
{
    "Session": "8cef2097-f6fa-4fa2-bc70-7aa7bbbc23d9"
}
```

`Pop` is useful when you have nested fan-outs and maps.

### Unum Runtime Variables

Many complex interactions require additional control over the runtime metadata. To provide the necessary programmability, Unum IR supports a set of runtime variables. Through the runtime variables, developers can read and write runtime metadata. To learn more about the runtime metadata supported in the Unum standard library, please see the [Unum runtime documtation](https://github.com/LedgeDash/unum/blob/main/docs/runtime.md).

Unum runtime variables can appear in `Conditional` as part of the boolean expression, in `Values` as part of the invocation names, or in `Payload Modifiers` as part of the modifier instructions. The following is a list of Unum variables currently supported in the standard library and their example use cases:

- `$out` refers to the output of the function.
   * You can branch on the function output by using `$out` in the `Conditional` field of the IR as shown in the branching example previously
   * You can manually set the output of a function by writing to `$out` in the `Payload Modifier`, for example `$out="Hello World"`
- `$n` where n is a non-negative integer refers to the branch index of the nth fan-out. For instance, `$0` is the index of the most recent fan-out (i.e., the inner-most loop), `$1` is the index of the 1st outer loop, so on and so forth.
   * You can control which branch in a Map moves forward to execute the edge and invoke the head node. For example, to only have branches with even indexes (or every other branch) invokes the head node, use `Conditional: "$0 % 2 == 0`.
   * You can have each branch fan-in with its next branch by specifying the `Values` as `[A-UnumIndex-$0, A-UnumIndex-($0+1)]` and setting the `Conditional` as `$0<$size-1` so that the last branch do not try to fan-in with its next branch which does not exist and whose index is out of bound.
   * You can modify the index in the `Payload Modifier`, for example `$0=0`, or `$0=$0+1"`.
- `$size` refers to the number of branches in the most recent fan-out (Unum supports nested fan-outs. The most recent fan-out is the inner-most loop).
   * We've seen an example of using `$size` in the `Conditional: $0<$size-1` to prevent the last branch from fan-in with a non-existent branch.
   * You can modify the size in the `Payload Modifier`, for example `$size=3`, or `$size=$size-1"`.

### Payload Modifiers

`Pop` is the only modifier currently supported in the standard library. It is designed to support nested fan-out and fan-in by removing the outer-most `Fan-out` object in the payload metadata.

Users can add any payload modifier instructions they deem necessary. Unum's design allows developers to fully custom the orchestration logic.

<!-- ## Additional Examples

### Nested Fan-out and Fan-in

### Pipeline Parallelism/Partial Fan-ins

 -->
