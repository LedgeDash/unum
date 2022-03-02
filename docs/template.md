# unum Application Template

unum application template resembles the AWS SAM template.

Should list all functions that are part of the application.

Should have a `WORKFLOW_TYPE` that specifies in what language is the workflow written in. Example values include "step-functions". And a `WORKFLOW_DEFINITION` that is the path to the workflow definition file. These two variables make building and compiling much simpler.

`WORKFLOW_TYPE`: "step-functions"