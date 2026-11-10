#!/usr/bin/env python3
"""Verify the enforcing CSP style nonce on the served landing and check-in pages.

Boots `src/python/server.py` through the shared V14 test harness, opens `/` and
`/checkin` in Chromium, and checks:

  * the `Content-Security-Policy` response header is present;
  * `style-src` carries a `'nonce-...'` source and does NOT carry
    `'unsafe-inline'`;
  * every `<style>` element in the DOM carries the same nonce;
  * a nonce-bearing probe stylesheet is actually applied by the browser;
  * no `Refused to apply inline style` (or other style-src) CSP violation is
    logged in the console or raised as a `securitypolicyviolation` event.

The landing and check-in pages inline critical CSS with the per-response nonce
and load the full route stylesheet asynchronously. The DOM-nonce assertion is
therefore meaningful, and the nonce-bearing probe remains the positive control
that proves the policy accepts the server's nonce rather than merely printing
one.

Usage:
    .venv/bin/python scripts/verify-csp-nonce.py
    .venv/bin/python scripts/verify-csp-nonce.py --json-out reports/csp-nonce-verification.json

Exit codes: 0 all checks passed, 1 a check failed, 2 the harness could not run.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - exercised only outside the venv
    sync_playwright = None

from tests.browser_runtime import launch_chromium
from tests.v14_test_utils import fresh_server

INLINE_STYLE_REFUSAL = re.compile(r"Refused to apply (?:inline )?style", re.IGNORECASE)


def csp_directive(csp: str, name: str) -> str:
    """Return one directive's value from a Content-Security-Policy header."""
    for chunk in csp.split(";"):
        tokens = chunk.strip().split()
        if tokens and tokens[0].lower() == name.lower():
            return " ".join(tokens[1:])
    return ""


def style_nonce(style_src: str) -> str:
    match = re.search(r"'nonce-([^']+)'", style_src)
    return match.group(1) if match else ""


def check(checks: list[dict], name: str, passed: bool, detail: str = "") -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def verify_page(page, base: str, path: str) -> dict:
    console_errors: list[str] = []
    page_errors: list[str] = []
    console_violations: list[dict] = []

    def on_console(message):
        text = message.text or ""
        if message.type == "error":
            console_errors.append(text[:500])
        if INLINE_STYLE_REFUSAL.search(text) or (
            "Content Security Policy" in text and "style" in text.lower()
        ):
            console_violations.append({"type": message.type, "text": text[:1000]})

    def on_page_error(error):
        text = str(error)
        page_errors.append(text[:500])
        if INLINE_STYLE_REFUSAL.search(text):
            console_violations.append({"type": "pageerror", "text": text[:1000]})

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.add_init_script(
        """
        window.__einviteCspViolations = [];
        document.addEventListener('securitypolicyviolation', (event) => {
          const directive = event.violatedDirective || '';
          if (directive.toLowerCase().startsWith('style-src')) {
            window.__einviteCspViolations.push({
              directive,
              blockedURI: event.blockedURI || '',
              sample: (event.sample || '').slice(0, 500)
            });
          }
        }, true);
        """
    )

    response = page.goto(base + path, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1000)

    status = response.status if response else 0
    headers = response.headers if response else {}
    csp = headers.get("content-security-policy") or headers.get("Content-Security-Policy") or ""
    style_src = csp_directive(csp, "style-src")
    nonce = style_nonce(style_src)
    unsafe_inline = "unsafe-inline" in style_src.lower()

    dom = page.evaluate(
        """
        () => ({
          styles: [...document.querySelectorAll('style')].map((element) => ({
            nonce: element.nonce,
            chars: (element.textContent || '').length
          })),
          stylesheets: [...document.querySelectorAll('link[rel="stylesheet"]')]
            .map((element) => element.getAttribute('href') || '')
        })
        """
    )
    styles = dom.get("styles", [])
    missing_nonce = [item for item in styles if not item.get("nonce")]
    mismatched_nonce = [
        item for item in styles
        if item.get("nonce") and nonce and item.get("nonce") != nonce
    ]

    probe_applied = ""
    if nonce:
        probe_applied = page.evaluate(
            """
            (nonce) => {
              const probe = document.createElement('style');
              probe.setAttribute('nonce', nonce);
              probe.textContent = ':root{--einvite-csp-nonce-probe:applied}';
              document.head.appendChild(probe);
              const value = getComputedStyle(document.documentElement)
                .getPropertyValue('--einvite-csp-nonce-probe').trim();
              probe.remove();
              return value;
            }
            """,
            nonce,
        )
    page.wait_for_timeout(250)

    event_violations = page.evaluate("() => window.__einviteCspViolations || []")
    csp_violations = console_violations + [
        {"type": "securitypolicyviolation", **item} for item in event_violations
    ]

    checks: list[dict] = []
    check(checks, f"{path} responds 200", status == 200, f"status={status}")
    check(checks, f"{path} sends Content-Security-Policy", bool(csp), csp[:160])
    check(checks, f"{path} style-src has a nonce", bool(nonce), style_src)
    check(checks, f"{path} style-src has no 'unsafe-inline'", not unsafe_inline, style_src)
    check(
        checks,
        f"{path} every <style> has the header nonce",
        not missing_nonce and not mismatched_nonce,
        (
            f"{len(styles)} style element(s)"
            + (" — vacuous: page has no inline <style>" if not styles else "")
            + (f"; missing={len(missing_nonce)} mismatched={len(mismatched_nonce)}" if styles else "")
        ),
    )
    check(
        checks,
        f"{path} accepts a nonce-bearing stylesheet",
        probe_applied == "applied",
        f"probe={probe_applied or 'not applied'}",
    )
    check(
        checks,
        f"{path} logs no style-src CSP violation",
        not csp_violations,
        f"{len(csp_violations)} violation(s)",
    )

    return {
        "path": path,
        "status": status,
        "csp": csp,
        "styleSrc": style_src,
        "nonce": nonce,
        "unsafeInline": unsafe_inline,
        "styleTagCount": len(styles),
        "styleTags": styles,
        "styleTagsMissingNonce": len(missing_nonce),
        "styleTagsMismatchedNonce": len(mismatched_nonce),
        "styleNonceCheck": "vacuous (0 <style> elements)" if not styles else "checked",
        "nonceProbe": probe_applied,
        "stylesheets": dom.get("stylesheets", []),
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "cspStyleViolations": csp_violations,
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        default=str(ROOT / "reports" / "csp-nonce-verification.json"),
        help="write the structured result here (default: reports/csp-nonce-verification.json)",
    )
    args = parser.parse_args()

    if sync_playwright is None:
        print("CSP_NONCE_CHECK_CANNOT_RUN: Playwright is not installed in this interpreter")
        print("Run with .venv/bin/python.")
        return 2

    output = Path(args.json_out)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "branch": None,
        "baseUrl": None,
        "pages": [],
        "notes": [],
        "passed": False,
    }

    try:
        with fresh_server() as (_process, base, _data):
            result["baseUrl"] = base
            with sync_playwright() as play:
                browser = launch_chromium(play)
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                try:
                    for path in ("/", "/checkin"):
                        page = context.new_page()
                        try:
                            page_result = verify_page(page, base, path)
                        finally:
                            page.close()
                        result["pages"].append(page_result)
                finally:
                    context.close()
                    browser.close()
    except Exception as exc:  # noqa: BLE001 - the result file must record the blocker
        result["error"] = f"{type(exc).__name__}: {exc}"
        print(f"[FAIL] harness: {result['error']}")

    if not result["pages"]:
        result["notes"].append("No page was verified; see error.")
    for page_result in result["pages"]:
        if page_result["styleTagCount"] == 0:
            result["notes"].append(
                f"{page_result['path']} has 0 <style> elements; the DOM nonce check is "
                "vacuous and the nonce probe is the positive control."
            )
        if page_result["consoleErrors"]:
            result["notes"].append(
                f"{page_result['path']} logged {len(page_result['consoleErrors'])} "
                "non-CSP console error(s); see consoleErrors."
            )

    result["passed"] = bool(result["pages"]) and all(
        page_result["passed"] for page_result in result["pages"]
    ) and "error" not in result
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print(f"Result: {'PASS' if result['passed'] else 'FAIL'}")
    print(f"JSON: {output}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
