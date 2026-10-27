# IAMMETER local HTTP client

Asynchronous local HTTP access for the IAMMETER Home Assistant Core upgrade,
with the original synchronous APIs retained for existing users.
Version `0.3.0` is a development candidate until published to PyPI.

```python
import asyncio
import aiohttp
from iammeter import AsyncClient

async def main():
    async with aiohttp.ClientSession() as session:
        client = AsyncClient(session, "meter.local", port=80)
        measurement = await client.async_get_data()
        print(measurement)

asyncio.run(main())
```

Home Assistant supplies its own shared `ClientSession`. The library never
creates or closes that session and has no dependency on Home Assistant.
The original `iammeter.client.Client` and `IamMeter` synchronous APIs remain
available for existing callers, including their constructor signatures, attributes,
requests exceptions and legacy measurement format/model grouping. The deprecated
`iammeter.power_meter` import path is retained as well. New Home Assistant Core
uses only `AsyncClient`; retaining compatibility does not make Core polling synchronous.
The distribution includes requests and voluptuous for those legacy APIs.

The address accepts a hostname or a complete HTTP/HTTPS URL. `/monitorjson`
is appended once when needed. A full URL controls its own scheme and port.
Credentials embedded in URLs and URL fragments are rejected. Supply optional
`username=` and `password=` arguments for custom credentials.

Requests use an explicit timeout (8 seconds by default). Access is anonymous
unless credentials were supplied. A 401 response triggers one attempt with the
legacy admin credentials, and successful legacy authentication is remembered
for the lifetime of the client. Custom credentials are never replaced by that
fallback. Cancellation propagates to the caller.

Catch `IammeterConnectionError` for connection/HTTP failures,
`IammeterAuthError` for rejected authentication, and `IammeterDataError` for
invalid JSON or malformed measurements.

Supported models: WEM3080, WEM3162, WEM3080T, WEM3046T, WEM3050T, WEM3063T,
and WEM2067. Current `method` prefixes identify the specific model; legacy
three-phase responses without a recognized method retain the WEM3080T fallback.
WEM3162 accepts lowercase `data` and preserves available identity metadata.

Readings retain the meter's engineering units and sign: V, A, W, kWh, Hz,
unitless power factor (for example `0.95`), var, and kvarh. No energy integration
or absolute-value conversion is performed by this library.

WEM2067 exposes A/B only; its optional third row is NET, never channel C.
Other three-phase models use A/B/C and an optional fourth NET row. Optional
`EA.Reactive` rows expose reactive power, inductive energy and capacitive energy.
Absent fields remain absent; they are never fabricated as zero. Measurements
must be finite numbers or an explicit null for an unknown reading. Parsing and authentication behavior are informed by
the independently maintained `lewei50/ha_iammeter` HTTP integration.

Validation distinguishes seven-model synthetic coverage from physical-device
acceptance. Physical WEM3162 and WEM3063T were not part of the current local lab.
