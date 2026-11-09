"""Sprint 4 request-correlation pins.

The server must attach a sanitized request ID before BaseHTTPRequestHandler logs
the request, and user-facing error toasts must show that reference without
turning it into HTML or exposing any request data.
"""
from __future__ import annotations

import urllib.request

from browser_runtime import launch_chromium
from playwright.sync_api import sync_playwright
from v14_test_utils import app_server


def test_request_id_is_in_json_log_and_response_header():
    with app_server({"EINVITE_JSON_LOGS": "1", "EINVITE_ALLOW_NO_SCANNER": "1"}) as (_process, base, data):
        request = urllib.request.Request(
            f"{base}/api/health/live",
            headers={"X-Request-ID": "sprint4-request-1"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            assert response.status == 200
            assert response.headers["X-Request-ID"] == "sprint4-request-1"
        log = (data / "server-test.log").read_text(encoding="utf-8", errors="replace")
        assert '"requestId": "sprint4-request-1"' in log
        assert "sprint4-request-1" in log


def test_error_toast_renders_a_reference_as_text():
    with app_server({"EINVITE_ALLOW_NO_SCANNER": "1"}) as (_process, base, _data):
        with sync_playwright() as playwright:
            browser = launch_chromium(playwright)
            try:
                page = browser.new_page()
                page.goto(f"{base}/dashboard.html", wait_until="domcontentloaded")
                page.wait_for_function("typeof window.uiToast === 'function'")
                page.evaluate("window.uiToast('Save failed', {type: 'error', reference: 'req-123'})")
                toast = page.locator(".ei-toast strong").last
                assert toast.inner_text() == "Save failed · Reference: req-123"
            finally:
                browser.close()
