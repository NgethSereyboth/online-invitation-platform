#!/usr/bin/env python3
"""tools/csp-violation-check.py — fail on any Content-Security-Policy violation.

The server sends `script-src 'self'` with no nonce and no hash list, so a single
inline event-handler attribute is silently refused by the browser. FB-18 recorded
four such refusals on the dashboard/public flow twice and they went unfixed; the
`smoke` gate could not see them because they are console errors, not failed
requests (FB-24).

This tool drives the two flows that actually produced them, against a real
`src/python/server.py` it starts itself:

  1. signed-in dashboard: register a fresh account, click the Templates
     quick-start button (the live check FB-20 failed), open the create dialog
  2. editor → publish → public invitation → guest RSVP submit

and records every console message and page error on every page. It exits 1 when
any page produced a CSP violation or could not reach its required state.

Usage:
    .venv/bin/python tools/csp-violation-check.py
    .venv/bin/python tools/csp-violation-check.py --port 4177 --keep-server
    .venv/bin/python tools/csp-violation-check.py --base http://127.0.0.1:8124

Evidence (JSON + screenshots) is written under artifacts/next-work/csp-check/.
Requires `.venv/bin/python` (Playwright) and a build in `src/python/`.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "next-work" / "csp-check"
VENV_PY = ROOT / ".venv" / "bin" / "python"

CSP_PATTERN = re.compile(
    r"(Content Security Policy|Refused to (?:execute|load|apply|run)|"
    r"violates the following Content Security Policy)",
    re.IGNORECASE,
)

failures: list[str] = []
notes: list[str] = []
violations: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")
    if not ok:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")
    return ok


def free_port(start: int = 4177) -> int:
    for port in range(start, start + 40):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise SystemExit("no free port")


def start_server(port: int, data_dir: Path) -> subprocess.Popen:
    env = {
        **os.environ,
        "EINVITE_DATA_DIR": str(data_dir),
        "EINVITE_DEV_AUTH_TOKENS": "1",
        "EINVITE_ALLOW_NO_SCANNER": "1",
        "PYTHONPATH": f"{ROOT / 'src' / 'python'}:{ROOT}",
        "PYTHONIOENCODING": "utf-8",
    }
    proc = subprocess.Popen(
        [str(VENV_PY), str(ROOT / "src" / "python" / "server.py"), "--port", str(port)],
        cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(120):
        time.sleep(0.25)
        if proc.poll() is not None:
            raise SystemExit(f"server exited during startup (code {proc.returncode})")
        try:
            urllib.request.urlopen(base + "/dashboard.html", timeout=2).read(64)
            return proc
        except (urllib.error.URLError, OSError):
            continue
    proc.terminate()
    raise SystemExit("server did not become ready")


def stop_server(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, 15)
    except Exception:
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        try:
            os.killpg(proc.pid, 9)
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="use an already-running server instead of starting one")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--email", help="account email (default: a fresh timestamped address)")
    ap.add_argument("--password", default="csp-check-2026")
    ap.add_argument("--keep-server", action="store_true")
    args = ap.parse_args()

    if not VENV_PY.exists():
        print("CSP_CHECK_CANNOT_RUN: .venv/bin/python is missing (Playwright lives there)")
        return 4

    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.png"):
        stale.unlink()
    data_dir = Path(tempfile.mkdtemp(prefix="einvite-csp-check-"))
    port = args.port or free_port()
    server = None
    try:
        if args.base:
            base = args.base.rstrip("/")
        else:
            server = start_server(port, data_dir)
            base = f"http://127.0.0.1:{port}"
        email = args.email or (
            "csp.check."
            + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S%f")
            + "@example.com"
        )
        run_suite(base, email, args.password)
    finally:
        if not args.keep_server:
            stop_server(server)
        if server is not None and not args.keep_server:
            shutil.rmtree(data_dir, ignore_errors=True)

    summary = {
        "base": base,
        "email": email,
        "checkedAt": datetime.datetime.now().isoformat(timespec="seconds"),
        "cspViolations": violations,
        "failures": failures,
        "notes": notes,
        "passed": not failures,
    }
    (OUT / "result.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print()
    if violations:
        print(f"CSP violations: {len(violations)}")
        for item in violations:
            print(f"  {item['where']}: {item['text'][:200]}")
    print("CSP_CHECK_PASSED" if not failures else f"CSP_CHECK_FAILED ({len(failures)} checks)")
    return 0 if not failures else 1


def run_suite(base: str, email: str, password: str) -> None:
    from playwright.sync_api import sync_playwright

    console: list[str] = []

    def collect(page, where: str):
        def on_console(message):
            text = message.text or ""
            console.append(f"{where} {message.type}: {text[:300]}")
            if CSP_PATTERN.search(text):
                violations.append({"where": where, "type": message.type, "text": text[:500]})
        def on_pageerror(error):
            console.append(f"{where} pageerror: {str(error)[:300]}")
            if CSP_PATTERN.search(str(error)):
                violations.append({"where": where, "type": "pageerror", "text": str(error)[:500]})
        page.on("console", on_console)
        page.on("pageerror", on_pageerror)

    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        collect(page, "dashboard")

        # 1 — boot the dashboard and get a fresh account signed in -------------
        page.goto(base + "/dashboard.html", wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        check("dashboard sign-in card renders", page.locator("#authSignInTab").count() == 1)
        page.click("#authRegisterTab")
        page.fill("#email", email)
        page.fill("#password", password)
        page.fill("#registerConfirmPassword", password)
        page.click("#loginBtn")
        try:
            page.wait_for_selector("#newBtn", timeout=15000)
        except Exception:
            page.click("#authSignInTab")
            page.fill("#email", email)
            page.fill("#password", password)
            page.click("#loginBtn")
            page.wait_for_selector("#newBtn", timeout=15000)
        check("fresh account signed in", page.is_visible("#newBtn"), email)
        page.screenshot(path=str(OUT / "dashboard-signed-in.png"))

        # 2 — the Templates quick-start button (the FB-20 red check) ----------
        button = page.locator("#quickstartTemplates")
        check("Templates quick-start button exists", button.count() == 1)
        inline = page.evaluate(
            "() => { const b = document.querySelector('#quickstartTemplates');"
            " return b ? b.getAttribute('onclick') : 'missing'; }"
        )
        check("Templates quick-start has no inline handler attribute", inline is None, repr(inline))
        button.click()
        try:
            page.wait_for_url(re.compile(r"templates\.html"), timeout=10000)
            navigated = True
        except Exception:
            navigated = False
        check("Templates quick-start navigates to templates.html", navigated, page.url)
        page.wait_for_timeout(600)

        # 3 — create dialog opens cleanly from the dashboard ------------------
        page.goto(base + "/dashboard.html", wait_until="domcontentloaded")
        page.wait_for_selector("#newBtn", timeout=15000)
        page.click("#newBtn")
        page.wait_for_selector("#createDialog", state="visible")
        check("create dialog opens", page.is_visible("#createDialog"))
        page.fill("#newTitle", "CSP Check Invitation")
        page.select_option("#newType", "Wedding")
        page.click("#confirmCreate")
        try:
            page.wait_for_url(re.compile(r"/editor"), timeout=25000)
            created = True
        except Exception:
            created = False
        check("invitation created and editor loaded", created, page.url)
        if not created:
            browser.close()
            return

        # 4 — publish and resolve the public link ----------------------------
        page.wait_for_timeout(1500)
        for _ in range(6):  # dismiss the first-run tour if it opened
            tour = page.locator("dialog.final-tour[open]")
            if not tour.count():
                break
            try:
                page.locator("dialog.final-tour button:visible").filter(has_text="Skip").first.click()
                page.wait_for_timeout(300)
            except Exception:
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "editor.png"))
        published = False
        try:
            page.click("#publishBtn", timeout=10000)
            published = True
        except Exception:
            pass
        check("editor publish control ran", published)
        page.wait_for_timeout(2500)
        body = page.locator("body").inner_text()
        match = re.search(r"/i/[A-Za-z0-9_-]+", body)
        if not match:
            for anchor in page.locator("a").all():
                href = anchor.get_attribute("href") or ""
                found = re.search(r"/i/[A-Za-z0-9_-]+", href)
                if found:
                    match = found
                    break
        check("published invitation exposes /i/<slug>", match is not None,
              match.group(0) if match else "not found")
        page.screenshot(path=str(OUT / "published.png"))

        if match:
            slug_path = match.group(0)
            public = browser.new_page(viewport={"width": 375, "height": 812})
            collect(public, "public")
            public.goto(base + slug_path, wait_until="domcontentloaded")
            public.wait_for_timeout(1500)
            cover = public.locator("#openCover")
            if cover.count():
                cover.click()
                public.wait_for_timeout(1500)
            else:
                notes.append("public page had no #openCover (opening disabled?)")
            public.screenshot(path=str(OUT / "public.png"))

            form = public.locator("#rsvp")
            check("public RSVP form renders", form.count() == 1)
            if form.count():
                public.fill("#rsvp input[name=name]", "CSP Check Guest")
                status_select = public.locator("#rsvp select[name=status]")
                if status_select.count():
                    status_select.select_option("Yes, joyfully")
                meal_select = public.locator("#rsvp select[name=meal]")
                if meal_select.count():
                    try:
                        meal_select.select_option("Vegetarian")
                    except Exception:
                        pass
                public.locator("#rsvp button").first.click()
                try:
                    public.wait_for_function(
                        "() => /Thank you|Your response was received/.test("
                        "document.querySelector('#rsvp')?.innerText || '')",
                        timeout=15000,
                    )
                    submitted = True
                except Exception:
                    submitted = False
                note = (public.locator("#rsvp").inner_text() or "")[:160] if form.count() else ""
                check("public RSVP submits and confirms", submitted, note.replace("\n", " "))
                public.screenshot(path=str(OUT / "public-rsvp-submitted.png"))
            public.close()

        browser.close()

    (OUT / "console.log").write_text("\n".join(console) + "\n", encoding="utf-8")
    check("no CSP violation on any page", not violations,
          f"{len(violations)} violation(s) — see artifacts/next-work/csp-check/console.log")
    other_errors = [
        line for line in console
        if " error: " in line and not CSP_PATTERN.search(line)
        and "favicon" not in line.lower()
    ]
    if other_errors:
        notes.append(f"{len(other_errors)} non-CSP console error(s): " + other_errors[0][:200])
        print(f"[note] {len(other_errors)} non-CSP console error(s):")
        for line in other_errors[:5]:
            print(f"  {line[:220]}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
