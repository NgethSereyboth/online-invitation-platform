"""Public health endpoints must not disclose internal product versions."""
from __future__ import annotations

import json
import urllib.request

import pytest
from v14_test_utils import app_server


@pytest.mark.parametrize("disclose_details", ["0", "1"])
def test_live_health_response_never_contains_version(disclose_details: str) -> None:
    """The public live probe stays minimal under either diagnostics setting."""
    with app_server({
        "EINVITE_DISCLOSE_HEALTH_DETAILS": disclose_details,
        "EINVITE_ALLOW_NO_SCANNER": "1",
    }) as (_process, base, _data):
        with urllib.request.urlopen(f"{base}/api/health/live", timeout=5) as response:
            assert response.status == 200
            payload = json.loads(response.read())

    assert payload == {"ok": True, "status": "live"}
    assert "version" not in payload
