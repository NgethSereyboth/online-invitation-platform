#!/usr/bin/env python3
"""LT-7.2 — the admin step-up prompt, end to end in a real browser (ROADMAP §4.2, §5.9).

The HTTP test (``lt_7_2_admin_stepup_test.py``) proves the gate server-side. This
one proves the admin pages still *work* behind it, which is the other half of the
item — before LT-7.2 no admin page could obtain a grant, so every gated button
would have failed with the raw 403.

Flow, with nothing stubbed:

1. Suspend (a real button in the Users tab) → the server refuses **403**.
2. The prompt opens, the password field is focused, and cancel is not needed —
   the admin types the password and submits.
3. ``POST /api/admin/step-up`` is called with that password and the original
   request is replayed → **200** with ``{"suspended": true}``, and the tab
   re-renders without an error. (The tab cannot *show* the new state: its list
   endpoint ``/api/admin/users`` does not select ``suspended_at`` — a
   pre-existing display gap, recorded in NOTES.md, not something this item
   changes.)
4. The prompt is a real modal (``showModal``): both inputs have programmatic
   labels, Escape closes it **without replaying** the refused request, and focus
   returns to the button that opened it (the success path re-renders the table,
   so there the assertion is that no dialog is left open).
5. The grant is cached in memory only (D-7): the next destructive action (reset
   password) goes straight through — **200**, no second prompt.
6. No step-up token is written to browser storage (D-7): after a reload the
   only grant is the server-side one bound to the session cookie.
7. No stray error alert appears, and the console stays clean.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

ADMIN_EMAIL = "admin@einvite.test"
PASSWORD = "Test1234!Pass"


def _register(base, email, password):
    request = urllib.request.Request(
        f"{base}/api/auth/register",
        data=json.dumps({"email": email, "password": password}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read() or b"{}")


def test_admin_pages_can_complete_the_step_up():  # noqa: C901 - linear scenario
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"playwright unavailable: {exc}")
    from v14_test_utils import app_server

    victim_email = f"lt72-ui-victim-{int(time.time())}@einvite.test"
    extra_env = {
        "EINVITE_ALLOW_NO_SCANNER": "1",
        "EINVITE_ADMIN_EMAIL": ADMIN_EMAIL,
        "EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP": "1",
    }

    with app_server(extra_env=extra_env) as (_process, base, _data):
        # The Users tab needs a second row to act on.
        _register(base, victim_email, PASSWORD)

        with sync_playwright() as pw:
            from browser_runtime import launch_chromium

            try:
                browser = launch_chromium(pw)
            except Exception as exc:  # pragma: no cover - environment dependent
                pytest.skip(f"chromium unavailable: {exc}")
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.set_default_timeout(15000)
            console: list[str] = []
            page_errors: list[str] = []
            responses: list[str] = []
            page.on("response", lambda r: responses.append(r.url))
            page.on("pageerror", lambda e: page_errors.append(str(e)))
            page.on(
                "console",
                lambda m: console.append(m.text)
                if m.type == "error" and "favicon" not in m.text.lower()
                else None,
            )

            # Native prompt/confirm are still real dialogs on the admin page
            # (only window.alert is rerouted to a toast). Record what was asked.
            dialogs: list[dict] = []

            def on_dialog(dialog):
                dialogs.append({"type": dialog.type, "message": dialog.message})
                dialog.accept("lt-7-2 ui probe" if dialog.type == "prompt" else None)

            page.on("dialog", on_dialog)

            # Register the admin through the real dashboard so the browser
            # context holds the session cookie.
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded")
            page.wait_for_selector("#loginView,#dashboardView")
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill(ADMIN_EMAIL)
            page.locator("#password").fill(PASSWORD)
            page.locator("#registerConfirmPassword").fill(PASSWORD)
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])")

            page.goto(base + "/admin.html", wait_until="domcontentloaded")
            row = page.locator("tbody tr", has_text=victim_email).first
            row.wait_for(state="visible")
            assert page.evaluate("() => document.querySelector('#usersPanel').classList.contains('active')")

            # 1) Suspend is refused until step-up — the browser sees the real 403.
            with page.expect_response(lambda r: "/suspend" in r.url) as refused:
                row.locator('[data-action="suspend"]').click()
            assert refused.value.status == 403, refused.value.status

            # 2) The prompt opens on its own with focus in the password field,
            #    real modal semantics, and programmatic labels for both inputs.
            password_field = page.locator("#adminStepUpPassword")
            password_field.wait_for(state="visible")
            assert page.evaluate("() => document.activeElement && document.activeElement.id") == "adminStepUpPassword"
            assert page.evaluate(
                "() => { const d = document.querySelector('dialog[aria-labelledby=adminStepUpTitle]');"
                " return !!d && d.open === true && d.matches(':modal'); }"
            ), "the prompt must be a modal dialog"
            labels = page.evaluate(
                """() => {
                  const name = (id) => {
                    const el = document.getElementById(id);
                    return el && el.labels && el.labels.length ? el.labels[0].textContent.trim() : '';
                  };
                  return { password: name('adminStepUpPassword'), code: name('adminStepUpCode') };
                }"""
            )
            assert labels["password"], labels
            assert labels["code"], labels

            # 3) Escape closes it without replaying the refused request, and
            #    focus returns to the button that opened it (WCAG 2.4.3).
            suspend_urls = lambda: [url for url in responses if "/suspend" in url]  # noqa: E731
            assert len(suspend_urls()) == 1, suspend_urls()
            page.keyboard.press("Escape")
            password_field.wait_for(state="detached")
            page.wait_for_timeout(600)
            assert len(suspend_urls()) == 1, f"Escape replayed the request: {suspend_urls()}"
            assert page.evaluate(
                "() => document.activeElement && document.activeElement.getAttribute('data-action')"
            ) == "suspend", "focus must return to the triggering button"

            # 4) Verify with the real password; the original request is replayed
            #    once and focus returns to the row button again.
            with page.expect_response(lambda r: "/suspend" in r.url) as refused_again:
                row.locator('[data-action="suspend"]').click()
            assert refused_again.value.status == 403, refused_again.value.status
            password_field.wait_for(state="visible")
            password_field.fill(PASSWORD)
            with page.expect_response(lambda r: "/suspend" in r.url) as replayed:
                page.locator("dialog:has(#adminStepUpPassword) button[data-confirm]").click()
            assert replayed.value.status == 200, replayed.value.status
            assert replayed.value.json() == {"suspended": True}, replayed.value.json()
            password_field.wait_for(state="detached")
            # A successful replay re-renders the users table, so the original
            # button is gone; the dialog must still be fully closed and nothing
            # may be left focused inside a removed dialog.
            assert page.evaluate("() => !document.querySelector('dialog[open]')")
            # The mutation happened server-side; the row still renders (the tab
            # reloads + re-renders after the retry) and nothing threw.
            row.wait_for(state="visible")

            # 5) The grant is cached in memory for this page lifetime: the next
            #    destructive action goes straight through with no second prompt.
            with page.expect_response(lambda r: "/reset-password" in r.url) as reset:
                row.locator('[data-action="reset-password"]').click()
            assert reset.value.status == 200, reset.value.status
            assert page.locator("#adminStepUpPassword").count() == 0

            # 6) D-7: no client-side grant is persisted. The only grant is the
            #    server-side one bound to the session cookie, so a reload keeps
            #    the server happy without any browser storage carrying a token.
            page.reload(wait_until="domcontentloaded")
            row = page.locator("tbody tr", has_text=victim_email).first
            row.wait_for(state="visible")
            persisted = page.evaluate(
                """() => {
                  const keys = [];
                  for (const store of [window.sessionStorage, window.localStorage]) {
                    for (let i = 0; i < store.length; i += 1) {
                      const key = store.key(i) || '';
                      if (key.includes('step-up')) keys.push(key);
                    }
                  }
                  return keys;
                }"""
            )
            assert persisted == [], f"step-up state leaked into browser storage: {persisted}"

            # 7) No uncaught error. The one console error allowed is the browser's
            # own "Failed to load resource: 403" line for the *refused* request —
            # that is the gate doing its job, not a defect.
            assert not page_errors, page_errors
            unexpected = [c for c in console if "Failed to load resource" not in c or "403" not in c]
            assert not unexpected, unexpected

            context.close()
            browser.close()

    print("LT_7_2_ADMIN_STEPUP_UI_PASSED", flush=True)
