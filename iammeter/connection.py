"""Normalize local IAMMETER connection addresses."""

from ipaddress import IPv6Address
from urllib.parse import urlsplit, urlunsplit


def normalize_connection(host: str, port: int = 80) -> tuple[str, int, str]:
    """Resolve a bare meter host or a complete HTTP(S) data endpoint.

    Full URLs determine their own protocol and port. The meter data suffix
    is appended to every URL path unless it is already present.
    """
    value = host.strip()
    if not value or any(
        character.isspace() or ord(character) < 32 for character in value
    ):
        raise ValueError("Enter a hostname, IP address or HTTP(S) data URL")
    full_url = "://" in value
    if not full_url and value.count(":") >= 2 and not value.startswith("["):
        IPv6Address(value)
        value = f"[{value}]"
    address = urlsplit(value if full_url else "//" + value)
    if (
        address.scheme not in ("", "http", "https")
        or address.hostname is None
        or address.username is not None
        or address.password is not None
        or "#" in value
        or "\\" in value
        or (
            not full_url
            and (
                address.path not in ("", "/", "/monitorjson", "/monitorjson/")
                or "?" in value
            )
        )
    ):
        raise ValueError(
            "Enter a meter address without embedded credentials or fragments"
        )
    explicit_port = address.port
    selected_port = (
        explicit_port
        if explicit_port is not None
        else ((443 if address.scheme == "https" else 80) if full_url else int(port))
    )
    if not 1 <= selected_port <= 65535:
        raise ValueError("The HTTP port must be between 1 and 65535")
    hostname = address.hostname
    url_host = f"[{hostname}]" if ":" in hostname else hostname
    if full_url:
        netloc = url_host + (f":{explicit_port}" if explicit_port is not None else "")
        path = address.path.rstrip("/")
        if not path.endswith("/monitorjson"):
            path += "/monitorjson"
        endpoint = urlunsplit((address.scheme, netloc, path, address.query, ""))
        return endpoint, selected_port, endpoint
    endpoint = f"http://{url_host}:{selected_port}/monitorjson"
    return hostname, selected_port, endpoint
