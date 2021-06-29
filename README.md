unum is a system for building and running stateful FaaS applications.

# Getting Started

Run the `setup.sh` script to install the `unum-cli` and its dependencies.

To build an unum application for AWS, run the following command the in an unum
application directory:

```bash
unum-cli build -t -p aws
```

The `-t` option would generate an AWS CloudFormation template (named
`template.yaml`) based on `unum-template.yaml` on the fly. You can also
generate a `template.yaml` without building the applicatoin by running

```bash
unum-cli template -p aws
```

With the `template.yaml` in the directory, you can simply run

```bash
unum-cli build
```

to build the application for AWS. 

To deploy your application to AWS, run

```bash
unum-cli deploy
```

If you want to build before deploying, use the following command to combine the two actions

```bash
unum-cli deploy -b
```

Without the `-b` option, unum will try to deploy the existing build artifacts
and you might see `No changes to deploy` becuase your code changes haven't
been built yet.


For AWS, unum uses [AWS
SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html)
for building and deploying. Build artifacts are in `.aws-sam/` under your
application directory.

# unum Applications and Funtions

An unum application consists of a set of unum functions. Each unum function is
a directory with the following files:

```
myfunction
 |- app.py
 |- requirements.txt
 |- unum_config.json
 |- __init__.py
```

An unum application is a directory containing a set of unum functions and an
`unum_template.yaml` file.

## unum Application Template

The unum application template `unum_template.yaml` describes the functions in
your application. The unum cli translates the template into platform specific
formats that can be used to provision the necessary resources to run your
application.

For example, to deploy your application on AWS, you can generate a [SAM
template](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-specification-template-anatomy.html)
(which is an extension of [the CloudFormation
template](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-guide.html)), with

```bash
unum-cli template -p aws
```


# unum Configurations

```json
{
    "Next": "next function's name" | [<function names>],
    "WaitFor": "Map" | [<function names>] ,
    "NextInput": "Scalar" | "Map" | "Fan-in"  
}
```



# unum Runtime


Cases beyond Step Functions:

Fan-in to multiple next functions. Step function always fan in to a single node.

Map user function's output + waitfor/fan-in with another function

Invalid combination: NextInput: scalar, Waitfor:map.

## Node Types

### ChainNode

Invoke a single next function with the user function's output as a scalar.

"Next": single function
"WaitFor": None
"NextInput": Scalar

### EndNode

Simply exit after the user function returns. There's no subsequent functions to invoke.

"Next": None
"WaitFor": None
"NextInput": None

### MapNode

The user function has to return a list.

For each element of the list invoke an instance of the next function.

"Next": single function or a list of functions
"WaitFor": None
"NextInput": Map


### FanInNode

Write the user function's output to the return value store specified in the `UnumMetadata` field of the input `event`.

If the "Next" field is non-empty, wait for other fan-out functions to complete before invoking the next function.

If the "Next" field is empty, ignore waiting for other fan-out functions and simply exit after writing the output to the return value store.

## ingress

```json
{
	"Data": {
		"Source":"http|s3|dynamodb|redis|elasticache|efs",
		"Value": {}
	},
	"UnumMetadata": {
		
	}
}
```

```json
"Data": {
	"Source":"http",
	"Value": {"<json object>"}
}
```

```json
"Data": {
	"Source":"s3",
	"Value": {
		"Bucket": "<bucket-name>",
		"Prefix": "<prefix>",
		"Fan-in": 5,
	}
}
```

```json
"Data": {
	"Source":"s3",
	"Value": {
		"Bucket": "<bucket-name>",
		"Prefix": "<prefix>"
	}
}
```


```json
"Data": {
	"Source":"dynamodb",
	"Value": {
		"Table": "<table-name>",
		"Item": "<id>",
		"Fan-in": 5,
	}
}
```

```json
"Data": {
	"Source":"dynamodb",
	"Value": {
		"Table": "<table-name>",
		"Item": "<id>"
	}
}
```

### S3 event

Automatically downloads the file to function's local storage (can parallelize
with function execution) and pass it as a file descriptor to the function.

### JSON

If ingress receives a JSON string

Keyword arguments

```json
{"foo": 1, "bar":2}
```

```python
def handle(foo, bar):
	...
```

Positional arguments

```json
{"arg1": 1, "arg2":2}
```

```python
def handle(foo, bar):
	...
```

Ingress runtime will pass 1 to `foo` and 2 to `bar`.

