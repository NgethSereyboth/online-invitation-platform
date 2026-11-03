#!/usr/bin/env python3
"""Measure cumulative layout shift and LCP on the routes that still carry an
open performance defect (D-1 templates CLS, D-2 guest LCP).

Runs against the local authoritative origin. Read-only: no writes.
"""
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
GUEST = os.environ.get("CLS_GUEST", "qa-ui-sweep-wedding")
ROUTES = [("templates", "/templates"), ("guest", f"/i/{GUEST}")]
VIEWPORTS = [(390, 844), (1440, 900)]

INIT = r"""
window.__perf = { cls: 0, shifts: [], lcp: 0, lcpEl: '' };
new PerformanceObserver((list) => {
  for (const e of list.getEntries()) {
    if (!e.hadRecentInput) {
      window.__perf.cls += e.value;
      window.__perf.shifts.push({ value: +e.value.toFixed(4), t: Math.round(e.startTime),
        nodes: (e.sources || []).map(s => s.node ? (s.node.id ? '#' + s.node.id : s.node.tagName + '.' + (s.node.className || '').toString().split(' ')[0]) : '?').slice(0, 3) });
    }
  }
}).observe({ type: 'layout-shift', buffered: true });
new PerformanceObserver((list) => {
  const e = list.getEntries().at(-1);
  if (e) { window.__perf.lcp = Math.round(e.startTime); window.__perf.lcpEl = e.element ? (e.element.id || e.element.tagName) : ''; }
}).observe({ type: 'largest-contentful-paint', buffered: true });
"""


def main() -> int:
    report = []
    with sync_playwright() as play:
        browser = launch_chromium(play)
        for name, route in ROUTES:
            for width, height in VIEWPORTS:
                ctx = browser.new_context(viewport={"width": width, "height": height})
                page = ctx.new_page()
                page.add_init_script(INIT)
                resp = page.goto(BASE + route, wait_until="load", timeout=60000)
                page.wait_for_timeout(5000)
                perf = page.evaluate("() => window.__perf")
                doc = page.evaluate("() => ({h: document.documentElement.scrollHeight, w: document.documentElement.scrollWidth})")
                report.append({"route": name, "path": route, "width": width, "status": resp.status if resp else None,
                               "cls": round(perf["cls"], 4), "lcp": perf["lcp"], "lcpEl": perf["lcpEl"],
                               "shifts": perf["shifts"][:8], "docHeight": doc["h"]})
                ctx.close()
        browser.close()
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
