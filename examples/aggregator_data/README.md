The handler function expects a JSON document of the following format:

```json
{"data":
	[
		{"2021-02-20T08:30:00.000Z":12}, 
	 	{"2021-02-20T09:30:00.000Z":2.5}
	]
}
```

A time series is represented by a JSON array. Each array element is a JSON
object of a single key-value pair, where the key is a string of ISO 8601
formatted timestamp and the value is a JSON number.

The `invoke.py` emulates a FaaS runtime by reading the "payload" data (i.e.,
the JSON document described above) from a file and then calls the handle
function with the data. This is similar to an HTTP FaaS runtime where the
runtime receives HTTP requests, unpack the request to get the body and calls
the handle function with the data.

In an actual deployment, both `invoke.py` and `handler.py` resides in the same
container instance.

To test locally, invoke the function with:

```bash
python3 invoke.py ../power_consumption_data.json
```

Both `invoke.py` and `handler.py` run inside the same Python interpreter instance.


*A key takeaway is that the the function code expects a JSON document with a
particular format described above.*
