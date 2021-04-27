# Runtime Wrapper

## ingress

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

