#!/usr/bin/env python3
"""Post-fix check for BUG-R10-1: skeletons hydrate to 36 real cards."""
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
OUT = ROOT / "bugs" / "round-10" / "shots"
OUT.mkdir(parents=True, exist_ok=True)
results = []


def main() -> int:
    with sync_playwright() as play:
        browser = launch_chromium(play)
        for width, height in ((390, 844), (1440, 900)):
            ctx = browser.new_context(viewport={"width": width, "height": height})
            page = ctx.new_page()
            errors, failed = [], []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("requestfailed", lambda r: failed.append(r.url))
            page.on("response", lambda r: failed.append(f"{r.status} {r.url}") if r.status >= 400 and "missing" not in r.url else None)
            page.goto(BASE + "/templates", wait_until="load", timeout=60000)
            page.wait_for_selector(".pack-card[role='listitem']", timeout=20000)
            page.wait_for_timeout(1500)
            data = page.evaluate("""() => ({
              cards: document.querySelectorAll('.pack-card[role="listitem"]').length,
              skeletons: document.querySelectorAll('.pack-skeleton-card').length,
              busy: document.querySelector('[data-pack-grid]').getAttribute('aria-busy'),
              count: document.querySelector('[data-pack-count]').textContent,
              gridTop: Math.round(document.querySelector('#studioGrid').getBoundingClientRect().top + scrollY),
              galleryH: Math.round(document.querySelector('#templatePackGallery').getBoundingClientRect().height),
              hOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
            })""")
            page.screenshot(path=str(OUT / f"templates-fixed-{width}.png"), full_page=False)
            # Khmer language switch must keep the hydrated cards.
            page.eval_on_selector("#langKm", "el => el.click()") if page.query_selector("#langKm") else None
            page.wait_for_timeout(700)
            data["kmCards"] = page.evaluate("() => document.querySelectorAll('.pack-card[role=\"listitem\"]').length")
            data["kmSkeletons"] = page.evaluate("() => document.querySelectorAll('.pack-skeleton-card').length")
            page.screenshot(path=str(OUT / f"templates-fixed-km-{width}.png"), full_page=False)
            data.update({"width": width, "console": errors[:5], "failed": failed[:5]})
            results.append(data)
            ctx.close()
        browser.close()
    print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
