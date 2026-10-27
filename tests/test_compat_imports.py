"""Public import paths for existing callers remain available."""

from iammeter import AsyncClient, Client, IamMeter
from iammeter.client import Client as LegacyClient
from iammeter.client import IamMeter as LegacyIamMeter
from iammeter.power_meter import WEM3080, WEM3080T, IamMeterError, discover


def test_public_import_paths():
    assert Client is LegacyClient
    assert IamMeter is LegacyIamMeter
    assert AsyncClient is not LegacyClient
    assert issubclass(IamMeterError, Exception)
    assert callable(discover)
    assert callable(WEM3080.map_response)
    assert callable(WEM3080T.map_response)
