"""Address normalization for the asynchronous public API."""

import pytest

from iammeter import AsyncClient


@pytest.mark.parametrize(
    "address",
    [
        "",
        " ",
        "http://",
        "ftp://meter.local",
        "http://user:password@meter.local",
        "http://meter.local/#section",
        "http://meter.local:0",
        "http://meter.local:65536",
        "http://meter.local:bad",
        "http://[bad",
        "meter local",
        "meter.local/?",
        "meter.local/#",
    ],
)
def test_invalid_address(address):
    from iammeter.connection import normalize_connection

    with pytest.raises(ValueError):
        normalize_connection(address)


@pytest.mark.parametrize(
    ("address", "port", "expected_port", "endpoint"),
    [
        (
            "https://meter.example/WEM3080/monitorjson",
            80,
            443,
            "https://meter.example/WEM3080/monitorjson",
        ),
        (
            "http://meter.example/WEM3080/monitorjson",
            9999,
            80,
            "http://meter.example/WEM3080/monitorjson",
        ),
        (
            "https://meter.example:8443/api/read?channel=A",
            80,
            8443,
            "https://meter.example:8443/api/read/monitorjson?channel=A",
        ),
        ("https://meter.example/", 80, 443, "https://meter.example/monitorjson"),
        ("meter.example", 8080, 8080, "http://meter.example:8080/monitorjson"),
    ],
)
def test_full_endpoint(address, port, expected_port, endpoint):
    from iammeter.connection import normalize_connection

    _normalized, resolved_port, actual_endpoint = normalize_connection(address, port)
    assert actual_endpoint == endpoint
    assert resolved_port == expected_port
    client = AsyncClient(None, address, port)
    assert client.endpoint == endpoint
    assert client.port == expected_port


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        (
            "http://simulator.iammeter.com/WEM3050T/",
            "http://simulator.iammeter.com/WEM3050T/monitorjson",
        ),
        (
            "https://meter.example/WEM3050T",
            "https://meter.example/WEM3050T/monitorjson",
        ),
        (
            "https://meter.example/WEM3050T/?scenario=solar",
            "https://meter.example/WEM3050T/monitorjson?scenario=solar",
        ),
        (
            "https://meter.example/WEM3050T/monitorjson/",
            "https://meter.example/WEM3050T/monitorjson",
        ),
        (
            "https://meter.example/WEM3050T/monitorjson?scenario=solar",
            "https://meter.example/WEM3050T/monitorjson?scenario=solar",
        ),
    ],
)
def test_url_suffix_is_added_once(address, expected):
    from iammeter.connection import normalize_connection

    _normalized, port, endpoint = normalize_connection(address)
    assert endpoint == expected
    assert _normalized == expected
    assert normalize_connection(_normalized, port) == (_normalized, port, endpoint)
