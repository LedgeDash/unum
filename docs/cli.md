# Unum Command-line

## Getting Started

### Applications with a high-level application definition (e.g., a AWS Step Functions)

```text
myapp/
 |- unum-template.yaml
 |- unum-step-functions.json
 |- function1/
   |- app.py
   |- requirements.txt
 |- function2/
   |- app.py
   |- requirements.txt
 |- function3/
   |- app.py
   |- requirements.txt
```

1. Compile to generate the Unum IR (i.e., added functions,
   `unum_config.yaml` for each function and updated Unum template)
2. Build to generate a deployable package for a specific target platform
   (i.e., platform-specific template and functions loaded with the Unum
   runtime for that platform)
3. Deploy the package to the target platform

### Applications with hand-written Unum IR

```text
myapp/
 |- unum-template.yaml
 |- function1/
   |- app.py
   |- requirements.txt
   |- unum_config.yaml
 |- function2/
   |- app.py
   |- requirements.txt
   |- unum_config.yaml
 |- function3/
   |- app.py
   |- requirements.txt
   |- unum_config.yaml
```

1. Build to generate a deployable package for a specific target platform
   (i.e., platform-specific template and functions loaded with the Unum
   runtime for that platform)
2. Deploy the package to the target platform

### Undeploy

### Remove build artifacts

### Delete Unum IR

### Updating and testing after making changes



## Commands

### init

```bash
$ unum-cli init
--name <VALUE>
[--template]
```

Create a directory named `VALUE` in the current directory and initialize it as a  Unum application.

Use the `--name <VALUE>` to choose the name of your application. The CLI will create a directory named `VALUE` under the current directory.

Use the `--template` option to select from available starter projects in the Unum appstore. Examples include applications that use chain, map, or fan-out patterns.

If `--template` option is not used, the CLI will set up a basic boilerplate application with 

1. A Unum template file named `unum-template.yaml`
2. Two function directories with one named `hello` and the other named `world`
3. A Step Function definition, named `unum-step-functions.json`, that chains the two functions



### compile

```bash
$ unum-cli compile
[--unum-template <PATH_TO_FILE>]
[--workflow-type <VALUE>]
[--workflow-definition <PATH_TO_FILE>]
```

Given a Unum application, compile it into the Unum IR.

Unum application = 

1. A set of FaaS functions written as regular functions for the target
   platform. Example: Python Lambda functions
2. A workflow definition. Example: AWS Step Functions state machine
3. A Unum template listing the functions and global configurations

Unum IR = 

1. Added functions written as regular functions for the target platform.
   Example: an added map function when the entry state of the Step Functions
   definition is a `Map` state.
2. Unum configuration files, one for each function, including added functions
3. Updated template file to include the added functions

Run this command inside a Unum application directory.

By default, the CLI looks for a `unum-template.yaml` file in the current directory. Users can specify `--unum-template <PATH_TO_FILE>` to overwrite the default behavior.

Users can specify the workflow type and where the workflow definition is in the Unum template (See `WorkflowType` and `WorkflowDefinition` in the [Unum Template Documentation]()).

Users must either set `WorkflowType` in the Unum template or  pass in `--workflow-type <VALUE>`.

Users can specify where the workflow definition is via `WorkflowDefinition` in the Unum template. Passing in `--workflow-definition <PATH_TO_FILE>` takes precedence over the value of `WorkflowDefinition`.  If no value is specified via `WorkflowDefinition` or `--workflow-definition`, CLI defaults to `unum-step-functions.json` if the workflow type is "step-functions".

The Unum template contains the names and filesystem locations of all the functions in the application. The CLI checks whether the names match what's in the workflow definition and uses those names to know which function is which step of the workflow.





### build

Given a Unum IR, generate deployable packages for a specific target platform

Unum IR = 

1. A set of FaaS functions, including added functions generated in the
   compilation stage, written as regular functions for the target platform.
   Example: Python Lambda functions
2. A set of Unum configuration files, one for each function
3. A Unum template file

Deployable package = 

1. A platform-specific template. Example: AWS SAM template, AWS CloudFormation
   template
2. A set of FaaS functions loaded with the Unum runtime and whose entry points
   are the Unum runtime.

### deploy

Given a platform-specific deployable package, deploy it onto the target platform

1. Create all the FaaS functions
2. Create the intermediate data store if not already exist

----



`compile`

Run `init`

Copy each function into `.unum` and add to it a `unum_config.yaml`.

Copy the unum template file, make updates if necessary, and put it to `.unum`.

Input: 

Workflow definition that is Step Functions or something else

Template file because I need to know which function name in the Step Functions definition refers to which directory.

Output: A set of unum functions and optionally updated unum template

For each function, generate an `unum_config.yaml`.

Generate additional functions. For instance, a function that performs map. And update the unum template.

`template`

Run `init`

Generate platform-specific template file from the unum template

Depends on `compile` because without running `compile` first, the unum template may not contain all the necessary functions.

`build`

Check if each function is a unum function (i.e., a function with `unum_config.yaml`). If yes, then load each with the target platform's runtime and then build with the target platform's toolchain (e.g., `sam`)

If the application has a Step Functions, the developer better has called `compile` already to make sure all necessary functions are generated and all functions are unum functions. If the application is handwritten, all functions should be present and all functions should be unum functions without running `compile`.

Need to make sure the target platform has a template file already generated. For instance, `template.yaml` for `sam`. If not, `build` should call `template` to generate it. This is necessary because otherwise `build` cannot run the target platform's toolchain (e.g., `sam` cannot run).


Input:

unum functions

Output:

platform-specific executables


`init`

create the `.unum` directory. 

Download unum runtime for all platforms into `.unum/runtime`. For instance `.unum/runtime/aws`
