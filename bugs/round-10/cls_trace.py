#!/usr/bin/env python3
"""Trace what moves on /templates so the CLS fix targets the cause."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from browser_runtime import launch_chromium  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = os.environ.get("CLS_BASE", "http://127.0.0.1:4175").rstrip("/")

INIT = r"""
window.__trace = { muts: [], frames: [], shifts: [] };
const t0 = performance.now();
const label = (n) => {
  if (!n || n.nodeType !== 1) return String(n && n.nodeName || '?');
  return n.tagName.toLowerCase() + (n.id ? '#' + n.id : '') + (n.className && typeof n.className === 'string' ? '.' + n.className.trim().split(/\s+/).join('.') : '');
};
function sample() {
  const q = (s) => document.querySelector(s);
  const rect = (el) => el ? { top: Math.round(el.getBoundingClientRect().top + scrollY), h: Math.round(el.getBoundingClientRect().height) } : null;
  window.__trace.frames.push({
    t: Math.round(performance.now()),
    gallery: rect(q('#templatePackGallery')),
    grid: rect(q('#studioGrid')),
    loading: rect(q('.template-loading')),
    packGrid: rect(q('.pack-grid')),
    doc: Math.round(document.documentElement.scrollHeight),
  });
  if (performance.now() - t0 < 3000) requestAnimationFrame(sample);
}
requestAnimationFrame(sample);
new MutationObserver((list) => {
  for (const m of list) {
    const added = [...m.addedNodes].map(label).slice(0, 4);
    const removed = [...m.removedNodes].map(label).slice(0, 4);
    if (!added.length && !removed.length) continue;
    window.__trace.muts.push({ t: Math.round(performance.now()), target: label(m.target), added, removed });
  }
}).observe(document.documentElement, { childList: true, subtree: true });
new PerformanceObserver((list) => {
  for (const e of list.getEntries()) {
    if (e.hadRecentInput) continue;
    window.__trace.shifts.push({ t: Math.round(e.startTime), value: +e.value.toFixed(4),
      sources: (e.sources || []).map(s => s.node ? { el: label(s.node), prev: s.previousRect && { x: Math.round(s.previousRect.x), y: Math.round(s.previousRect.y), w: Math.round(s.previousRect.width), h: Math.round(s.previousRect.height) }, cur: s.currentRect && { x: Math.round(s.currentRect.x), y: Math.round(s.currentRect.y), w: Math.round(s.currentRect.width), h: Math.round(s.currentRect.height) } } : null).filter(Boolean) });
  }
}).observe({ type: 'layout-shift', buffered: true });
"""


def main() -> int:
    with sync_playwright() as play:
        browser = launch_chromium(play)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.add_init_script(INIT)
        page.goto(BASE + "/templates", wait_until="load", timeout=60000)
        page.wait_for_timeout(3500)
        trace = page.evaluate("() => window.__trace")
        ctx.close()
        browser.close()

    frames = trace["frames"]
    # Print only frames where a tracked geometry changed, plus nearby mutations.
    changes = []
    prev = None
    for f in frames:
        key = json.dumps({k: f[k] for k in ("gallery", "grid", "loading", "packGrid", "doc")}, sort_keys=True)
        if key != prev:
            changes.append(f)
            prev = key
    print("SHIFTS")
    print(json.dumps(trace["shifts"], indent=1))
    print("GEOMETRY CHANGES (first 30)")
    print(json.dumps(changes[:30], indent=1))
    print("MUTATIONS (gallery/grid only)")
    print(json.dumps([m for m in trace["muts"] if any("#templatePackGallery" in x or "#studioGrid" in x or "pack-grid" in x or "template-loading" in x or ".empty" in x for x in m["added"] + m["removed"] + [m["target"]])][:20], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
