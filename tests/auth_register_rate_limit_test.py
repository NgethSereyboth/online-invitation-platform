"""Registration throttling: public traffic stays at 10/600 s; local harnesses get headroom.

The frozen canvas visual gate creates two identities per width/mode pair — 12 in a full
run — from loopback, so a 10-per-600 s ceiling makes the gate impossible to finish in one
command. The loopback allowance is tied to the same local bootstrap mode that already
grants loopback administrator authority, and it must vanish when that mode is off (which
is what a production deployment does).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from v14_test_utils import app_server


def _register(base: str, index: int) -> int:
    payload = json.dumps({
        "email": f"throttle-{index}@example.com",
        "password": "Throttle-test-password-123!",
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/api/auth/register",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def test_loopback_harness_can_create_twelve_identities() -> None:
    """One uninterrupted gate run needs 12 registrations from loopback."""
    with app_server({"EINVITE_ALLOW_NO_SCANNER": "1"}) as (_process, base, _data):
        statuses = [_register(base, index) for index in range(12)]

    assert statuses == [201] * 12, statuses


def test_public_limit_is_unchanged_without_local_bootstrap() -> None:
    """With the local bootstrap off, the tenth registration still succeeds and the next 429s."""
    with app_server({
        "EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP": "0",
        "EINVITE_ALLOW_NO_SCANNER": "1",
    }) as (_process, base, _data):
        statuses = [_register(base, index) for index in range(11)]

    assert statuses[:10] == [201] * 10, statuses
    assert statuses[10] == 429, statuses
