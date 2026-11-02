#!/usr/bin/env python3
"""Focused probe: are the phase-10 Pages cards really invisible at 360/390?

The round-4 flow records `pane: true, cards: 0` after `openCreation()` at the
two phone widths. This probe reproduces only that step and samples the DOM for
three seconds so the failure can be told apart from a 700 ms race.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from browser_runtime import dismiss_editor_onboarding, launch_chromium  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://127.0.0.1:4180"
OUT = Path(__file__).resolve().parent
DOC = {
    "schemaVersion": 13, "eventType": "Wedding",
    "fields": {
        "names": "[Groom name] & [Bride name]", "namesKm": "",
        "date": "2029-12-27", "time": "16:05", "venue": "[Venue]", "venueKm": "",
        "message": "We would be honoured to celebrate with you.", "messageKm": "",
    },
    "settings": {
        "rsvpEnabled": True, "wishesEnabled": False, "scheduleEnabled": True,
        "venueEnabled": True, "galleryEnabled": False, "countdownEnabled": True,
        "musicEnabled": False, "openingEnabled": False, "contactEnabled": False,
    },
    "languageMode": "both", "accent": "#9d4555",
    "palette": {"background": "#fff8f2", "surface": "#ffffff", "text": "#342c26", "heading": "#9d4555"},
    "sectionOrder": [], "schedule": [], "venues": [], "customBlocks": [], "designPages": [],
    "objects": {"title": {"id": "title", "type": "text", "left": "10%", "top": "18%", "width": "80%",
                          "height": "110px", "html": "Probe invitation", "fontSize": 42,
                          "color": "#342c26", "zIndex": 1}},
}

STATE_JS = """() => {
  const pane = document.querySelector('[data-studio-pane="pages"]');
  const manager = document.querySelector('#designPagesManager');
  const cards = [...document.querySelectorAll('#designPagesManager .v22-page-card[data-page-id]')];
  const vis = el => {
    if (!el) return null;
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return {w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y),
            display: cs.display, visibility: cs.visibility, opacity: cs.opacity,
            hidden: el.hasAttribute('hidden'), ariaHidden: el.getAttribute('aria-hidden'),
            inert: 'inert' in el ? el.inert : null};
  };
  const chain = [];
  for (let n = manager; n && n !== document.body; n = n.parentElement) chain.push({tag: n.tagName, id: n.id, cls: n.className, ...vis(n)});
  const paneChain = [];
  for (let n = pane; n && n !== document.body; n = n.parentElement) paneChain.push({tag: n.tagName, id: n.id, cls: n.className, ...vis(n)});
  return {
    body: {classes: document.body.className, drawer: document.body.dataset.editorDrawer,
           layout: document.body.dataset.editorLayout, mode: document.body.dataset.mobileEditorMode},
    paneActive: !!pane && pane.classList.contains('active'),
    pane: vis(pane),
    manager: vis(manager),
    managerScroll: manager ? {sw: manager.scrollWidth, sh: manager.scrollHeight, cw: manager.clientWidth, ch: manager.clientHeight} : null,
    cards: cards.length,
    visibleCards: cards.filter(el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; }).length,
    chain: chain.slice(0, 6),
    paneChain: paneChain.slice(0, 6),
    left: vis(document.querySelector('aside.left')),
    right: vis(document.querySelector('aside.right')),
    panes: [...document.querySelectorAll('[data-studio-pane]')].map(n => ({pane: n.dataset.studioPane, active: n.classList.contains('active')})),
  };
}"""


def main() -> int:
    with sync_playwright() as pw:
        browser = launch_chromium(pw)
        try:
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()
            page.set_default_timeout(30000)
            page.goto(BASE + "/dashboard.html", wait_until="domcontentloaded")
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill(f"round-4-probe-{int(__import__('time').time())}@example.com")
            page.locator("#password").fill("Probe-round-4-123")
            page.locator("#registerConfirmPassword").fill("Probe-round-4-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])")
            row = page.evaluate("""async doc => {
              const r = await fetch('/api/invitations', {method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({slug: 'round-4-probe-' + Date.now(), document: doc})});
              if (!r.ok) throw Error(await r.text());
              return r.json();
            }""", DOC)
            results = {}
            for width, height in ((360, 800), (390, 844), (768, 900)):
                page.set_viewport_size({"width": width, "height": height})
                page.goto(BASE + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded")
                page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'")
                dismiss_editor_onboarding(page)
                if width == 360:
                    page.evaluate("() => window.EInviteCommandRegistry.execute('page.addBlank')")
                    page.wait_for_function("() => window.EInviteEditorBridge.getState().designPages.length === 1")
                    page.wait_for_selector("#designPagesManager .v22-page-card[data-page-id]", state="attached")
                    page.evaluate("() => window.EInviteEditorBridge.save()")
                    page.wait_for_function("() => document.documentElement.dataset.savePending === 'false'")
                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'")
                    dismiss_editor_onboarding(page)
                if width < 820:
                    page.evaluate("() => window.EInviteResponsiveLayout.openCreation()")
                else:
                    page.locator('[data-studio-tab="pages"]').click()
                samples = []
                for _ in range(12):
                    page.wait_for_timeout(250)
                    samples.append(page.evaluate(STATE_JS))
                results[width] = samples
                print(width, json.dumps(samples[-1])[:1200], flush=True)
            (OUT / "probe-pages-mobile.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
            context.close()
        finally:
            browser.close()
    print("PROBE_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
