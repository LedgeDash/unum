A simple fan-out fan-in application that converts text into uppercase. The
purpose of this application is to demonstrate Step Functions' data limitation.

For each chunk of a large text, run a parallel instance of the `upper`
function that converts the chunk into uppercase letters. The `upper` function
returns the uppercase text as its return value (i.e., in Python `return
text.upper()`). All parallel `upper` instances fan-in to a `cat` function that
concatenates the `upper` functions outputs and returns a single string.

With Step Functions, all `upper` instances first return outputs to the Step
Functions instance. If the combined size of all `upper` functions' outputs
exceeds 256KB, Step Functions throws the following error:

```json
{
  "error": "States.DataLimitExceeded",
  "cause": "The state/task 'Uppers' returned a result with a size exceeding the maximum number of bytes service limit."
}
```

