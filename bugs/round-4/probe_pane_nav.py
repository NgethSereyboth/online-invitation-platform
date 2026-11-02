#!/usr/bin/env python3
"""What does the creation drawer show on each contract width, and which
visible control switches it to the Pages pane?

BUG-R4-3 candidate: at 360 the Tools drawer opens but
`[data-studio-tab="pages"]` resolves to a rail button with zero visible size,
so a user has no rail to switch panes from.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from browser_runtime import dismiss_editor_onboarding, launch_chromium  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://127.0.0.1:4180"
DOC = json.loads((Path(__file__).resolve().parent / "probe_doc.json").read_text())
WIDTHS = tuple(int(x) for x in os.environ.get("PROBE_WIDTHS", "360,390,768,1024,1280").split(","))
HEIGHT = int(os.environ.get("PROBE_HEIGHT", "900"))
SETTLE = int(os.environ.get("PROBE_SETTLE", "700"))

DUMP = """() => {
  const vis = el => {
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden' &&
      r.right > 0 && r.left < innerWidth && r.bottom > 0 && r.top < innerHeight;
  };
  const row = sel => [...document.querySelectorAll(sel)].map(el => {
    const r = el.getBoundingClientRect();
    return {sel, tag: el.tagName, id: el.id, text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 40),
      cls: String(el.className).slice(0, 70), visible: vis(el),
      box: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}};
  });
  const left = document.querySelector('aside.left');
  return {
    width: innerWidth,
    layout: document.body.dataset.editorLayout,
    drawer: document.body.dataset.editorDrawer,
    mode: document.body.dataset.mobileEditorMode,
    barDisplay: getComputedStyle(document.querySelector('#mobileEditorV14Bar') || document.body).display,
    railDisplay: getComputedStyle(document.querySelector('.studio-tool-rail') || document.body).display,
    leftX: left ? Math.round(left.getBoundingClientRect().x) : null,
    leftText: left ? (left.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 260) : '',
    tabs: row('[data-studio-tab]'),
    panes: row('[data-studio-pane]'),
    paneTabs: row('.studio-pane-tab, [data-pane-tab], .studio-pane-tabs button'),
    tops: [...document.querySelectorAll('aside.left button, aside.left [role=tab]')].filter(e => {
      const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.top < 160;
    }).slice(0, 10).map(e => ({text: (e.innerText || e.getAttribute('aria-label') || '').trim().slice(0, 30),
      id: e.id, cls: String(e.className).slice(0, 60), attrs: [...e.attributes].map(a => a.name + '=' + a.value.slice(0, 30)).join(' ')}))
  };
}"""


def main() -> int:
    with sync_playwright() as pw:
        browser = launch_chromium(pw)
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.set_default_timeout(30000)
            page.goto(BASE + "/dashboard.html", wait_until="domcontentloaded")
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill(f"round-4-panenav-{int(time.time())}@example.com")
            page.locator("#password").fill("Probe-round-4-123")
            page.locator("#registerConfirmPassword").fill("Probe-round-4-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])")
            row = page.evaluate("""async doc => {
              const r = await fetch('/api/invitations', {method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({slug: 'round-4-panenav-' + Date.now(), document: doc})});
              if (!r.ok) throw Error(await r.text());
              return r.json();
            }""", DOC)
            page.goto(BASE + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded")
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'")
            dismiss_editor_onboarding(page)
            # Match the sweep's document: one saved design page, so boot has to
            # render the Pages manager before the drawer can settle.
            page.evaluate("() => window.EInviteCommandRegistry.execute('page.addBlank')")
            page.wait_for_function("() => window.EInviteEditorBridge.getState().designPages.length === 1")
            page.evaluate("() => window.EInviteEditorBridge.save()")
            page.wait_for_function("() => document.documentElement.dataset.savePending === 'false'")
            storage = ctx.storage_state()
            ctx.close()

            for width in WIDTHS:
                c = browser.new_context(viewport={"width": width, "height": HEIGHT}, storage_state=storage)
                p = c.new_page()
                p.set_default_timeout(30000)
                p.goto(BASE + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded")
                p.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'")
                dismiss_editor_onboarding(p)
                p.evaluate("""() => {
                  window.__dr = [];
                  new MutationObserver(ms => {
                    for (const m of ms) if (m.attributeName === 'data-editor-drawer')
                      window.__dr.push({t: Math.round(performance.now()), v: document.body.dataset.editorDrawer});
                  }).observe(document.body, {attributes: true, attributeFilter: ['data-editor-drawer']});
                }""")
                p.wait_for_timeout(SETTLE)  # let the boot restore finish (OBS-R4-2)
                if width <= 820:
                    p.locator("#mobileToolsMode").click()
                    for i in range(5):
                        p.wait_for_timeout(200)
                        probe = p.evaluate("""() => {
                          const b = document.querySelector('#mobileToolsMode');
                          const r = b.getBoundingClientRect();
                          const hit = document.elementFromPoint(Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2));
                          return {drawer: document.body.dataset.editorDrawer, mode: document.body.dataset.mobileEditorMode,
                            box: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)},
                            hit: hit ? hit.tagName + '#' + (hit.id || '') + '.' + String(hit.className).slice(0, 40) : null};
                        }""")
                        print(f"CLICK {width} +{(i + 1) * 200}ms", json.dumps(probe))
                    print(f"DRAWER_LOG {width}", json.dumps(p.evaluate("() => window.__dr"))[:600])
                    print(f"SET_TRACE {width}", json.dumps(p.evaluate("() => (window.__setTrace || []).slice(-12)"))[:3000])
                p.wait_for_timeout(500)
                data = p.evaluate(DUMP)
                print(f"\n=== {width} ===")
                print(json.dumps({k: data[k] for k in ("layout", "drawer", "mode", "barDisplay", "railDisplay", "leftX", "leftText")}, ensure_ascii=False))
                print("tabs:", json.dumps([t for t in data["tabs"]]))
                print("paneTabs:", json.dumps([t for t in data["paneTabs"]]))
                print("tops:", json.dumps(data["tops"], ensure_ascii=False)[:1200])
                p.screenshot(path=str(Path(__file__).resolve().parent / "shots" / f"probe-panenav-{width}.png"), full_page=False)
                c.close()
        finally:
            browser.close()
    print("PANENAV_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
