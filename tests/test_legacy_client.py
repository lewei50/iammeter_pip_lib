"""Regression tests for bounded HTTP requests without changing the public API."""

from unittest.mock import Mock, patch

import pytest
import requests

from iammeter.client import DEFAULT_TIMEOUT, Client, IamMeter

SINGLE_PHASE = {
    "SN": "test-meter",
    "mac": "00:00:00:00:00:01",
    "Data": [230.0, 2.0, 460.0, 100.0, 10.0],
}


@pytest.mark.parametrize("timeout", [DEFAULT_TIMEOUT, 1.5, (2, 4)])
def test_http_timeout_and_measurements(timeout):
    response = Mock()
    response.json.return_value = SINGLE_PHASE
    with patch("iammeter.client.requests.get", return_value=response) as get:
        client = Client("192.0.2.1", 8080, timeout=timeout)
        data = client.get_data()
    get.assert_called_once_with(
        "http://admin:admin@192.0.2.1:8080/monitorjson", timeout=timeout
    )
    response.raise_for_status.assert_called_once_with()
    assert data["sn"] == "test-meter"
    assert data["Power"] == 460.0


def test_legacy_constructor():
    response = Mock()
    response.json.return_value = SINGLE_PHASE
    with patch("iammeter.client.requests.get", return_value=response) as get:
        meter = IamMeter("192.0.2.1", 80, "Old name")
    assert meter.model == "WEM3080"
    assert meter.measurement["sn"] == "test-meter"
    assert meter.serial_number == "Old name"
    assert get.call_args.kwargs["timeout"] == DEFAULT_TIMEOUT


def test_constructor_custom_timeout():
    response = Mock()
    response.json.return_value = SINGLE_PHASE
    with patch("iammeter.client.requests.get", return_value=response) as get:
        IamMeter("192.0.2.1", timeout=3)
    assert get.call_args.kwargs["timeout"] == 3


@pytest.mark.parametrize("error", [requests.Timeout, requests.ConnectionError])
def test_connection_errors(error):
    with patch("iammeter.client.requests.get", side_effect=error):
        with pytest.raises(error):
            Client("192.0.2.1").get_data()


def test_http_error_before_parsing():
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("HTTP failure")
    with patch("iammeter.client.requests.get", return_value=response):
        with pytest.raises(requests.HTTPError):
            Client("192.0.2.1").get_data()
    response.json.assert_not_called()


def test_invalid_json():
    response = Mock()
    response.json.side_effect = ValueError("Invalid JSON")
    with patch("iammeter.client.requests.get", return_value=response):
        with pytest.raises(ValueError):
            Client("192.0.2.1").get_data()


def test_three_phase_measurements():
    response = Mock()
    response.json.return_value = {
        "SN": "test-three-phase",
        "mac": "00:00:00:00:00:02",
        "Datas": [[230, 2, 460, 100, 10, 50, 0.95]] * 4,
    }
    with patch("iammeter.client.requests.get", return_value=response):
        data = Client("192.0.2.1").get_data()
    assert data["Model"] == "WEM3080T"
    assert data["PF_A"] == 0.95
    assert data["Power_Net"] == 460


@pytest.mark.parametrize(
    ("address", "port", "expected_host", "expected_port"),
    [
        ("192.0.2.1", 80, "192.0.2.1", 80),
        ("meter.local", 8080, "meter.local", 8080),
        ("http://192.0.2.1", 80, "192.0.2.1", 80),
        (" http://meter.local/ ", 8080, "meter.local", 80),
        ("http://meter.local:8080", 80, "meter.local", 8080),
        ("meter.local:8080", 8888, "meter.local", 8080),
        ("http://meter.local:8080/monitorjson", 8888, "meter.local", 8080),
        ("http://meter.local/monitorjson/", 80, "meter.local", 80),
        ("HTTP://METER.LOCAL/", 80, "meter.local", 80),
        ("http://[2001:db8::1]:8080/", 80, "2001:db8::1", 8080),
    ],
)
def test_address_normalization(address, port, expected_host, expected_port):
    from iammeter.client import normalize_address

    assert normalize_address(address, port) == (expected_host, expected_port)


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
    from iammeter.client import normalize_address

    with pytest.raises(ValueError):
        normalize_address(address)


@pytest.mark.parametrize(
    ("address", "expected_url"),
    [
        ("http://meter.local:8080/monitorjson", "http://meter.local:8080/monitorjson"),
        ("http://[2001:db8::1]:8080/", "http://[2001:db8::1]:8080/monitorjson"),
    ],
)
def test_request_with_url_address(address, expected_url):
    response = Mock()
    response.json.return_value = SINGLE_PHASE
    with patch("iammeter.client.requests.get", return_value=response) as get:
        meter = IamMeter(address)
    get.assert_called_once_with(expected_url, timeout=DEFAULT_TIMEOUT, auth=None)
    assert meter.port == 8080
    assert meter.measurement["Power"] == 460.0


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
    from iammeter.client import normalize_connection

    normalized, resolved_port, actual_endpoint = normalize_connection(address, port)
    assert actual_endpoint == endpoint
    assert resolved_port == expected_port
    client = Client(address, port)
    assert client.endpoint == endpoint
    assert client.port == expected_port


def test_full_url_legacy_auth_fallback():
    unauthorized = Mock(status_code=401)
    response = Mock(status_code=200, ok=True)
    response.json.return_value = SINGLE_PHASE
    url = "https://meter.example/custom/monitorjson"
    with patch(
        "iammeter.client.requests.get", side_effect=[unauthorized, response, response]
    ) as get:
        meter = IamMeter(url)
        assert meter.client.get_data()["sn"] == "test-meter"
    assert get.call_args_list[0].kwargs["auth"] is None
    assert get.call_args_list[1].kwargs["auth"] == ("admin", "admin")
    assert get.call_args_list[2].kwargs["auth"] == ("admin", "admin")
    unauthorized.json.assert_not_called()


def test_full_url_http_error():
    response = Mock(status_code=403)
    response.raise_for_status.side_effect = requests.HTTPError()
    with patch("iammeter.client.requests.get", return_value=response) as get:
        with pytest.raises(requests.HTTPError):
            Client("https://meter.example/api/data").get_data()
    get.assert_called_once_with(
        "https://meter.example/api/data/monitorjson", timeout=DEFAULT_TIMEOUT, auth=None
    )
    response.json.assert_not_called()


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
    from iammeter.client import normalize_connection

    normalized, port, endpoint = normalize_connection(address)
    assert endpoint == expected
    assert normalized == expected
    assert normalize_connection(normalized, port) == (normalized, port, endpoint)
