## IamMeter

Python Client for IamMeter device.

See https://www.iammeter.com/docs

##### Create a new connection by supplying IamMeter host and port(default:80)

`import client`

`s= client.IamMeter("host",port)`

`print(s.client.get_data())`

##### ChangeLog

0.2.1 power_meter.py deprecated,using client.py instead.
Change return format,more readable.

0.1.7 first commit，return sensor‘s map


### 0.2.2 (unreleased)

HTTP reads now use an eight-second timeout and raise `requests.HTTPError` for
unsuccessful HTTP status codes before parsing the response. Connection errors,
timeouts and invalid JSON are propagated to the caller. Existing positional
arguments and measurement keys are unchanged. The `requests` runtime dependency
is now declared in the package metadata.

```python
from iammeter.client import IamMeter

meter = IamMeter("192.0.2.1", 80, timeout=5)
print(meter.measurement)  # Initial read performed by the constructor
print(meter.client.get_data())  # Subsequent read
```

`timeout` is keyword-only and also available on `Client`. It accepts the same
values as `requests.get(timeout=...)` (a number or connect/read timeout tuple).
The timeout bounds individual connection/read waits; it is not an overall
wall-clock deadline for the complete response.

Run tests with `python3 -m pytest tests`.

Meter addresses accept either a hostname/IP with a separate HTTP port, or a
complete HTTP/HTTPS JSON endpoint:

```python
meter = IamMeter("meter.local", 8080)
meter = IamMeter("https://simulator.iammeter.com/WEM3080/monitorjson")
```

A full URL keeps its protocol, port, path prefix, and query parameters. Its port takes
precedence over the separate argument; without an explicit port, HTTP uses 80
and HTTPS uses 443. The path is completed with `/monitorjson` unless it already
ends with that suffix. For example, `http://meter.local/WEM3050T/` becomes
`http://meter.local/WEM3050T/monitorjson`. Trailing slashes are removed before
checking the suffix, so it is never appended twice. Embedded credentials and
fragments are rejected. HTTPS
certificate verification remains enabled through the default Requests behavior.

Bare host/IP connections retain the existing legacy authentication. Full URLs
are requested anonymously first, with legacy `admin/admin` retried only after an
HTTP 401 response. Custom username/password settings are not added in this release.


### WEM2067 support (0.2.2 candidate)

Responses with a `method` matching `5-*` are identified as `WEM2067`. The first
two `Datas` rows are channels A and B. An optional third row is the NET summary,
not a C channel. Existing measurement keys (`Power_A`, `ImportEnergy_B`,
`Power_Net`, and others) are retained. Other multi-channel responses keep the
existing `WEM3080T` family label and three physical channels; their optional NET
summary remains the fourth row. Missing NET rows are valid and produce no NET
keys. Malformed physical or present NET rows raise `ValueError`.

This adds active measurements and optional NET readings; it does not add
`EA.Reactive` sensors.
