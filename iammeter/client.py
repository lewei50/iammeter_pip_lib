# coding: utf-8

IAMMETER_REQUEST_URL = 'http://admin:admin@{}:{}/monitorjson'

from ipaddress import IPv6Address
import re
from urllib.parse import urlsplit, urlunsplit

import requests

DEFAULT_TIMEOUT = 8

def normalize_connection(host, port=80):
    """Resolve a bare meter host or a complete HTTP(S) data endpoint.

    Full URLs determine their own protocol and port. The meter data suffix
    is appended to every URL path unless it is already present.
    """
    value = host.strip()
    if not value or any(character.isspace() or ord(character) < 32 for character in value):
        raise ValueError("Enter a hostname, IP address or HTTP(S) data URL")
    full_url = "://" in value
    if not full_url and value.count(":") >= 2 and not value.startswith("["):
        IPv6Address(value)
        value = "[{}]".format(value)
    address = urlsplit(value if full_url else "//" + value)
    if (
        address.scheme not in ("", "http", "https")
        or address.hostname is None
        or address.username is not None
        or address.password is not None
        or "#" in value
        or "\\" in value
        or (not full_url and (address.path not in ("", "/", "/monitorjson", "/monitorjson/") or "?" in value))
    ):
        raise ValueError("Enter a meter address without embedded credentials or fragments")
    explicit_port = address.port
    selected_port = explicit_port if explicit_port is not None else (
        (443 if address.scheme == "https" else 80) if full_url else int(port)
    )
    if not 1 <= selected_port <= 65535:
        raise ValueError("The HTTP port must be between 1 and 65535")
    hostname = address.hostname
    url_host = "[{}]".format(hostname) if ":" in hostname else hostname
    if full_url:
        netloc = url_host + (":{}".format(explicit_port) if explicit_port is not None else "")
        path = address.path.rstrip("/")
        if not path.endswith("/monitorjson"):
            path += "/monitorjson"
        endpoint = urlunsplit((address.scheme, netloc, path, address.query, ""))
        return endpoint, selected_port, endpoint
    endpoint = "http://{}:{}/monitorjson".format(url_host, selected_port)
    return hostname, selected_port, endpoint


def normalize_address(host, port=80):
    """Return the endpoint's hostname and effective port."""
    _, selected_port, endpoint = normalize_connection(host, port)
    return urlsplit(endpoint).hostname, selected_port


def _parse_multichannel(data):
    """Parse physical channels separately from an optional NET summary."""
    method = data.get("method")
    two_channel = isinstance(method, str) and re.fullmatch(r"5-.+", method) is not None
    model = "WEM2067" if two_channel else "WEM3080T"
    phases = ("A", "B") if two_channel else ("A", "B", "C")
    rows = data["Datas"]
    if not isinstance(rows, list) or len(rows) < len(phases):
        raise ValueError("Missing physical channel rows")
    out = {"Model": model, "sn": data["SN"], "mac": data["mac"]}
    names = ("Voltage", "Current", "Power", "ImportEnergy", "ExportGrid", "Frequency", "PF")
    for phase, row in zip(phases, rows):
        if not isinstance(row, list) or len(row) < len(names):
            raise ValueError("Invalid physical channel row")
        out.update(("{}_{}".format(name, phase), value) for name, value in zip(names, row))
    if len(rows) > len(phases):
        net = rows[len(phases)]
        if not isinstance(net, list) or len(net) < len(names):
            raise ValueError("Invalid NET row")
        out.update(
            ("{}_Net".format(name), net[index])
            for index, name in enumerate(names) if name != "Current"
        )
    return out


class IamMeter:
    """Base wrapper around iammeter HTTP API"""
    def __init__(self, host, port = 80, sn = "", *, timeout=DEFAULT_TIMEOUT):
        self.client = Client(host, port, timeout=timeout)
        self.host = self.client.ip
        self.port = self.client.port
        self.serial_number = sn
        self.mac = ""
        self.measurement = self.client.get_data()
        self.model = self.measurement["Model"]


class Client(object):
    def __init__(self, ip, port = 80, *, timeout=DEFAULT_TIMEOUT):
        self._full_url = "://" in ip.strip()
        self.address, self.port, self.endpoint = normalize_connection(ip, port)
        self.ip = urlsplit(self.endpoint).hostname
        self.url = IAMMETER_REQUEST_URL
        self.timeout = timeout
        self._legacy_auth_required = False

    def get_data(self):
        if self._full_url:
            auth = ("admin", "admin") if self._legacy_auth_required else None
            r = requests.get(self.endpoint, timeout=self.timeout, auth=auth)
            if r.status_code == 401 and not self._legacy_auth_required:
                r = requests.get(self.endpoint, timeout=self.timeout, auth=("admin", "admin"))
                if r.ok:
                    self._legacy_auth_required = True
        else:
            host = "[{}]".format(self.ip) if ":" in self.ip else self.ip
            r = requests.get(self.url.format(host, self.port), timeout=self.timeout)
        r.raise_for_status()
        return self.parse_data(r.json())

    def parse_data(self, data):
        #WEM3162
        if 'data' in data:
            out = {
                "Model":"WEM3162",
                "Voltage":data["Data"][0],
                "Current":data["Data"][1],
                "Power":data["Data"][2],
                "ImportEnergy":data["Data"][3],
                "ExportGrid":data["Data"][4]
            }
        #WEM3080
        if 'Data' in data:
            out = {
                "Model":"WEM3080",
                "sn":data["SN"],
                "mac":data["mac"],
                "Voltage":data["Data"][0],
                "Current":data["Data"][1],
                "Power":data["Data"][2],
                "ImportEnergy":data["Data"][3],
                "ExportGrid":data["Data"][4]
            }
        # Multi-channel meters share measurement keys, with model-specific row counts.
        if 'Datas' in data:
            out = _parse_multichannel(data)
        return out
