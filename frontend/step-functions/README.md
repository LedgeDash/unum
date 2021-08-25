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

# Cases where the Step Functions compiler adds functions

## Starts with a Map State

Inputs to the Map state are arrays. For each element of the array, the Map state invokes one parallel instance of the `Iterator`.

An example from excamera:

```json
"vpxenc and xcdec": {
  "Type": "Map",
  "ItemsPath": "$.chunks",
  "ResultPath": "$",
  "MaxConcurrency": 0,
  "Next": "Group",
  "Iterator": {
    "StartAt": "vpxenc",
    "States": {
      "vpxenc": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-west-1:746167823857:function:excamera-stepfunction-basic-vpxenc",
        "Next": "xcdec"
      },
      "xcdec": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-west-1:746167823857:function:excamera-stepfunction-basic-xcdec",
        "End": true
      }

    }
  }
}
```



We can't do any tricks on the first function of the `Iterator` to achieve the Map state's behavior. It seems to me that the only option is to add a function that serves as the fan-out initiator. It accepts arrays, does nothing and simply returns them. Its `unum-config.json` will have `NextInput: Map` so that the unum runtime will invoke an instance of the `Next` function for each element of the array.

In essence, we're transforming the Step Function definition to:

```json
"unum map": {
    "Type": "Pass",
    "Next": "vpxenc and xcdec"
},
"vpxenc and xcdec": {
  "Type": "Map",
  "ItemsPath": "$.chunks",
  "ResultPath": "$",
  "MaxConcurrency": 0,
  "Next": "Group",
  "Iterator": {
    "StartAt": "vpxenc",
    "States": {
      "vpxenc": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-west-1:746167823857:function:excamera-stepfunction-basic-vpxenc",
        "Next": "xcdec"
      },
      "xcdec": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-west-1:746167823857:function:excamera-stepfunction-basic-xcdec",
        "End": true
      }

    }
  }
}
```



## Starts with a Parallel State

## Starts with a Choice state





# Combinations

lambda -> lambda

lambda-> parallel

lambda->map

lambda-> choice



Starting with a Map state