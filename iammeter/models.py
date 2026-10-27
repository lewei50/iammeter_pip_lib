"""Parse IAMMETER local HTTP responses without depending on Home Assistant."""

import math
import re
import sys
from typing import Any

MODELS = {
    1: "WEM3080",
    2: "WEM3080T",
    3: "WEM3046T",
    4: "WEM3050T",
    5: "WEM2067",
    6: "WEM3063T",
}
SUPPORTED_MODELS = frozenset((*MODELS.values(), "WEM3162"))
MEASUREMENTS = (
    "Voltage",
    "Current",
    "Power",
    "ImportEnergy",
    "ExportGrid",
    "Frequency",
    "PF",
)


class IammeterDataError(ValueError):
    """The device did not return a valid meter response."""


def _row(value: Any, length: int) -> list[int | float | None]:
    if not isinstance(value, list) or len(value) < length:
        raise IammeterDataError("Missing measurement values")
    if any(
        v is not None
        and (
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or abs(v) > sys.float_info.max
            or not math.isfinite(v)
        )
        for v in value[:length]
    ):
        raise IammeterDataError("Measurements must be finite numbers")
    return value


def parse_meter_data(payload: Any) -> dict[str, Any]:
    """Return physical measurements, optional NET/reactive fields and identity."""
    if not isinstance(payload, dict):
        raise IammeterDataError("Expected a JSON object")
    data: dict[str, Any] = {}
    if "Data" in payload or "data" in payload:
        key = "Data" if "Data" in payload else "data"
        model = "WEM3080" if key == "Data" else "WEM3162"
        phases: tuple[str, ...] = ("A",)
        row = _row(payload[key], 5)
        data.update(zip(MEASUREMENTS[:5], row[:5]))
    elif "Datas" in payload:
        method = payload.get("method")
        match = re.fullmatch(r"([1-6])-.+", method) if isinstance(method, str) else None
        model = MODELS[int(match[1])] if match else "WEM3080T"
        phases = ("A", "B") if model == "WEM2067" else ("A", "B", "C")
        rows = payload["Datas"]
        if not isinstance(rows, list) or len(rows) < len(phases):
            raise IammeterDataError("Missing physical channels")
        for phase, values in zip(phases, rows):
            row = _row(values, 7)
            data.update(
                (f"{key}_{phase}", value) for key, value in zip(MEASUREMENTS, row)
            )
        if len(rows) > len(phases):
            row = _row(rows[len(phases)], 7)
            data.update(
                (f"{key}_Net", row[index])
                for index, key in enumerate(MEASUREMENTS)
                if key != "Current"
            )
    else:
        raise IammeterDataError("No meter measurements in response")
    extra = payload.get("EA")
    if isinstance(extra, dict) and "Reactive" in extra:
        rows = extra["Reactive"]
        if not isinstance(rows, list):
            raise IammeterDataError("Invalid reactive measurements")
        for phase, values in zip(phases, rows):
            row = _row(values, 3)
            data.update(
                (f"{key}_{phase}", value)
                for key, value in zip(
                    (
                        "ReactivePower",
                        "InductiveReactiveEnergy",
                        "CapacitiveReactiveEnergy",
                    ),
                    row,
                )
            )
    data["Model"] = model
    for target, keys in (
        ("sn", ("SN", "sn")),
        ("mac", ("mac", "MAC")),
        ("version", ("version",)),
    ):
        for key in keys:
            if key in payload:
                data[target] = payload[key]
                break
    return data
