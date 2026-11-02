#!/usr/bin/env python3
"""Tablet dead zone check: is there a visible control that opens Tools at 601-820?"""
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

STATE = """() => {
  const vis = n => { const r = n.getBoundingClientRect(), cs = getComputedStyle(n);
    return {w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y),
            display: cs.display, visibility: cs.visibility, hidden: n.hasAttribute('hidden')}; };
  const bar = document.querySelector('#mobileEditorV14Bar');
  const tabs = [...document.querySelectorAll('[data-studio-tab]')].map(n => ({tab: n.dataset.studioTab,
    inRail: !!n.closest('.studio-tool-rail'), ariaHiddenAncestor: n.closest('[aria-hidden="true"]')?.tagName || null,
    inertAncestor: !!n.closest('[inert]'), ...vis(n)}));
  return {drawer: document.body.dataset.editorDrawer, layout: document.body.dataset.editorLayout,
    hasMobileClass: document.body.classList.contains('mobile-editor-v14'),
    flag: !!window.__einviteMobileEditorV14,
    mq820: matchMedia('(max-width: 820px)').matches, mq600: matchMedia('(max-width: 600px)').matches,
    bar: bar ? vis(bar) : null, barBtn: document.querySelector('#mobileToolsMode') ? vis(document.querySelector('#mobileToolsMode')) : null,
    tabs,
    rules: (() => { const out = [];
      for (const ss of document.styleSheets) { let rs; try { rs = ss.cssRules; } catch (e) { continue; }
        const walk = list => { for (const r of list) {
          if (r.cssRules) walk(r.cssRules);
          if (r.selectorText && r.selectorText.includes('mobile-editor-v14-bar'))
            out.push({sel: r.selectorText.slice(0, 110), display: r.style.display, media: r.parentRule?.media?.mediaText || ''});
        } };
        walk(rs); }
      return out; })()};
}"""


def main() -> int:
    with sync_playwright() as pw:
        browser = launch_chromium(pw)
        try:
            ctx = browser.new_context(viewport={"width": 768, "height": 900})
            page = ctx.new_page()
            page.set_default_timeout(30000)
            page.goto(BASE + "/dashboard.html", wait_until="domcontentloaded")
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill(f"round-4-tablet-{int(time.time())}@example.com")
            page.locator("#password").fill("Probe-round-4-123")
            page.locator("#registerConfirmPassword").fill("Probe-round-4-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])")
            row = page.evaluate("""async doc => {
              const r = await fetch('/api/invitations', {method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({slug: 'round-4-tablet-' + Date.now(), document: doc})});
              if (!r.ok) throw Error(await r.text());
              return r.json();
            }""", DOC)
            results = {}
            for width in (601, 700, 768, 819, 820, 900):
                page.set_viewport_size({"width": width, "height": 900})
                page.goto(BASE + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded")
                page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'")
                dismiss_editor_onboarding(page)
                page.wait_for_timeout(900)
                state = page.evaluate(STATE)
                results[width] = state
                print(width, json.dumps(state)[:1300], flush=True)
            ctx.close()
        finally:
            browser.close()
    (Path(__file__).resolve().parent / "probe-tablet.json").write_text(json.dumps(results, indent=1))
    print("TABLET_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
