#!/usr/bin/env python3
"""TP-5.2 — public-page proof for one template per category.

For each category it creates a throw-away invitation on the test server
(``v14_test_utils.app_server``, temporary data only), publishes it, and opens the
public page at 375 km / 375 en / 1440 km. It records:

* horizontal overflow (``documentElement.scrollWidth`` vs the viewport)
* clipped text objects (``scrollHeight/scrollWidth`` vs client)
* ornament sharpness (rendered CSS width vs the image's natural width)
* CSP violations and console errors
* the CSP response header on the document itself

Usage: .venv/bin/python tools/proof-public-page.py
Output: artifacts/next-work/review-tp/public-proof.json and shots in review-tp/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from browser_runtime import launch_chromium  # noqa: E402
from v14_test_utils import app_server  # noqa: E402
from template_pack_edit_export_test import built_document  # noqa: E402

OUT = ROOT / "artifacts" / "next-work" / "review-tp"
SAMPLE = {
    "wedding": "wd-royal-maroon-gold",
    "birthday": "bd-first-pastel",
    "ceremony": "merit-dana",
    "greeting": "gr-khmer-new-year",
    "business": "biz-grand-opening",
}

MEASURE_JS = """
() => {
  const root = document.documentElement;
  const objects = [...document.querySelectorAll('.published-object')];
  // The guest page renders text as .published-text, with .typography-flow inside it;
  // there is no .content here (that class is the editor canvas).
  const texts = objects.filter(node => node.classList.contains('published-text'));
  const clipped = texts.filter(node => {
    const content = node.querySelector('.typography-flow') || node;
    return content.scrollHeight > content.clientHeight + 1 || content.scrollWidth > content.clientWidth + 1;
  }).map(node => node.getAttribute('data-object-id'));
  const spilled = texts.filter(node => {
    const content = node.querySelector('.typography-flow') || node;
    const box = node.getBoundingClientRect(), inner = content.getBoundingClientRect();
    return inner.bottom > box.bottom + 1 || inner.right > box.right + 1 || inner.top < box.top - 1;
  }).map(node => node.getAttribute('data-object-id'));
  const images = [...document.images].map(image => {
    const src = image.currentSrc || image.src;
    return {
      src: src.split('/').pop(),
      natural: image.naturalWidth,
      rendered: Math.round(image.getBoundingClientRect().width),
      svg: /\.svg(\?|$)/i.test(src),
    };
  });
  return {
    scrollWidth: root.scrollWidth,
    innerWidth: window.innerWidth,
    objects: objects.length,
    texts: texts.length,
    clipped,
    spilled,
    images,
    hiddenImages: images.filter(i => i.natural === 0).length,
    // SVG ornaments scale without blur; only a raster smaller than its box is soft.
    blurryImages: images.filter(i => !i.svg && i.natural > 0 && i.rendered > 0 && i.natural < i.rendered * 0.75).length,
    svgImages: images.filter(i => i.svg).length,
    lang: document.documentElement.lang || null,
    guestLanguage: document.querySelector('.guest')?.getAttribute('data-language') || null,
  };
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    results = []
    with app_server() as (_process, base, _data):
        with sync_playwright() as play:
            browser = launch_chromium(play)
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("public-proof@example.com")
            page.locator("#password").fill("Strong-public-proof-123")
            page.locator("#registerConfirmPassword").fill("Strong-public-proof-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)
            console: list[str] = []
            console_hooked = False

            for category, template_id in SAMPLE.items():
                document = built_document(template_id)
                created = page.evaluate(
                    """async model => {
                        const csrf = decodeURIComponent((document.cookie.match(/(?:^|;\\s*)einvite_csrf=([^;]+)/) || [])[1] || '');
                        const response = await fetch('/api/invitations', {
                            method: 'POST', credentials: 'same-origin',
                            headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
                            body: JSON.stringify({slug: model.templateId, document: model}),
                        });
                        if (!response.ok) throw Error(await response.text());
                        return response.json();
                    }""",
                    document,
                )
                published = page.evaluate(
                    """async ([id, model]) => {
                        const csrf = decodeURIComponent((document.cookie.match(/(?:^|;\\s*)einvite_csrf=([^;]+)/) || [])[1] || '');
                        const response = await fetch('/api/invitations/' + id + '/publish', {
                            method: 'POST', credentials: 'same-origin',
                            headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
                            body: JSON.stringify({document: model, expectedRevision: null}),
                        });
                        const body = await response.json().catch(() => ({}));
                        return {ok: response.ok, status: response.status, body};
                    }""",
                    [created["id"], document],
                )
                row = {"category": category, "id": template_id, "published": published["ok"], "views": {}}
                if not published["ok"]:
                    row["error"] = published
                    results.append(row)
                    continue
                url = base + published["body"]["url"] if published["body"]["url"].startswith("/") else published["body"]["url"]

                console: list[str] = []
                if not console_hooked:
                    page.on("console", lambda message: console.append(message.text) if message.type == "error" else None)
                    console_hooked = True
                for width, lang in ((375, "km"), (375, "en"), (1440, "km")):
                    page.set_viewport_size({"width": width, "height": 900})
                    console.clear()
                    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    headers = response.headers if response else {}
                    # The saved guest language persists across reloads, so each view asks
                    # for its own. The in-page toggle is visually hidden behind a topbar
                    # proxy, so a synthetic click is the supported drive (see
                    # tests/v12_browser_stabilization_test.py:114). Its handlers attach
                    # after load; a click before that is a no-op, so wait for them first.
                    # The static html has lang="en"; the guest script applies the saved
                    # language after load, so wait for that decision before comparing.
                    for _ in range(50):
                        if page.evaluate("() => document.querySelector('.guest')?.dataset.language"):
                            break
                        page.wait_for_timeout(100)
                    if page.evaluate("() => document.documentElement.lang") != lang:
                        for _ in range(60):
                            if page.evaluate(
                                f"() => typeof document.querySelector('[data-guest-lang=\"{lang}\"]')?.onclick === 'function'"
                            ):
                                break
                            page.wait_for_timeout(100)
                        page.evaluate(
                            f"() => document.querySelector('[data-guest-lang=\"{lang}\"]')?.click()"
                        )
                        # CSP forbids string predicates (`unsafe-eval`), so poll instead.
                        for _ in range(40):
                            if page.evaluate("() => document.documentElement.lang") == lang:
                                break
                            page.wait_for_timeout(100)
                    page.wait_for_timeout(250)
                    metrics = page.evaluate(MEASURE_JS)
                    metrics["cspHeader"] = "content-security-policy" in {key.lower() for key in headers}
                    metrics["consoleErrors"] = [text for text in console if "Content Security Policy" in text][:3]
                    metrics["consoleErrorCount"] = len(console)
                    metrics["cspClean"] = bool(metrics["cspHeader"]) and not metrics["consoleErrors"]
                    shot = OUT / f"public-{category}-{width}-{lang}.png"
                    page.screenshot(path=str(shot), full_page=False, timeout=20000)
                    metrics["shot"] = shot.name
                    row["views"][f"{width}-{lang}"] = metrics
                results.append(row)
                print(f"{category}: {template_id} ok={published['ok']}", flush=True)

            browser.close()

    (OUT / "public-proof.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    failures = [
        (row["category"], view, key)
        for row in results
        for view, metrics in (row.get("views") or {}).items()
        for key in (("overflow",) if metrics.get("scrollWidth") != metrics.get("innerWidth") else ())
    ]
    csp_failures = [
        (row["category"], view)
        for row in results
        for view, metrics in (row.get("views") or {}).items()
        if not metrics.get("cspClean")
    ]
    print(f"WROTE {OUT / 'public-proof.json'} ({len(results)} categories); overflow={failures}")
    print(f"CSP_CHECK_{'PASSED' if not csp_failures and not failures else 'FAILED'}")
    return 0 if not failures and not csp_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
