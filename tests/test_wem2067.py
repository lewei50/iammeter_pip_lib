"""Model-aware channel parsing and compatibility with existing measurements."""

import pytest

from iammeter.client import Client

A = [230, 1, 230, 11, 1, 50, 0.91]
B = [240, 2, 480, 22, 2, 49, 0.92]
C = [250, 3, 750, 33, 3, 48, 0.93]
NET = [235, 0, 710, 44, 4, 49.5, 0.94]


def payload(rows, method="5-test"):
    return {"method": method, "SN": "test-meter-2067", "mac": "00:00:00:00:00:01", "Datas": rows}


def test_dual_channel():
    data = Client("127.0.0.1").parse_data(payload([A, B]))
    assert data["Model"] == "WEM2067"
    assert data["Power_A"] == 230
    assert data["Power_B"] == 480
    assert data["PF_B"] == 0.92
    assert not any(key.endswith(("_C", "_Net")) for key in data)


def test_dual_channel_net():
    data = Client("127.0.0.1").parse_data(payload([A, B, NET]))
    assert data["Power_Net"] == 710
    assert data["ImportEnergy_Net"] == 44
    assert data["PF_Net"] == 0.94
    assert "Current_Net" not in data
    assert not any(key.endswith("_C") for key in data)


@pytest.mark.parametrize("method", [None, "2-test", "4-test", "55-test"])
def test_legacy_three_phase(method):
    data = Client("127.0.0.1").parse_data(payload([A, B, C, NET], method))
    assert data["Model"] == "WEM3080T"
    assert data["Power_C"] == 750
    assert data["Power_Net"] == 710
    assert data["PF_Net"] == 0.94


def test_three_phase_without_net():
    data = Client("127.0.0.1").parse_data(payload([A, B, C], "4-test"))
    assert data["Model"] == "WEM3080T"
    assert data["Power_C"] == 750
    assert "Power_Net" not in data


@pytest.mark.parametrize("rows", [[], [A], [A, [240]], [A, None], [A, B, [235]], "invalid"])
def test_invalid_dual_channel_payload(rows):
    with pytest.raises(ValueError):
        Client("127.0.0.1").parse_data(payload(rows))


def test_two_rows_without_model_are_not_assumed_dual_channel():
    with pytest.raises(ValueError):
        Client("127.0.0.1").parse_data(payload([A, B], None))
