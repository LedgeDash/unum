# Get Started
To compute the unum IR from a Step Functions state machine, run:

```bash
./sf.py -t <path-to-unum-template.yaml> -w <path-to-step-functions-state-machine>
```

```
-t --template the unum-template.yaml for the workflow [REQUIRED]
-w --workflow the Step Functions definition of the workflow [REQUIRED]
-p --print print the computed IR to STDOUT
-u --update update generate unum-config.json files
```
# How the Transformation is Done (wip)

Typical SF state that invokes a Lambda:

```json
"StateName": {
	"Type": "Task",
    "Resource": "arn:aws:lambda:us-west-1:<account-id>:function:<function-name>",
    "Next": "AnotherStateName"
}
```

If this is a leaf state (i.e., doesn't have a next state after completion):

```json
"StateName": {
	"Type": "Task",
    "Resource": "arn:aws:lambda:us-west-1:<account-id>:function:<function-name>",
    "End":true
}
```



The frontend compiler takes a Step Functions definition, a `unum-template.yaml` and a set of directories, one for each function in the `unum-template.yaml` and generates a set of `unum-config.json` files and optionally updates the `unum-template.yaml`. The frontend compiler has multiple modes. 

1. Takes a Step Functions definition whose `Resource` fields are *aws arns*. This means that the functions are already deployed (with or without unum runtime). The frontend compiler just generates the `unum-config.json` field for each function.

   How to update each function with the new `unum-config.json` file?

   If there is a `function-arn.yaml` file, the compiler can find the function names and therefore the function's code directory and just place the new `unum-config.json` file there. Afterwards, new `unum-config.json` files can be deployed by `unum-cli deploy -b`. This means that *the unum functions have to be already deployed by the `unum-cli`*.

2. Take a Step Function definition whose `Resource` fields are *unum function names*, generate a `unum-config.json` file for each function. Each function that appear in the `Resource` field should have a directory with the same name in the current directory with the function's code. The generated `unum-config.json` files will have the `Next` fields being unum names (not aws arns).

   The results will be the same as hand-writing `unum-config.json` files. and the application should be deployable by `unum-cli deploy -b`.

It is possible for the Step Functions frontend compiler to add functions (see below). Therefore, it might add functions to the `unum-template.yaml` file as well as change which function is the `Start` function.

The `StateName` is entirely ignored.

All `Task` states are assumed to be Lambda functions.


