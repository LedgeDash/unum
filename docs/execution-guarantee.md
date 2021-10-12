# Execution Guarantee

unum provides *at-least-once execution with exactly-one result*. It means

1. At-least once invocation on individual functions.
2. In a particular workflow invocation, a particular function will always be invoked with the exact same input and produce the exact same output, even if the function is nonidempotent and invoked multiple times.
3. Each workflow invocation will produce exactly one result. This is not to say that invoking a workflow with the same input will always produce the same output, because functions may not be idempotent. But that a particular invocation always produces one result, not multiple.

If we tie the 3 guarantees together and look at it from the workflow perspective, what we can guarantee is that: if none of the functions in the workflow have side-effects (e.g., writing to external services), the workflow will appear to execute exactly-once from an external observer's perspective, even if the functions are nonidempotent. In other words, as far as the "internal states" of workflows are concerned, unum's guarantee is "observationally equivalent" to exactly-once execution.

## Design Challenges

There are 3 challenges that we need to consider when deciding what guarantees we can provide.

### Challenge One: Lambda's asynchronous HTTP invoke API does NOT guarantee exactly once invocation

unum exclusively uses the async HTTP invoke API to trigger Lambdas because it eliminates waiting. The way the API works is that "[Lambda places the event in a queue and returns a success response without additional information. A separate process reads events from the queue and sends them to your function.](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html)" The downside is that, "[it's possible for it (the invokee) to receive the same event from Lambda multiple times because the queue itself is eventually consistent.](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html)" Basically at-least-once event delivery.

What this means is that a single call to the async HTTP invoke API might create multiple instances of the invokee function. The instances might be concurrent, depending on how soon the duplicate instance is triggered and how long the Lambda runs. 

Looking at the problem from the workflow perspective, at-least-once delivery for individual functions can result in multiple final outputs for a single workflow invocation. And if any of the functions are *nonidempotent*, we might see multiple different results for a single workflow invocation.

Anecdotally, duplicate events are usually several minutes after the first delivery, so it's not very close.

### Challenge Two: Faults and Retries

Faults could happen at any point during execution and when they happen, Lambda automatically retries the crashed Lambda twice if it is invoked asynchronously. If a function has side-effects (e.g., writing to external services) and it retries, we might observe the side-effects multiple times.

It is worth noting that retries are sequential and not concurrent. The previous execution has to fail first before the retry happens.

Also, retries are tunable. We can turn it off.

### Challenge Three: Fan-out functions need to correctly synchronize to avoid invoking the fan-in function multiple times

The ideal semantics for fan-in is: invoke the fan-in function once when all of the upstream fan-out functions have completed.

This is relatively easy to do with centralized orchestrators because fan-out functions sends their results back to the orchestrator and the orchestrator is the one that invokes the fan-in function. In unum, however, there isn't a centralized orchestrator. Any one of those concurrent fan-out functions can invoke the fan-in function and we need to make sure that they synchronize correctly. We want to avoid the situation where more than one fan-out functions end up calling the fan-in function.



**How does unum guarantee at-least-once execution with exactly-one result?**

At-least once is given to us by Lambda. The async HTTP invoke API guarantees at-least-once. The question is how to ensure exactly-one result given the 3 challenges laid out previously.

The answer is checkpoint. Each function instance checkpoints by writing an uniquely named item to the unum intermediary data store (e.g., S3, DynamoDB). And the runtime logic goes like this:

First, before running the user function, check to see if a checkpoint already exists. If it does, skip running the user function and simply read from the checkpoint. What's in the checkpoint is my output. And then invoke the continuation with the checkpoint's data.

This makes sure that if a step in the workflow has completed and persisted, it will not run again. It is useful in the case of non-concurrent duplicates, e.g, retries (crashes after checkpoint but before invoking continuations) and duplicate invocations that happen after the original has completed.

If the checkpoint doesn't exist, unum considers the user function not complete and goes ahead and run the user function. After the user function completes, unum checkpoints the output using an atomic `checkpoint_if_not_exist()` operation. The operation checks to see if the checkpoint already exists and only writes the checkpoint if it does NOT exists. All as an atomic operation. If the checkpoint exists, the operation fails without overwriting the checkpoint and returns an error.

It is important for this operation to be atomic because there might be other concurrent instances of the same invocation (Challenge One). The atomic `checkpoint_if_not_exist()` operation makes sure that we only take the result of the 1st instance to finish as the final result of this step. Any instances whose `checkpoint_if_not_exist()` fails due to existing file, simply discard their result and terminate. And the only instance whose `checkpoint_if_not_exist()` succeeds will invoke the continuations.

Note that we don't need this atomic `checkpoint_if_not_exist()` if we don't have *concurrent* duplicate instances. For example, if Lambda changes the async invoke API to exactly-once, or if async invoke duplicates never starts before the original instance completes, we can simply rely on the first check-to-see-if-checkpoint-already-exists test.



Last but not least, how does unum synchronize fan-out functions so that the fan-in function is invoked only once when all upstream fan-out functions complete? We have several options to achieve this:

1. We can use a shared atomic data structure such as an atomic counter in DynamoDB.
2. We can decide at compile time which fan-out instance will perform the fan-in. For example, the fan-out function with the largest index number will perform the fan-in. The downside is that the last function will have to wait for other instances to finish.
3. We can use a storage trigger, e.g., ObjectCreate event on s3 keys. All fan-out functions can write to the key but only the 1st write will trigger the fan-in function. The downside is that we'll require storage systems that support triggers.

Note that simply for the sake of correctness and execution guarantee, we don't need to make sure that the fan-in function is called only once, because the async invoke API already doesn't guarantee that even if the API is called only once. However, in practice this creates at least 2 problems:

1. Duplicate invocations incur billing. In the worst case scenario, the number of fan-in function instances = number of fan-out functions. This weakens our cost-saving argument.
2. The multiple concurrent invocations of the fan-in function makes it nearly impossible to match logs and analyze data for experiments.

In other words, even though the unum runtime can tolerate fan-in functions being called multiple times, it's much better to make sure that they're called only once.



**How does DynamoDB and S3 play into providing the above execution guarantee?**

The main limitation with s3 is that it doesn't have atomic data structures. Therefore,

1. we can't build an atomic `checkpoint_if_not_exist` operation over S3
2. fan-in needs to rely on storage triggers or a pre-selected function.

Our current implementation with s3 is following

1. `checkpoint_if_not_exist` is not atomic. Check file existence and write to s3 are 2 independent operations. So far, I haven't actually encountered any problems because the async HTTP invoke API rarely have duplicate deliveries and when it does, it's always mins later so the instances never run concurrently. But this is not to say that concurrent instances definitely won't happen.
2. I pre-select the fan-out function with the largest index to call the fan-in function. The pre-selected function waits for all other fan-out functions to complete.

DynamoDB can support atomic  `checkpoint_if_not_exist` operation with `ConditionExpression` in the `PutItem` API. So that's not a problem.

For fan-in, I use the atomic counter. None of the fan-out functions need to wait. The last function to finish knows that it's the last to finish by getting the counter value and then invoke the fan-in function.



**What happens when we turn checkpoint off?**

1. Duplicate instances from the async HTTP invoke API essentially create concurrent workflow invocations. From the user's perspective, one workflow invocation can produce multiple final outputs. Moreover, if any of the functions in the workflow is non-idempotent, we can end up with multiple final outputs that are of different values.
2. Retries will execute the user function no matter what, even if it succeeded last time (for instance it crashes after user function completes but before invoking the continuation).

Now, we have the option to turn Lambda's automatic retry off and move that logic to the workflow language/application developer. That way, a workflow just fails when a Lambda fails unless a retry logic is explicitly written in the workflow. This is what Step Function does.

Duplicate instances from the async invoke API is very rare in practice though.

**What happens when the workflow fails at a certain step?**

When a workflow fails at a some point, unum doesn't retry from the beginning but retry fromt the failed step. This is true *regardless of whether checkpoint is turned on or not*, because Lambda automatically retries functions when they crash.

However, we can retry a particular workflow *invocation* by passing in the invocation name (i.e., the session ID). If checkpoint is off, the retry start from the beginning. If checkpoint is on, the retry starts from the function that crashed.

**How does unum's guarantee compare with Step Functions' guarnatee?**

[Step Functions' description on execution guarantee](https://docs.aws.amazon.com/step-functions/latest/dg/express-at-least-once-execution.html) is not entirely clear so I'll make some guess in what they guarantee.

Standard SF's main feature is that it "persists execution state on every state transition". So in the case of a SF instance crashing, the workflow can restart from where it crashes and not from the beginning. Express SF, on the other hand, does NOT persist execution states at all and when SF crashes, "the workflow will be automatically restarted from beginning". 

My guess is that this is the reason why SF calls the Standard Workflows "exactly-once workflow execution" and Express Workflows "at-least-once workflow execution".

However, the documentation doesn't talk about the case where a Standard SF crashes after invoking a Lambda but before the Lambda returns, in which I assume that the Lambda will be executed again since its execution state wasn't persisted.

One important difference is that SF uses the synchronous invoke API for Lambda (a reasonable guess) and that API is exactly once. unum cannot use this API because of double billing and the point of unum being removing centralized orchestrator that waits. So in a way, unum is trading this guarantee for being purely serverless (run only when needed). Also, if Lambda's async invoke API becomes exactly-once, unum can guarantee exactly-once on individual Lambdas too.

Given the above assumption of SF behavior. I believe Standard SF provides the same guarantee as unum with checkpoint ON and Express SF as unum with checkpoint OFF. 
