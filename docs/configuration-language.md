# unum Configuration Language

Each unum function has an unum configuration file that instructs the runtime
what orchestration actions to take, that is whether it should invoke a
function, which function(s) to invoke, and what input data to send. An
unum configuration is a JSON file with the following fields:

```
{
    "Next": "next function's name" | [<function names>],
    "NextInput": "Scalar" | "Map" | "Fan-in"
    "WaitFor": "Map" | [<function names>]
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
* Simple programming such as `$MyIndex`.
TODO


|  | Scalar | Map |
|-|-|-|
| F1 | invoke F1 with user function's return value | User function return a list. Invoke an instance of F1 for each element of the list |
| [F1, F2] | invoke both F1 and F2 with user function's return value | User function return a list. Invoke an instance of F1 and an instance of F2 for each element of the list |


## Patterns

The unum configuration can express common orchestration patterns such as
chaining, fan-out and fan-in.


Mapping between unum configuration and Step Functions states

|  | Scalar | Map |
|-|-|-|
| F1 | Chain | Map |
| [F1, F2] | Parallel | Parallel with 2 branches. Each branch being a Map. |


### Cases Beyond Step Functions

Fan-in to multiple next functions. Step function always fan in to a single node.

Map user function's output + waitfor/fan-in with another function

Invalid combination: NextInput: scalar, Waitfor:map.