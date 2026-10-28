#!/usr/bin/env python3
"""LT-7.2 step 5 — the API-keys card on account.html, end to end (ROADMAP §4.5).

The HTTP test (``security_api_keys_test.py``) proves the server side. This one
proves the account page can actually drive it, with nothing stubbed:

1. The card starts empty and the create button opens the real dialog with the
   name field focused.
2. Submitting creates the key through ``POST /api/account/api-keys`` and the
   show-once dialog carries an ``einv_`` key.
3. After it closes, the list shows the row — and the full key is **not** in the
   list DOM (only prefix + last four).
4. The key the UI minted works over plain HTTP for an allowed route (RSVP read).
5. The row's Revoke button (through the confirm dialog) revokes it, the row
   flips to Revoked/disabled, and the same key is refused with 401 afterwards.

Prints ``LT_7_2_API_KEYS_UI_PASSED`` on success.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

PASSWORD = "Test1234!Pass"


def _post(base, path, body, token=None, api_key=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if api_key:
        headers["X-API-Key"] = api_key
    request = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        payload = error.read() or b"{}"
        try:
            return error.code, json.loads(payload)
        except json.JSONDecodeError:
            return error.code, {"_raw": payload.decode("utf-8", "replace")}


def _get(base, path, api_key=None, token=None):
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, {}


def test_account_page_creates_uses_and_revokes_an_api_key():  # noqa: C901 - linear scenario
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"playwright unavailable: {exc}")
    from v14_test_utils import app_server

    email = f"lt72-keys-ui-{int(time.time())}@einvite.test"
    extra_env = {"EINVITE_ALLOW_NO_SCANNER": "1"}

    with app_server(extra_env=extra_env) as (_process, base, _data):
        # An invitation to exercise the key against, created over HTTP as the
        # same account the browser will sign into.
        status, auth = _post(base, "/api/auth/register", {"email": email, "password": PASSWORD})
        assert status in (200, 201) and auth.get("token"), (status, auth)
        document = {"schemaVersion": 14, "eventType": "Wedding", "fields": {"names": "Keys UI"},
                    "objects": {}, "designPages": [], "settings": {"rsvpEnabled": True}}
        status, created = _post(base, "/api/invitations", {"slug": "keys-ui-rsvp", "document": document},
                                token=auth["token"])
        assert status in (200, 201), (status, created)
        invitation_id = created["id"]

        with sync_playwright() as pw:
            from browser_runtime import launch_chromium

            try:
                browser = launch_chromium(pw)
            except Exception as exc:  # pragma: no cover - environment dependent
                pytest.skip(f"chromium unavailable: {exc}")
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.set_default_timeout(15000)
            page_errors: list[str] = []
            console_errors: list[str] = []
            page.on("pageerror", lambda e: page_errors.append(str(e)))
            page.on("console", lambda m: console_errors.append(m.text)
                    if m.type == "error" and "favicon" not in m.text.lower() else None)

            # Native confirms are accepted (revoke asks one); nothing else is.
            dialogs: list[dict] = []

            def on_dialog(dialog):
                dialogs.append({"type": dialog.type, "message": dialog.message})
                dialog.accept()

            page.on("dialog", on_dialog)

            # Sign in through the real dashboard so the context holds the session.
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded")
            page.wait_for_selector("#loginView,#dashboardView")
            if page.locator("#loginView:not([hidden])").count():
                page.locator("#email").fill(email)
                page.locator("#password").fill(PASSWORD)
                page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])")

            page.goto(base + "/account.html", wait_until="domcontentloaded")
            card = page.locator("#v13ApiKeys")
            card.wait_for(state="visible")
            page.wait_for_function("() => document.querySelector('#v13ApiKeys')?.textContent.includes('No API keys yet')")

            # 1) The create dialog opens with the name field focused.
            page.locator("#v13CreateApiKey").click()
            dialog = page.locator("dialog.ei-dialog").last
            dialog.wait_for(state="visible")
            # inner_text() is rendered text: the card heading is uppercased by CSS.
            assert "create an api key" in dialog.inner_text().lower(), dialog.inner_text()
            assert page.evaluate("() => document.activeElement && document.activeElement.id") == "v13ApiKeyName"

            page.locator("#v13ApiKeyName").fill("UI automation key")
            page.locator("#v13ApiKeyScope").select_option("rsvps:read")
            with page.expect_response(lambda r: r.url.endswith("/api/account/api-keys") and r.request.method == "POST") as created_response:
                dialog.locator("[data-confirm]").click()
            assert created_response.value.status == 201, created_response.value.status

            # 2) The show-once dialog carries the real key.
            reveal = page.locator("dialog.ei-dialog").last
            reveal.wait_for(state="visible")
            assert "copy your api key now" in reveal.inner_text().lower(), reveal.inner_text()
            api_key = page.locator("#v13NewApiKey").input_value()
            assert api_key.startswith("einv_") and len(api_key) >= 40, api_key
            reveal.locator("[data-copy]").click()
            # Clipboard rights differ by environment: the copy handler settles on
            # either "copied" or the manual-copy fallback. Either proves it ran.
            page.wait_for_function(
                "() => /copied|copy failed/i.test(document.querySelector('#v13ApiKeysStatus')?.textContent || '')",
                timeout=5000)
            status_text = page.locator("#v13ApiKeysStatus").inner_text()
            assert status_text, status_text
            reveal.locator("[data-confirm]").click()
            reveal.wait_for(state="detached")

            # 3) The list shows the row without ever reprinting the secret.
            row = page.locator("#v13ApiKeys .v13-row", has_text="UI automation key").first
            row.wait_for(state="visible")
            row_text = row.inner_text()
            assert api_key not in row_text, row_text
            assert api_key[-4:] in row_text and "rsvps:read" in row_text, row_text

            # 4) The key the UI minted works for its scope over plain HTTP.
            status, rsvps = _get(base, f"/api/invitations/{invitation_id}/rsvps", api_key=api_key)
            assert status == 200 and isinstance(rsvps, list), (status, rsvps)

            # 5) Revoke from the row, through the confirm dialog.
            row.locator("button").click()
            page.wait_for_function(
                "() => document.querySelector('#v13ApiKeys .v13-row button')?.textContent === 'Revoked'")
            assert dialogs and dialogs[-1]["type"] == "confirm", dialogs
            assert "Revoke this API key?" in dialogs[-1]["message"], dialogs[-1]
            assert page.locator("#v13ApiKeys .v13-row button").first.is_disabled()
            status, after = _get(base, f"/api/invitations/{invitation_id}/rsvps", api_key=api_key)
            assert status == 401, (status, after)

            assert not page_errors, page_errors
            assert not console_errors, console_errors
            print("[OK] account page created, listed (masked), used and revoked an API key", flush=True)
            browser.close()
        print("LT_7_2_API_KEYS_UI_PASSED", flush=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "-q"]))
