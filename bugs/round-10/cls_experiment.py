#!/usr/bin/env python3
"""A/B the CLS contribution of the transient #studioGrid loading block.

Injects CSS into the /templates response only; source files are untouched.
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
INIT = r"""
window.__cls = 0; window.__n = 0;
new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) { window.__cls += e.value; window.__n++; } })
  .observe({ type: 'layout-shift', buffered: true });
"""
VARIANTS = {
    "baseline": "",
    "hide-loading": ".template-loading{visibility:hidden}",
    "no-loading": ".template-loading{display:none}",
}


def main() -> int:
    out = {}
    with sync_playwright() as play:
        browser = launch_chromium(play)
        for width, height in ((390, 844), (1440, 900)):
            for name, css in VARIANTS.items():
                ctx = browser.new_context(viewport={"width": width, "height": height})
                page = ctx.new_page()
                page.add_init_script(INIT)
                if css:
                    def fulfill(route, css=css):
                        resp = route.fetch()
                        body = resp.text()
                        body = body.replace("</head>", f"<style>{css}</style></head>", 1)
                        route.fulfill(response=resp, body=body)
                    page.route(BASE + "/templates", fulfill)
                page.goto(BASE + "/templates", wait_until="load", timeout=60000)
                page.wait_for_timeout(4000)
                out[f"{width}:{name}"] = {
                    "cls": round(page.evaluate("() => window.__cls"), 4),
                    "shifts": page.evaluate("() => window.__n"),
                }
                ctx.close()
        browser.close()
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
