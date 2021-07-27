unum is a system for building and running stateful FaaS applications.

unum application repository:
[unum-appstore](https://github.com/LedgeDash/unum-appstore)

Minimalistic FaaS Workflow with Distributed Coordination

<!-- Traditionally, stateful FaaS applications are built on platform-specific
coordinators (e.g., Step Functions, Durable Functions Orchestration).
Coordinators are long-running stateful processes that are independent of the
FaaS system where functions execute. Programmers write workflows in the
language of the particular coordinator (e.g., [Amazon States
Language](https://states-language.net/) for AWS Step Functions), and the
workflow code is executed by the provider's custom-made coordinator system.
The system launches a coordinator process for each invocation of an
application, and the process runs until the entire workflow completes.

Coordinators centralize the orchestration logic and make all the orchestration
decisions. All FaaS functions are launched by the coordinator and all
functions' outputs are first sent back to the coordinator. -->

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
a directory with an unum configuration file (`unum_config.json`), the user
function and its dependencies.

The following is an example Python unum function:

```
myfunction/
 |- app.py
 |- mylibrary.py
 |- requirements.txt
 |- unum_config.json
 |- __init__.py
```

`app.py` is the user function. It is written exactly like a normal Lambda
function. `mylibrary.py` is the user library code. `requirements.txt` lists
other Python packages that the function depends on and will be installed via
`pip`. `unum_config.json` is the unum configuration for this particular
function.

An unum application is a directory containing a set of unum functions, an unum
template and the unum runtime. In the following `hello-world-app` example, we
have 2 functions, `hello` and `world`, each in its own directory. The `common`
directory contains the unum runtime for Python applications. The
`unum-template.yaml` is the unum application template.

```
hello-world-app/
 |- hello/
     |- app.py
	 |- requirements.txt
	 |- unum_config.json
	 |- __init__.py
 |- world/
     |- app.py
	 |- requirements.txt
	 |- unum_config.json
	 |- __init__.py
 |- common/
 |- unum-template.yaml
 |- __init__.py
```

See unum application examples in [unum-appstore](https://github.com/LedgeDash/unum-appstore).

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

See [unum Application Template
Anatomy](https://github.com/LedgeDash/unum-compiler/blob/main/docs/template.md)
for more details.



# unum Intermediary Representation

The unum IR expresses serverless workflows using **continuations**. Each function has a continuation that defines what the next function to invoke is and how to invoke it.

unum implements continuations declaratively with a [configuration language](configuration-language). Each unum function is packaged with a `unum-config.json` file where a continuation is defined for that particular function.

Programmers can write the configuration directly or provide a Step Functions state machine to the frontend compiler. The frontend compiler translates the state machine to a set of `unum-config.json` file, one for each function in the state machine.

[Graph: frontends-> IR -> backends]

# unum Runtime

unum runtime wraps around user function code and interposes on user function input and output.

[Graph: wrap]

On a high level, the unum runtime does two things

1. Executes the continuation.
2. Assigns each function invocation a unique name by adding necessary metadata to input payloads



<!--Each unum function has an unum configuration file (`unum_config.json`). The-->
<!--unum runtime uses unum configs to decide what orchestration actions to take-->
<!--after user functions complete, that is whether to invoke a function, which-->
<!--function(s) to invoke, and with what input data.-->

<!--A unum configuration specifies the following information:-->

* <!--which function or functions to invoke next-->
* <!--how to process the user function's output-->
* <!--which function or functions to wait for before invoking the next function-->

<!--After the user function returns, the unum runtime executes the orchestration-->
<!--action based on the unum configuration. Each individual unum function carries-->
<!--out its share of orchestration actions without deligating back to a-->
<!--centralized coordinator service.-->

<!--See [unum Configuration
Language](https://github.com/LedgeDash/unum-compiler/blob/main/docs/configuration-language.md)-->
<!--for more details.-->

# Possible Tooling on top of unum

A monitor process watching the intermediary data store to detect new workflow invocations and function completions and errors. This process can provide a similar graphic UI as the Standard Step Functions.

