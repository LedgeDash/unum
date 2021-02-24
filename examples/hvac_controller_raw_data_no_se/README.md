The handle function expects a JSON document with an `average` field containing
the average power consumption per minute.

`hvac_controller` returns a JSON document containing the command for the
actuator. The output looks like

```json
{
	"timestamp": "2021-02-20T10:30:00.000",
	"reduce_power": true
}
```

Optionally, we can write `hvac_controller` such that it causes side effects by
calling a REST API of an actuator.
