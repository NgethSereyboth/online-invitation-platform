#!/usr/bin/env python3
"""Round-6 sweep of the published Freebuff origin at all six contract widths.

Derived from bugs/round-4/live_sweep.py. Records console/page errors, failed
requests, non-2xx responses, horizontal overflow, right-edge crossings, clipped
text, unlabelled controls, unnamed buttons, small tap targets and Khmer text
presence. Live has no published invitation (every /i/<slug> is 404) and the
editor/dashboard are auth-gated, so those states are exercised against the
byte-identical local bundle by bugs/round-4/flow_sweep.py and recorded here as
signed-out redirects.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
from browser_runtime import launch_chromium  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = os.environ.get("ROUND6_BASE", "https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page").rstrip("/")
OUT = Path(__file__).resolve().parent
SHOTS = OUT / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)
VIEWPORTS = [(360, 800), (390, 844), (768, 900), (1024, 900), (1280, 900), (1440, 900)]
ROUTES = [
    "/", "/privacy", "/templates", "/public", "/verify", "/reset", "/billing",
    "/admin", "/dashboard", "/designer", "/guests", "/responses", "/analytics",
    "/materials", "/checkin", "/account",
    "/i/missing-slug-round-6", "/missing-route-round-6",
    "/invitations/00000000-0000-0000-0000-000000000000/editor",
]

AUDIT = r"""() => {
  const vis = (el) => {
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    return cs.display !== 'none' && cs.visibility !== 'hidden' && Number(cs.opacity || 1) > 0.05 && r.width > 0 && r.height > 0;
  };
  const name = (el) => (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.') : '');
  const rightEdge = [];
  for (const el of document.querySelectorAll('header, main, section, article, footer, nav, button, a, input, select, textarea, table, img, h1, h2')) {
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.right > innerWidth + 1 && r.left < innerWidth) rightEdge.push({ el: name(el), tag: el.tagName, right: Math.round(r.right) });
    if (rightEdge.length >= 12) break;
  }
  const clipped = [];
  for (const el of document.querySelectorAll('h1, h2, h3, p, span, strong, small, label, button, a')) {
    if (!vis(el) || !el.textContent.trim()) continue;
    const cs = getComputedStyle(el);
    if (el.scrollWidth > el.clientWidth + 2 && ['hidden', 'clip'].includes(cs.overflowX)) {
      clipped.push({ el: name(el), tag: el.tagName, text: el.textContent.trim().slice(0, 60), scroll: el.scrollWidth, client: el.clientWidth });
    }
    if (clipped.length >= 12) break;
  }
  const unlabelled = [];
  for (const el of document.querySelectorAll('input:not([type=hidden]), select, textarea')) {
    if (!vis(el) || el.disabled) continue;
    const id = el.id;
    const label = id ? document.querySelector(`label[for="${CSS.escape(id)}"]`) : null;
    const wrapped = el.closest('label');
    const named = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.getAttribute('title') || el.getAttribute('placeholder');
    if (!label && !wrapped && !named) unlabelled.push({ el: name(el), type: el.type || el.tagName });
  }
  const unnamed = [];
  for (const el of document.querySelectorAll('button, a')) {
    if (!vis(el)) continue;
    const text = (el.textContent || '').trim();
    const named = el.getAttribute('aria-label') || el.getAttribute('title') || (el.querySelector('img') && el.querySelector('img').alt);
    if (!text && !named) unnamed.push({ el: name(el), tag: el.tagName });
  }
  const images = [...document.querySelectorAll('img')].filter(vis);
  const smallTargets = [];
  for (const el of document.querySelectorAll('button, a, input, select, textarea')) {
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 24 || r.height < 24) smallTargets.push({ el: name(el), w: Math.round(r.width), h: Math.round(r.height) });
  }
  const doc = document.documentElement;
  const text = (document.body?.innerText || '');
  return {
    title: document.title,
    lang: doc.lang || '',
    overflowX: Math.max(0, doc.scrollWidth - doc.clientWidth),
    scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth,
    docHeight: doc.scrollHeight,
    rightEdge, clipped, unlabelled, unnamed,
    imgs: images.length, imgsNoAlt: images.filter((i) => !i.hasAttribute('alt')).length,
    smallTargets: smallTargets.slice(0, 12),
    h1: [...document.querySelectorAll('h1')].filter(vis).map((h) => h.textContent.trim().slice(0, 80)).slice(0, 4),
    khmer: /[\u1780-\u17ff]/.test(text),
  };
}"""


def slug(route: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", route.lower()).strip("-") or "root"


def main() -> int:
    records = []
    with sync_playwright() as play:
        browser = launch_chromium(play)
        for width, height in VIEWPORTS:
            context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
            for route in ROUTES:
                page = context.new_page()
                console, errors, failed, bad = [], [], [], []
                page.on("console", lambda msg: console.append({"type": msg.type, "text": msg.text[:300]}))
                page.on("pageerror", lambda err: errors.append(str(err)[:300]))
                page.on("requestfailed", lambda req: failed.append({"url": req.url[:180], "why": (req.failure or "")[:120]}))
                page.on("response", lambda res: bad.append({"url": res.url[:180], "status": res.status}) if res.status >= 400 else None)
                status, url = None, None
                try:
                    res = page.goto(BASE + route, wait_until="load", timeout=30000)
                    status = res.status if res else None
                    page.wait_for_timeout(1200)
                    url = page.url
                    audit = page.evaluate(AUDIT)
                except Exception as exc:  # a navigation failure is a finding
                    audit = {"error": str(exc)[:300]}
                path = SHOTS / f"live-{slug(route)}-{width}.png"
                try:
                    page.screenshot(path=str(path), full_page=True)
                except Exception as exc:
                    audit["screenshot_error"] = str(exc)[:200]
                records.append({
                    "route": route, "width": width, "height": height,
                    "status": status, "final_url": url, "shot": str(path.relative_to(OUT)),
                    "console_errors": [m for m in console if m["type"] == "error"],
                    "console_warnings": [m for m in console if m["type"] == "warning"][:10],
                    "page_errors": errors, "request_failed": failed, "http_errors": bad,
                    "audit": audit,
                })
                page.close()
                print(f"{width:>4} {route:<58} status={status}", flush=True)
                time.sleep(0.2)
            context.close()
        browser.close()

    (OUT / "live-sweep.json").write_text(json.dumps(records, indent=1), encoding="utf-8")
    hits = []
    for r in records:
        a = r.get("audit", {})
        if r["console_errors"] or r["page_errors"] or r["request_failed"] or r["http_errors"]:
            hits.append((r["route"], r["width"], "console/network", len(r["console_errors"]), len(r["page_errors"]), len(r["request_failed"]), len(r["http_errors"])))
        if a.get("error"):
            hits.append((r["route"], r["width"], "navigation", a["error"]))
        if a.get("overflowX", 0) > 1:
            hits.append((r["route"], r["width"], "overflow", a["overflowX"]))
        for key in ("rightEdge", "clipped", "unlabelled", "unnamed"):
            if a.get(key):
                hits.append((r["route"], r["width"], key, len(a[key])))
        if a.get("imgsNoAlt"):
            hits.append((r["route"], r["width"], "imgsNoAlt", a["imgsNoAlt"]))
        if r["width"] <= 390 and a.get("smallTargets"):
            hits.append((r["route"], r["width"], "smallTargets", len(a["smallTargets"])))
    print(f"\nSWEEP_RECORDS={len(records)}")
    for hit in hits:
        print("HIT", *hit)
    print(f"SWEEP_HITS={len(hits)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
