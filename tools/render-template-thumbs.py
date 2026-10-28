#!/usr/bin/env python3
"""Render the 36 template-pack thumbnails in the real editor (TP-1.4).

For each built template the script creates a throwaway invitation on the test
server, opens its editor, switches to the first design page, and captures the
artboard. The capture is downscaled to 420 px wide and written as a WebP under
``assets/template-pack/thumbs/`` (the catalogue already points there).

Constraints from the work order: one thumbnail <= 40 KB, the set <= 1.5 MB.
Intermediate PNGs stay in ``artifacts/next-work/template-thumbs/`` (git-ignored);
only the WebPs are product assets.

Usage:
    .venv/bin/python tools/render-template-thumbs.py                # all 36
    .venv/bin/python tools/render-template-thumbs.py --only wd-royal-maroon-gold
    .venv/bin/python tools/render-template-thumbs.py --base http://127.0.0.1:8124  # reuse a server
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

OUT = ROOT / "assets" / "template-pack" / "thumbs"
EVIDENCE = ROOT / "artifacts" / "next-work" / "template-thumbs"
BUILT = ROOT / "assets" / "template-pack" / "built"
THUMB_WIDTH = 420
MAX_BYTES = 40 * 1024
MAX_TOTAL = 1_500_000
ZOOM = 0.6


def load_built(template_id: str) -> dict:
    text = (BUILT / f"{template_id}.js").read_text(encoding="utf-8")
    return json.loads(text[len("export default "):].rstrip().rstrip(";"))


def built_ids() -> list[str]:
    return sorted(path.stem for path in BUILT.glob("*.js"))


def encode_webp(png_bytes: bytes) -> bytes:
    from PIL import Image

    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    if image.width != THUMB_WIDTH:
        height = max(1, round(THUMB_WIDTH * image.height / image.width))
        image = image.resize((THUMB_WIDTH, height), Image.LANCZOS)
    for quality in (86, 80, 74, 68, 60, 52, 44):
        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", quality=quality, method=6)
        data = buffer.getvalue()
        if len(data) <= MAX_BYTES:
            return data
    raise RuntimeError(f"cannot reach {MAX_BYTES} bytes (best {len(data)})")


def register(page, base: str, email: str) -> None:
    page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
    page.locator("#authRegisterTab").click()
    page.locator("#email").fill(email)
    page.locator("#password").fill("Strong-template-thumbs-123")
    page.locator("#registerConfirmPassword").fill("Strong-template-thumbs-123")
    page.locator("#loginBtn").click()
    page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)


def create_invitation(page, payload: dict) -> str:
    created = page.evaluate(
        """async (documentModel) => {
            const response = await fetch('/api/invitations', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({slug: documentModel.templateId, document: documentModel.document})
            });
            if (!response.ok) throw Error(await response.text());
            return response.json();
        }""",
        payload,
    )
    return created["id"]


def capture(page, base: str, invitation_id: str, page_id: str) -> bytes:
    page.goto(f"{base}/invitations/{invitation_id}/editor", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_function(
        "() => document.documentElement.dataset.editorReady === 'true'"
        " && !!document.querySelector('#stage')",
        timeout=45000,
    )
    # First open in this context shows the studio tour; it would cover the artboard.
    page.evaluate(
        """() => {
            const dismiss = document.querySelector('#finalTourDismiss');
            if (dismiss) dismiss.click();
            document.querySelectorAll('dialog.final-tour[open]').forEach((dialog) => dialog.close());
        }"""
    )
    page.wait_for_timeout(120)

    # The editor opens on the hero canvas; the pack's design lives on page 1.
    # The pages pane is rendered by the v22 page manager, whose thumbnail button
    # calls activateCanvas(`page:<id>`). It renders asynchronously, so wait for the
    # card and open the Pages pane through the command registry if it is late.
    card_selector = f'.v22-page-card[data-page-id="{page_id}"]'
    try:
        page.wait_for_selector(card_selector, timeout=8000)
    except Exception:
        page.evaluate("() => window.EInviteCommandRegistry?.execute?.('workspace.pages')")
        page.wait_for_selector(card_selector, timeout=15000)
    opened = page.evaluate(
        """(cardSelector) => {
            const card = document.querySelector(cardSelector);
            const button = card && card.querySelector('[data-page-thumb-id]');
            if (!button) return false;
            button.click();
            return true;
        }""",
        card_selector,
    )
    if not opened:
        raise RuntimeError(f"page {page_id} has no navigator button")
    page.wait_for_function(
        """(token) => {
            const bridge = window.EInviteEditorBridge;
            if (!bridge || bridge.getActiveCanvasId() !== 'page:' + token) return false;
            return document.querySelectorAll('#stage .object').length > 0;
        }""",
        arg=page_id,
        timeout=20000,
    )
    page.evaluate(
        """(zoom) => {
            const view = window.EInviteCanvasViewController;
            if (view && view.setZoom) view.setZoom(zoom, {source: 'thumbnail'});
        }""",
        arg=ZOOM,
    )
    # Page switches animate (opacity/transform). Screenshot after the canvas has
    # settled, or a thumbnail catches the fade mid-flight and looks washed out.
    page.wait_for_timeout(900)
    page.evaluate("async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))); }")
    page.wait_for_timeout(350)
    return page.locator("#stage").screenshot(timeout=30000)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render template-pack thumbnails in the editor.")
    parser.add_argument("--only", action="append", default=[], help="template id (repeatable)")
    parser.add_argument("--base", default="", help="reuse a running server at this base URL")
    parser.add_argument("--keep-png", action="store_true", default=True)
    parser.add_argument("--update-assets", action="store_true", help="rewrite the thumbnail hash table in docs/ASSETS.md")
    args = parser.parse_args(argv)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is required", file=sys.stderr)
        return 1

    ids = args.only or built_ids()
    OUT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    def run(browser, base: str, email: str) -> int:
        page = browser.new_page(viewport={"width": 1500, "height": 1700}, device_scale_factor=1)
        page.on("pageerror", lambda error: print(f"PAGEERROR {error}", file=sys.stderr))
        register(page, base, email)
        failures = 0
        for template_id in ids:
            payload = load_built(template_id)
            first_page = payload["document"]["designPages"][0]["id"]
            try:
                invitation_id = create_invitation(page, payload)
                png = capture(page, base, invitation_id, first_page)
                (EVIDENCE / f"{template_id}.png").write_bytes(png)
                webp = encode_webp(png)
                (OUT / f"{template_id}.webp").write_bytes(webp)
                print(f"THUMB {template_id} {len(webp)} bytes")
            except Exception as error:  # keep going: one bad template must not stop 35
                failures += 1
                print(f"THUMB_FAILED {template_id}: {error}", file=sys.stderr)
        page.close()
        return failures

    if args.base:
        with sync_playwright() as play:
            browser = play.chromium.launch()
            failures = run(browser, args.base, "template-thumbs@example.com")
            browser.close()
    else:
        from v14_test_utils import app_server

        with app_server() as (_process, base, _data):
            with sync_playwright() as play:
                browser = play.chromium.launch()
                failures = run(browser, base, "template-thumbs@example.com")
                browser.close()

    if args.update_assets:
        import hashlib
        assets = ROOT / "docs" / "ASSETS.md"
        text = assets.read_text(encoding="utf-8")
        start = text.index("## Gallery thumbnails (36)")
        marker = "| `%s`"
        table_start = text.index("|---|---|---|", start) + len("|---|---|---|")
        table_end = text.index("\n\n", table_start)
        lines = []
        for path in sorted(OUT.glob("*.webp")):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"| `{path.name}` | {path.stat().st_size} | `{digest}` |")
        assets.write_text(text[:table_start] + "\n" + "\n".join(lines) + text[table_end:], encoding="utf-8")
        print(f"ASSETS_UPDATED {len(lines)} thumbnail rows")

    total = sum(path.stat().st_size for path in OUT.glob("*.webp"))
    count = len(list(OUT.glob("*.webp")))
    print(f"TEMPLATE_THUMBS files={count} total={total}")
    if total > MAX_TOTAL:
        print(f"TEMPLATE_THUMBS_OVER_BUDGET {total} > {MAX_TOTAL}", file=sys.stderr)
        failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
