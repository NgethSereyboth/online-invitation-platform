#!/usr/bin/env python3
"""Who resets the drawer after a saved design page + reload?

Wraps EInviteResponsiveLayout as soon as it exists (init script) and records
every setDrawer/sync call with a stack, plus every data-editor-drawer change.
"""
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

INSTRUMENT = """() => {
  if (window.__probeInstalled) return;
  window.__probeInstalled = true;
  window.__probe = [];
  const stamp = () => (window.__probe.length + ':' + Math.round(performance.now()));
  const wrap = () => {
    const api = window.EInviteResponsiveLayout;
    if (!api || api.__probeWrapped) return !!api;
    api.__probeWrapped = true;
    for (const k of ['setDrawer', 'openCreation', 'closeCreation', 'openInspector', 'closeInspector', 'sync']) {
      const orig = api[k];
      if (typeof orig !== 'function') continue;
      try { api[k] = function (...a) {
        window.__probe.push({at: stamp(), call: k, arg: a[0], drawer: document.body.dataset.editorDrawer,
          stack: (new Error().stack || '').split('\\n').slice(1, 7).join(' | ')});
        return orig.apply(this, a);
      }; } catch (e) { window.__probe.push({at: stamp(), call: k, error: String(e)}); }
    }
    new MutationObserver(muts => {
      for (const m of muts) window.__probe.push({at: stamp(), attr: m.attributeName,
        old: m.oldValue, now: document.body.getAttribute(m.attributeName)});
    }).observe(document.body, {attributes: true, attributeOldValue: true,
      attributeFilter: ['data-editor-drawer', 'class']});
    return true;
  };
  if (!wrap()) { const t = setInterval(() => { if (wrap()) clearInterval(t); }, 10); }
}"""

SNAP = """() => {
  const l = document.querySelector('aside.left');
  const r = l?.getBoundingClientRect();
  return {drawer: document.body.dataset.editorDrawer, mode: document.body.dataset.mobileEditorMode,
          leftX: r ? Math.round(r.x) : null, vis: l ? getComputedStyle(l).visibility : null,
          cls: document.body.className.split(' ').filter(c => /drawer|mobile|inspector/.test(c)),
          pages: window.EInviteEditorBridge?.getState?.().designPages?.length};
}"""


def scenario(page, label, do_add=False):
    if do_add:
        page.evaluate("() => window.EInviteCommandRegistry.execute('page.addBlank')")
        page.wait_for_function("() => window.EInviteEditorBridge.getState().designPages.length === 1")
        page.wait_for_selector("#designPagesManager .v22-page-card[data-page-id]", state="attached")
        page.evaluate("() => window.EInviteEditorBridge.save()")
        page.wait_for_function("() => document.documentElement.dataset.savePending === 'false'")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'")
        dismiss_editor_onboarding(page)
    page.wait_for_timeout(1200)
    page.evaluate("(" + INSTRUMENT + ")()")
    page.evaluate("() => { window.__probe.length = 0 }")
    print(label, "BEFORE", json.dumps(page.evaluate(SNAP)), flush=True)
    page.evaluate("() => window.EInviteResponsiveLayout.openCreation()")
    page.wait_for_timeout(600)
    print(label, "AFTER", json.dumps(page.evaluate(SNAP)), flush=True)
    log = page.evaluate("() => window.__probe")
    print(label, "LOG", json.dumps(log)[:4000], flush=True)


def main() -> int:
    with sync_playwright() as pw:
        browser = launch_chromium(pw)
        try:
            ctx = browser.new_context(viewport={"width": 360, "height": 800})
            page = ctx.new_page()
            page.set_default_timeout(30000)
            page.add_init_script("(" + INSTRUMENT + ")()")
            page.goto(BASE + "/dashboard.html", wait_until="domcontentloaded")
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill(f"round-4-drawer2-{int(time.time())}@example.com")
            page.locator("#password").fill("Probe-round-4-123")
            page.locator("#registerConfirmPassword").fill("Probe-round-4-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])")
            row = page.evaluate("""async doc => {
              const r = await fetch('/api/invitations', {method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({slug: 'round-4-drawer2-' + Date.now(), document: doc})});
              if (!r.ok) throw Error(await r.text());
              return r.json();
            }""", DOC)
            page.goto(BASE + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded")
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'")
            dismiss_editor_onboarding(page)
            scenario(page, "FRESH")
            scenario(page, "AFTER_PAGE_RELOAD", do_add=True)
            ctx.close()
        finally:
            browser.close()
    print("DRAWER2_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
