A chain of 2 `noop` functions that simply return their inputs.

Faults are manually added to the workflow by calling `raise` in the user code
which will cause the lambda to crash.

