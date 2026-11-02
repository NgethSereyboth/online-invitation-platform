#!/usr/bin/env python3
"""Instrument the mobile drawer transition: what resets dataset.editorDrawer?"""
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

SNAP = """() => {
  const l = document.querySelector('aside.left'), h = document.querySelector('.studio-pane-host');
  const lr = l?.getBoundingClientRect();
  return {
    drawer: document.body.dataset.editorDrawer,
    classes: document.body.className.split(' ').filter(c => c.includes('drawer') || c.includes('mobile') || c.includes('inspector')),
    mode: document.body.dataset.mobileEditorMode,
    layout: document.body.dataset.editorLayout,
    activeTab: document.body.dataset.activeInspector,
    leftX: lr ? Math.round(lr.x) : null,
    leftVis: l ? getComputedStyle(l).visibility : null,
    leftAria: l?.getAttribute('aria-hidden'),
    hostCls: h?.className,
    hostAria: h?.getAttribute('aria-hidden'),
    hostInert: h ? h.inert : null,
    api: window.EInviteResponsiveLayout ? {v: window.EInviteResponsiveLayout.version, mode: window.EInviteResponsiveLayout.mode()} : null,
  };
}"""


def main() -> int:
    with sync_playwright() as pw:
        browser = launch_chromium(pw)
        try:
            ctx = browser.new_context(viewport={"width": 360, "height": 800})
            page = ctx.new_page()
            page.set_default_timeout(30000)
            page.goto(BASE + "/dashboard.html", wait_until="domcontentloaded")
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill(f"round-4-drawer-{int(time.time())}@example.com")
            page.locator("#password").fill("Probe-round-4-123")
            page.locator("#registerConfirmPassword").fill("Probe-round-4-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])")
            row = page.evaluate("""async doc => {
              const r = await fetch('/api/invitations', {method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({slug: 'round-4-drawer-' + Date.now(), document: doc})});
              if (!r.ok) throw Error(await r.text());
              return r.json();
            }""", DOC)
            page.goto(BASE + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded")
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'")
            dismiss_editor_onboarding(page)
            page.wait_for_timeout(1200)
            print("INITIAL", json.dumps(page.evaluate(SNAP)), flush=True)

            page.evaluate("""() => {
              window.__drawerLog = [];
              for (const ev of ['einvite:workspace-resized', 'einvite:editor-ready']) {
                document.addEventListener(ev, e => window.__drawerLog.push([ev, Date.now(), JSON.stringify(e.detail || null), document.body.dataset.editorDrawer]));
              }
              window.__drawerSets = [];
              const api = window.EInviteResponsiveLayout;
              for (const k of ['setDrawer', 'openCreation', 'closeCreation', 'openInspector', 'sync']) {
                const orig = api[k];
                if (!orig) continue;
                api[k] = (...a) => { window.__drawerSets.push([k, Date.now(), document.body.dataset.editorDrawer]); return orig(...a); };
              }
            }""")
            page.evaluate("() => window.EInviteResponsiveLayout.openCreation()")
            print("AFTER_CALL", json.dumps(page.evaluate(SNAP)), flush=True)
            page.wait_for_timeout(400)
            print("AFTER_400", json.dumps(page.evaluate(SNAP)), flush=True)
            print("CALLS", json.dumps(page.evaluate("() => window.__drawerSets")), flush=True)
            print("EVENTS", json.dumps(page.evaluate("() => window.__drawerLog.slice(-12)")), flush=True)

            page.locator("#mobileToolsMode").click()
            print("AFTER_TOOLS", json.dumps(page.evaluate(SNAP)), flush=True)
            page.wait_for_timeout(400)
            print("AFTER_TOOLS_400", json.dumps(page.evaluate(SNAP)), flush=True)

            page.locator('[data-studio-tab="pages"]').click()
            page.wait_for_timeout(500)
            print("AFTER_PAGES_TAB", json.dumps(page.evaluate(SNAP)), flush=True)
            print("CALLS2", json.dumps(page.evaluate("() => window.__drawerSets")), flush=True)
            print("EVENTS2", json.dumps(page.evaluate("() => window.__drawerLog.slice(-12)")), flush=True)
            ctx.close()
        finally:
            browser.close()
    print("DRAWER_PROBE_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
