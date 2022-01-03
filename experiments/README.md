# Experiments


## Catch

Support for the `Catch` field in Step Functions.

Use the `catch` workflow for experiments.

The `catch` workflow calls `raise` in user Python code. "User Python code"
here refers to the user code from Unum's perspective. It doesn't matter
whether `raise` happens in the user code or in the Unum runtime code because
from Lambda's perspective, it's all "user" code, and what we care about is to
successfully trigger the failure destination lambda so that the failure can be
handled.

Things to figure out:

1. Do Step Functions distinguish different kinds of Lambda failures or are all
   failures treated the same (e.g., `Lambda: Unknown`)?

2. Failure destination feature in Lambda. Does Lambda trigger the failure
   destination lambda on the first failure or after the configured number of
   attempts?

3. What information is sent to the failure destination lambda?

4. In the Step Functions way, how does a Catch work? Does it specify one of
   the states in the state machine?

5. If we support `Catch` does that satisfy the "progress requirement" that
   workflows do not get stuck?

6. Since the point is to trigger our own failure handling logic by running a
   failure destination lambda, there's a pretty flexible design space here. We
   can have a single lambda being the failure handling entry point and have
   developers provide additional lambdas for failure handling. Or have
   different failure destination lambdas for each state as specified and just
   have the failure handling logic in the runtime. The aforementioned two are
   specific to what Lambda provides today. But the idea is very general and
   can work with other FaaS interfaces. For example, if Lambda includes
   metadata in `context` for retries, we can set the actual number of retries
   to be 1 more than the user specified retries and just handle it by the Unum
   runtime on the same lambda. 




## Chaining Performance

## Fan-out Performance

