#!/usr/bin/env python3
"""At 768, list every visible control outside inert asides."""
from __future__ import annotations

import json
import sys
import time

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from browser_runtime import dismiss_editor_onboarding, launch_chromium  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://127.0.0.1:4180"
DOC = json.loads((Path(__file__).resolve().parent / "probe_doc.json").read_text())

LIST = """() => [...document.querySelectorAll('button, [role="button"], a[href]')].filter(n => {
    const r = n.getBoundingClientRect(), cs = getComputedStyle(n);
    return r.width > 1 && r.height > 1 && cs.visibility !== 'hidden' && cs.display !== 'none' && !n.closest('[inert]');
  }).map(n => ({text: (n.innerText || n.getAttribute('aria-label') || '').trim().slice(0, 40),
    id: n.id, cls: (n.className || '').toString().slice(0, 60), x: Math.round(n.getBoundingClientRect().x),
    y: Math.round(n.getBoundingClientRect().y), w: Math.round(n.getBoundingClientRect().width)}))"""


def main() -> int:
    with sync_playwright() as pw:
        browser = launch_chromium(pw)
        try:
            ctx = browser.new_context(viewport={"width": 768, "height": 900})
            page = ctx.new_page()
            page.set_default_timeout(30000)
            page.goto(BASE + "/dashboard.html", wait_until="domcontentloaded")
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill(f"round-4-btns-{int(time.time())}@example.com")
            page.locator("#password").fill("Probe-round-4-123")
            page.locator("#registerConfirmPassword").fill("Probe-round-4-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])")
            row = page.evaluate("""async doc => {
              const r = await fetch('/api/invitations', {method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({slug: 'round-4-btns-' + Date.now(), document: doc})});
              if (!r.ok) throw Error(await r.text());
              return r.json();
            }""", DOC)
            page.goto(BASE + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded")
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'")
            dismiss_editor_onboarding(page)
            page.wait_for_timeout(900)
            print(json.dumps(page.evaluate(LIST), indent=1), flush=True)
            ctx.close()
        finally:
            browser.close()
    print("BUTTONS_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
