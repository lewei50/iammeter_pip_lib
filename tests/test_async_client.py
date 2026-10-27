"""Real asynchronous HTTP, authentication, error and model regression tests."""

import asyncio

import aiohttp
import pytest
from aiohttp import web

from iammeter import (
    AsyncClient,
    IammeterAuthError,
    IammeterConnectionError,
    IammeterDataError,
    parse_meter_data,
)

SINGLE = {
    "SN": "test-meter",
    "mac": "00:00:00:00:00:01",
    "version": "test-version",
    "Data": [230, 2, -460, 100, 10],
}
ROW = [230, 2, -460, 100, 10, 50, 0.95]


@pytest.fixture
async def meter_server():
    state = {
        "payload": SINGLE,
        "status": 200,
        "authentication": False,
        "calls": [],
        "text": None,
        "delay": 0,
    }

    async def handler(request):
        state["calls"].append(request.headers.get("Authorization"))
        await asyncio.sleep(state["delay"])
        if state["authentication"] and request.headers.get(
            "Authorization"
        ) != aiohttp.encode_basic_auth("admin", "admin"):
            return web.Response(status=401)
        if state["text"] is not None:
            return web.Response(text=state["text"], status=state["status"])
        return web.json_response(state["payload"], status=state["status"])

    app = web.Application()
    app.router.add_get("/monitorjson", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        yield state, f"http://127.0.0.1:{port}/"
    finally:
        await runner.cleanup()


async def test_anonymous_session_ownership(meter_server):
    state, url = meter_server
    async with aiohttp.ClientSession() as session:
        data = await AsyncClient(session, url).async_get_data()
        assert data["Power"] == -460
        assert data["ImportEnergy"] == 100
        assert data["ExportGrid"] == 10
        assert data["version"] == "test-version"
        assert state["calls"] == [None]
        assert not session.closed


async def test_legacy_authentication_is_cached(meter_server):
    state, url = meter_server
    state["authentication"] = True
    async with aiohttp.ClientSession() as session:
        client = AsyncClient(session, url)
        await client.async_get_data()
        await client.async_get_data()
    auth = aiohttp.encode_basic_auth("admin", "admin")
    assert state["calls"] == [None, auth, auth]


async def test_custom_credentials(meter_server):
    state, url = meter_server
    async with aiohttp.ClientSession() as session:
        await AsyncClient(
            session, url, username="custom", password="secret"
        ).async_get_data()
    assert state["calls"] == [aiohttp.encode_basic_auth("custom", "secret")]


@pytest.mark.parametrize("status", [401, 403])
async def test_rejected_authentication(meter_server, status):
    state, url = meter_server
    state["status"] = status
    async with aiohttp.ClientSession() as session:
        with pytest.raises(IammeterAuthError):
            await AsyncClient(session, url).async_get_data()


async def test_http_failure(meter_server):
    state, url = meter_server
    state["status"] = 500
    async with aiohttp.ClientSession() as session:
        with pytest.raises(IammeterConnectionError):
            await AsyncClient(session, url).async_get_data()
    assert state["calls"] == [None]


async def test_timeout(meter_server):
    state, url = meter_server
    state["delay"] = 0.05
    async with aiohttp.ClientSession() as session:
        with pytest.raises(IammeterConnectionError):
            await AsyncClient(session, url, timeout=0.001).async_get_data()


async def test_invalid_json(meter_server):
    state, url = meter_server
    state["text"] = "not JSON"
    async with aiohttp.ClientSession() as session:
        with pytest.raises(IammeterDataError):
            await AsyncClient(session, url).async_get_data()


async def test_cancellation_propagates(meter_server):
    state, url = meter_server
    state["delay"] = 0.05
    async with aiohttp.ClientSession() as session:
        task = asyncio.create_task(AsyncClient(session, url).async_get_data())
        await asyncio.sleep(0.005)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not session.closed


@pytest.mark.parametrize(
    ("method", "model"),
    [
        ("2-x", "WEM3080T"),
        ("3-x", "WEM3046T"),
        ("4-x", "WEM3050T"),
        ("5-x", "WEM2067"),
        ("6-x", "WEM3063T"),
    ],
)
def test_model_identification(method, model):
    data = parse_meter_data(
        {
            "method": method,
            "Datas": [ROW] * (2 if model == "WEM2067" else 3),
            "SN": "test-meter",
        }
    )
    assert data["Model"] == model
    assert data["PF_A"] == 0.95
    assert data["Power_A"] == -460


def test_legacy_single_phase():
    data = parse_meter_data({"data": ROW[:5], "mac": "00:00:00:00:00:01"})
    assert data["Model"] == "WEM3162"
    assert data["Power"] == -460


def test_unknown_measurement_keeps_other_readings():
    """An explicit null remains unknown without dropping the other readings."""
    data = parse_meter_data({"Data": [230, None, -460, 100, 10]})
    assert data["Current"] is None
    assert data["Power"] == -460


@pytest.mark.parametrize("method", ["2-x", "3-x", "4-x", "5-x", "6-x"])
def test_reactive_fields(method):
    data = parse_meter_data(
        {
            "method": method,
            "Datas": [ROW] * (2 if method == "5-x" else 3),
            "EA": {"Reactive": [[-10, 20, 30]] * 3},
        }
    )
    assert data["ReactivePower_A"] == -10
    assert data["InductiveReactiveEnergy_A"] == 20
    assert data["CapacitiveReactiveEnergy_A"] == 30


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"Data": []},
        {"Data": [True, 2, 3, 4, 5]},
        {"Data": [float("nan"), 2, 3, 4, 5]},
        {"Data": [10**500, 2, 3, 4, 5]},
        {"Data": ["230", 2, 3, 4, 5]},
        {"Datas": []},
        {"Data": ROW[:5], "EA": {"Reactive": None}},
        {"Data": ROW[:5], "EA": {"Reactive": [[1]]}},
    ],
)
def test_invalid_payload(payload):
    with pytest.raises(IammeterDataError):
        parse_meter_data(payload)


async def test_password_requires_username():
    async with aiohttp.ClientSession() as session:
        with pytest.raises(ValueError, match="username"):
            AsyncClient(session, "meter.local", password="secret")
