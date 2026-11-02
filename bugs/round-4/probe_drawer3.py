#!/usr/bin/env python3
"""Early-tap race: does a Tools tap right after editor-ready survive boot?"""
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
  const stamp = () => Math.round(performance.now());
  const wrap = () => {
    const api = window.EInviteResponsiveLayout;
    if (!api || api.__probeWrapped) return !!api;
    api.__probeWrapped = true;
    for (const k of ['setDrawer', 'openCreation', 'closeCreation', 'sync']) {
      const orig = api[k];
      if (typeof orig !== 'function') continue;
      api[k] = function (...a) {
        window.__probe.push({t: stamp(), call: k, arg: a[0], drawer: document.body.dataset.editorDrawer,
          stack: (new Error().stack || '').split('\\n').slice(2, 6).join(' | ')});
        return orig.apply(this, a);
      };
    }
    new MutationObserver(muts => {
      for (const m of muts) if (m.attributeName === 'data-editor-drawer')
        window.__probe.push({t: stamp(), drawer: m.oldValue + '->' + document.body.dataset.editorDrawer});
    }).observe(document.body, {attributes: true, attributeOldValue: true, attributeFilter: ['data-editor-drawer']});
    return true;
  };
  if (!wrap()) { const t = setInterval(() => { if (wrap()) clearInterval(t); }, 10); }
}"""

SNAP = """() => {
  const l = document.querySelector('aside.left'), r = l?.getBoundingClientRect();
  const rr = document.querySelector('aside.right');
  return {drawer: document.body.dataset.editorDrawer, mode: document.body.dataset.mobileEditorMode,
    x: r ? Math.round(r.x) : null, vis: l ? getComputedStyle(l).visibility : null,
    ariaL: l?.getAttribute('aria-hidden'), ariaR: rr?.getAttribute('aria-hidden'),
    cls: document.body.className.split(' ').filter(c => /drawer|mobile|inspector/.test(c)),
    pages: window.EInviteEditorBridge?.getState?.().designPages?.length,
    ready: document.documentElement.dataset.editorReady};
}"""


def main() -> int:
    with sync_playwright() as pw:
        browser = launch_chromium(pw)
        try:
            WIDTH = int(__import__('os').environ.get('PROBE_WIDTH', '360'))
            ctx = browser.new_context(viewport={"width": WIDTH, "height": 800})
            # aria snapshot helper injected below via probe state
            page = ctx.new_page()
            page.set_default_timeout(30000)
            page.add_init_script("(" + INSTRUMENT + ")()")
            page.goto(BASE + "/dashboard.html", wait_until="domcontentloaded")
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill(f"round-4-drawer3-{int(time.time())}@example.com")
            page.locator("#password").fill("Probe-round-4-123")
            page.locator("#registerConfirmPassword").fill("Probe-round-4-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])")
            row = page.evaluate("""async doc => {
              const r = await fetch('/api/invitations', {method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({slug: 'round-4-drawer3-' + Date.now(), document: doc})});
              if (!r.ok) throw Error(await r.text());
              return r.json();
            }""", DOC)

            def run(label, action):
                page.goto(BASE + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded")
                page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'")
                dismiss_editor_onboarding(page)
                page.evaluate("(" + INSTRUMENT + ")()")
                page.evaluate("() => { window.__probe.length = 0 }")
                print(label, "BEFORE", json.dumps(page.evaluate(SNAP)), flush=True)
                action()
                print(label, "T0", json.dumps(page.evaluate(SNAP)), flush=True)
                for i in range(6):
                    page.wait_for_timeout(500)
                    print(label, "SAMPLE", i, json.dumps(page.evaluate(SNAP)), flush=True)
                print(label, "LOG", json.dumps(page.evaluate("() => window.__probe"))[:3000], flush=True)

            run("EARLY_TOOLS_CLICK", lambda: page.locator("#mobileToolsMode").click())
            run("EARLY_OPEN_CREATION", lambda: page.evaluate("() => window.EInviteResponsiveLayout.openCreation()"))
            ctx.close()
        finally:
            browser.close()
    print("DRAWER3_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
