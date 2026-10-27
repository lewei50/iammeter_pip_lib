"""Asynchronous IAMMETER client using a caller-owned aiohttp session."""

from typing import Any

import aiohttp

from .connection import normalize_connection
from .models import IammeterDataError, parse_meter_data

DEFAULT_TIMEOUT = 8


class IammeterConnectionError(Exception):
    """The meter could not be reached."""


class IammeterAuthError(IammeterConnectionError):
    """The meter rejected authentication."""


class AsyncClient:
    """Read local data without creating or closing the supplied session."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int = 80,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        username: str = "",
        password: str = "",
    ) -> None:
        if password and not username:
            raise ValueError("A username is required with a password")
        self.session = session
        self.address, self.port, self.endpoint = normalize_connection(host, port)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.auth = aiohttp.encode_basic_auth(username, password) if username else None
        self._legacy_auth_required = False

    async def _read(self, auth: str | None) -> Any:
        async with self.session.get(
            self.endpoint,
            headers={"Authorization": auth} if auth else None,
            timeout=self.timeout,
        ) as response:
            response.raise_for_status()
            return await response.json(content_type=None)

    async def async_get_data(self) -> dict[str, Any]:
        """Read anonymously, falling back to legacy credentials on a 401."""
        legacy_auth = aiohttp.encode_basic_auth("admin", "admin")
        auth = self.auth or (legacy_auth if self._legacy_auth_required else None)
        try:
            try:
                payload = await self._read(auth)
            except aiohttp.ClientResponseError as err:
                if err.status != 401 or auth is not None:
                    raise
                payload = await self._read(legacy_auth)
                self._legacy_auth_required = True
        except aiohttp.ClientResponseError as err:
            if err.status in (401, 403):
                raise IammeterAuthError("Meter authentication failed") from err
            raise IammeterConnectionError("Meter returned an HTTP error") from err
        except (TimeoutError, aiohttp.ClientError) as err:
            raise IammeterConnectionError("Unable to read meter") from err
        except ValueError as err:
            raise IammeterDataError("Meter did not return JSON") from err
        return parse_meter_data(payload)
