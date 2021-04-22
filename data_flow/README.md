# Pipelining

To express a pipeline, you can simple chain them as if they are regular functions:

```python
f3(f2(f1(input)))
```

or you can create intermediary variables for the output of each function:

```python
f1_ret = f1(input)
f2_ret = f2(f1_ret)
f3_ret = f3(f2_ret)
```

Either way, unum will create a pipeline of `f1->f2->f3`. Note that in this
unum pipeline, it is `f1` that sends its output to `f2` and `f2` to `f3`. This
is different from orchestrator based systems where `f1` and `f2` need to first
send their outputs to an orchestrator and the orchestrator then invokes `f2`
and `f3`, respectively.

You could perform transformation on input and output data. For example,

```python
f1_ret = f1(input)
f1_ret = f1_ret["timestamp"] = datetime.now().isoformat(timespec='milliseconds')
f2_ret = f2(f1_ret)
f3_ret = f3(f2_ret)
```

But we recommend that you move them to FaaS functions instead of placing them
in the workflow.

[NOTE] We could support only a small set of restricted transformations,
similar to [Intrinsic Functions in AWS Step
Functions](https://states-language.net/spec.html#intrinsic-functions).

[NOTE] We could forbidden any transformations in the workflow and push them to
functions that programmers write. This should not limit the capability of our
system because programmers can still perform those computations in functions. 

Additionally, not allowing arbitrary computations in the workflow benefits
programmers in terms of billing. Even in orchestrator-based systems where the
orchestrator can perform arbitrary computation, it is still not a good idea to
perform heavy computations in the orchestrator for billing purposes. For
example, in DF, heavy computation means longer restoration time.




* Doesn't yet support composing workflows. Functions called by the workflow
  file are assumed to be leaf functions, not other workflows.
* [TODO] Move to a config file similar to SAM.
* [TODO] Assign should work with multiple left-hand side names


# Python dataflow analysis tools

IBM's pyflowgraph: https://github.com/IBM/pyflowgraph

pyleaf: https://pypi.org/project/pyleaf/

pycfg: https://pypi.org/project/pycfg/

microsoft: Python program analysis: https://github.com/microsoft/python-program-analysis

pyntch: http://www.unixuser.org/~euske/python/pyntch/#source
