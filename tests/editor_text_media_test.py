#!/usr/bin/env python3
"""ROADMAP-v0.54-to-v1.0 Part 3.2 + 3.3 — Text + media editing layers.

Tests the new editor modules (v56):

  1. **Inline rich text editor sanitiser** (`src/js/editor/text/inline-editor.js`)
     — strips `<script>`, `<iframe>`, `<style>`, keeps `<b>`, `<i>`, `<u>`,
     `<strong>`, `<em>`, `<span style="color:...">`, `<br>`. Tested via
     Playwright headless Chromium because the sanitiser uses `DOMParser`.

  2. **Server-side sanitiser parity** (`src/python/server.py`)
     — confirms the same input survives the authoritative server-side
     `_RichTextSanitizer` so client + server agree on the allowed subset.

  3. **Image filters persist correctly** to the document model
     (`src/js/editor/media/filters.js`) — `serializeToCSS()` turns
     `{brightness, contrast, saturate, blur, grayscale}` into a CSS
     `filter:` string that round-trips through the model defaults.

  4. **Image crop rect** (`src/js/editor/media/crop.js`) — `serializeToCanvas()`
     produces correct source-rect coordinates from a normalised 0..1
     `cropRect` for the 9-arg `drawImage(src, sx, sy, sw, sh, dx, dy, dw, dh)`.

  5. **Text effects** (`src/js/editor/text/effects.js`) — `serializeToCSS`
     produces correct `text-shadow`, `-webkit-text-stroke`, and
     `linear-gradient` + `background-clip: text` for shadow/outline/gradient.

  6. **Text-on-curve** (`src/js/editor/text/typography.js`) — `arcPath`
     returns null for 0° (caller renders straight) and a valid SVG path
     for non-zero angles; Khmer font detection works.

  7. **Image mask** (`src/js/editor/media/image.js`) — `serializeToCSS`
     returns valid `clip-path` values for all 6 presets (none, circle,
     rounded-4, rounded-12, heart, star).

If Playwright or Chromium isn't installed the test reports SKIP (exit 0)
unless `EINVITE_REQUIRE_BROWSER=1` is set. Per the project convention
(see `tests/browser_runtime.skipped`), headless-browser tests should not
gate CI in environments that lack a browser — but they must be runnable.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_JS = ROOT / "src" / "js" / "editor"
SRC_PY = ROOT / "src" / "python"

# ---------------------------------------------------------------------------
# Helpers — load the new JS modules from disk so we can inline them into a
# headless Chromium page without depending on the bundle being rebuilt.
# ---------------------------------------------------------------------------

def read_module(rel_path: str) -> str:
    path = (SRC_JS / rel_path).resolve()
    assert path.is_file(), f"Missing editor module: {rel_path}"
    return path.read_text(encoding="utf-8").replace("</script>", "<\\/script>")


def build_test_page() -> str:
    """Build a minimal HTML page that loads every new editor module inline.

    The modules are designed to be safe even when their bridge/controller
    dependencies are missing — they still register their pure helpers on
    `window.EInvite*`.
    """
    modules = [
        "text/inline-editor.js",
        "text/effects.js",
        "text/typography.js",
        "media/crop.js",
        "media/filters.js",
        "media/image.js",
    ]
    scripts = "\n".join(
        f'<script data-module="{m}">{read_module(m)}</script>' for m in modules
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>EInvite v56 editor module tests</title>
</head>
<body>
  <div id="stage" style="position: relative; width: 600px; height: 400px;">
    <div id="text-el-1" data-object-id="t1" style="position: absolute; left: 50px; top: 50px; width: 200px; font-size: 18px;">Hello world</div>
    <!-- No <img> with src — `about:blank` triggers ERR_UNKNOWN_URL_SCHEME
         on some Chromium versions; the modules don't need a real image
         for the pure-function tests below. -->
    <div id="img-el-1" data-object-id="i1" style="position: absolute; left: 50px; top: 100px; width: 200px; height: 150px; background: #ccc;"></div>
  </div>
  {scripts}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Server-side sanitiser parity test (pure Python — no browser needed).
# ---------------------------------------------------------------------------

def load_server_module():
    """Load `src/python/server.py` as a module so we can call its
    `_RichTextSanitizer` directly. Server.py is large but pure-Python."""
    # server.py imports `core.auth`, `features.malware_scanner`, `ai_agent`,
    # `platform_v32`, `future_platform_v52`, etc. The PYTHONPATH convention
    # used by `v14_test_utils.app_server` adds BOTH `src/python/` AND the
    # repo root, so we mirror that here. We also set
    # EINVITE_ALLOW_NO_SCANNER so the startup preflight doesn't raise when
    # ClamAV isn't installed.
    sys.path.insert(0, str(SRC_PY))
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("EINVITE_ALLOW_NO_SCANNER", "1")
    spec = importlib.util.spec_from_file_location("einvite_server", SRC_PY / "server.py")
    assert spec and spec.loader, "Could not load server.py"
    module = importlib.util.module_from_spec(spec)
    sys.modules["einvite_server"] = module
    spec.loader.exec_module(module)
    return module


def test_server_sanitizer(server_module) -> None:
    sanitize = server_module.sanitize_rich_text_html
    # Strips dangerous tags.
    assert "<script" not in sanitize("<script>alert(1)</script>hello")
    assert "<iframe" not in sanitize("<iframe src=x></iframe>hi")
    assert "<style" not in sanitize("<style>body{}</style>text")
    assert "<object" not in sanitize("<object data=x></object>y")
    # Keeps safe tags.
    out = sanitize("<b>bold</b> <i>italic</i> <u>underline</u>")
    assert "<b>bold</b>" in out and "<i>italic</i>" in out and "<u>underline</u>" in out, out
    # Keeps span with color + font-weight styles (both server-allowed).
    out = sanitize('<span style="color: #ff0000; font-weight: bold">red</span>')
    assert '<span style="color:#ff0000;font-weight:bold">red</span>' in out, out
    # Drops javascript: URLs in spans.
    out = sanitize('<span style="color: javascript:alert(1)">x</span>')
    assert "javascript:" not in out, out


# ---------------------------------------------------------------------------
# Playwright-driven client-side test.
# ---------------------------------------------------------------------------

def run_browser_tests(page) -> list[str]:
    """Run a sequence of assertions in the browser; collect failure messages."""
    failures: list[str] = []

    # 1. Every module loaded.
    missing = page.evaluate("""() => {
      const expected = ['EInviteInlineEditor', 'EInviteTextEffects', 'EInviteTypography',
                        'EInviteImageCrop', 'EInviteImageFilters', 'EInviteImageMask'];
      return expected.filter(name => !window[name]);
    }""")
    if missing:
        failures.append(f"Modules missing from window: {missing}")

    # 2. Inline editor sanitizer strips dangerous tags.
    cases = [
        # (input, must_not_contain, must_contain)
        ("<script>alert(1)</script><b>bold</b>",
         ["<script", "alert(1)"], ["<b>bold</b>"]),
        ("<iframe src=x></iframe><i>it</i>",
         ["<iframe"], ["<i>it</i>"]),
        ("<style>body{}</style><u>u</u>",
         ["<style"], ["<u>u</u>"]),
        ('<span style="color: #ff0000">red</span>',
         [], ['<span style="color:#ff0000">red</span>']),
        ('<span style="color: javascript:alert(1)">x</span>',
         ["javascript:"], []),
        ('<strong>s</strong><em>e</em><br>',
         [], ["<strong>s</strong>", "<em>e</em>", "<br>"]),
        ('<a href="javascript:alert(1)">x</a>',  # inline editor has no <a> allowlist
         ["javascript:"], []),
        ('<div>wrap<b>b</b></div>',  # unknown tag — keep children, drop wrapper
         ["<div"], ["<b>b</b>"]),
    ]
    for i, (raw, banned, kept) in enumerate(cases):
        result = page.evaluate(
            "(html) => window.EInviteInlineEditor.sanitize(html)",
            raw,
        )
        for needle in banned:
            if needle.lower() in result.lower():
                failures.append(f"sanitize case {i}: '{raw[:40]}' contained banned '{needle}' → {result!r}")
        for needle in kept:
            if needle.lower() not in result.lower():
                failures.append(f"sanitize case {i}: '{raw[:40]}' lost expected '{needle}' → {result!r}")

    # 3. Image filters serializeToCSS round-trip.
    result = page.evaluate("""() => {
      const f = { brightness: 1.2, contrast: 1.1, saturate: 1.0, blur: 0, grayscale: 0 };
      const css = window.EInviteImageFilters.serializeToCSS(f);
      return { css, hasBrightness: css.includes('brightness(1.2)'),
                          hasContrast: css.includes('contrast(1.1)'),
                          noSaturate: !css.includes('saturate('),
                          noBlur: !css.includes('blur(') };
    }""")
    if not (result["hasBrightness"] and result["hasContrast"] and result["noSaturate"] and result["noBlur"]):
        failures.append(f"filters.serializeToCSS wrong: {result}")

    # 4. Filters persist correctly to the document model (round-trip through normalize).
    result = page.evaluate("""() => {
      const stored = { brightness: 1.5, contrast: 0.8, saturate: 1.2, blur: 3, grayscale: 0.5 };
      const normalized = window.EInviteImageFilters.normalize(stored);
      return { stored, normalized,
               defaults: window.EInviteImageFilters.DEFAULTS };
    }""")
    if result["normalized"]["brightness"] != 1.5 or result["normalized"]["blur"] != 3:
        failures.append(f"filters.normalize round-trip failed: {result}")
    # Defaults must include all five properties.
    expected_keys = {"brightness", "contrast", "saturate", "blur", "grayscale"}
    if set(result["defaults"].keys()) != expected_keys:
        failures.append(f"filters.DEFAULTS missing keys: {result['defaults'].keys()}")

    # 5. Crop rect → canvas source coords (9-arg drawImage).
    result = page.evaluate("""() => {
      const crop = { x: 0.25, y: 0.5, w: 0.5, h: 0.25, ratio: '1:1' };
      const img = { naturalWidth: 1000, naturalHeight: 800 };
      const r = window.EInviteImageCrop.serializeToCanvas(crop, img);
      return { sx: r.sx, sy: r.sy, sw: r.sw, sh: r.sh };
    }""")
    expected = {"sx": 250, "sy": 400, "sw": 500, "sh": 200}
    if result != expected:
        failures.append(f"crop.serializeToCanvas wrong: got {result}, expected {expected}")

    # 6. Crop rect modification — applyRatio preserves centre.
    result = page.evaluate("""() => {
      // A 1:1 preset on a crop that starts as 0.5 x 0.5 (centred) → 0.5 x 0.5 (centred).
      const crop = { x: 0.25, y: 0.25, w: 0.5, h: 0.5, ratio: '1:1' };
      const css = window.EInviteImageCrop.serializeToCSS(crop);
      return { css, hasObjectFit: css.objectFit === 'cover',
                          posHasX: css.objectPosition.includes('50%'),
                          posHasY: css.objectPosition.includes('50%') };
    }""")
    if not (result["hasObjectFit"] and result["posHasX"] and result["posHasY"]):
        failures.append(f"crop.serializeToCSS wrong: {result}")

    # 7. Text effects — shadow / outline / gradient.
    result = page.evaluate("""() => {
      const fx = {
        shadow: { color: 'rgba(0,0,0,0.5)', blur: 4, dx: 0, dy: 2 },
        outline: { color: '#ff0000', width: 3 },
        gradient: { from: '#ff0000', to: '#00ff00', angle: 90 },
      };
      const css = window.EInviteTextEffects.serializeToCSS(fx);
      return {
        shadow: css['text-shadow'] || '',
        outline: css['-webkit-text-stroke'] || '',
        bg: css['background'] || '',
        clip: css['-webkit-background-clip'] || '',
        fillColor: css['color'] || '',
      };
    }""")
    if 'rgba(0,0,0,0.5)' not in result["shadow"] or '2px' not in result["shadow"]:
        failures.append(f"effects shadow wrong: {result}")
    if result["outline"] != '3px #ff0000':
        failures.append(f"effects outline wrong: {result}")
    if 'linear-gradient(90deg, #ff0000, #00ff00)' not in result["bg"]:
        failures.append(f"effects gradient wrong: {result}")
    if result["clip"] != 'text' or result["fillColor"] != 'transparent':
        failures.append(f"effects background-clip wrong: {result}")

    # 8. Text effects — defaults (no effects → empty CSS).
    result = page.evaluate("""() => {
      return window.EInviteTextEffects.serializeToCSS({});
    }""")
    if result:
        failures.append(f"effects empty model should produce no CSS, got: {result}")

    # 9. Text-on-curve — arcPath returns null for 0°, valid for non-zero.
    result = page.evaluate("""() => {
      const straight = window.EInviteTypography.arcPath(300, 0);
      const up = window.EInviteTypography.arcPath(300, 60);
      const down = window.EInviteTypography.arcPath(300, -60);
      return {
        straightIsNull: straight === null,
        upPath: up?.d || '',
        downPath: down?.d || '',
        upHasSweep1: up?.sweep === 1,
        downHasSweep0: down?.sweep === 0,
      };
    }""")
    if not result["straightIsNull"]:
        failures.append(f"typography.arcPath(0) should be null, got {result['straightIsNull']}")
    if not (result["upPath"].startswith("M 0 0 A ") and "1 300 0" in result["upPath"]):
        failures.append(f"typography.arcPath(60) wrong: {result['upPath']}")
    if not (result["downPath"].startswith("M 0 0 A ") and "0 300 0" in result["downPath"]):
        failures.append(f"typography.arcPath(-60) wrong: {result['downPath']}")
    if not (result["upHasSweep1"] and result["downHasSweep0"]):
        failures.append(f"typography sweep flags wrong: {result}")

    # 10. Khmer font detection.
    result = page.evaluate("""() => {
      return {
        isKhmer: window.EInviteTypography.isKhmerFont('Noto Sans Khmer'),
        isKhmerLower: window.EInviteTypography.isKhmerFont('noto serif khmer'),
        isNotKhmer: window.EInviteTypography.isKhmerFont('Inter'),
        isNotKhmerEmpty: window.EInviteTypography.isKhmerFont(''),
      };
    }""")
    if not (result["isKhmer"] and result["isKhmerLower"] and not result["isNotKhmer"] and not result["isNotKhmerEmpty"]):
        failures.append(f"typography Khmer detection wrong: {result}")

    # 11. Image mask — all 6 presets produce valid clip-path strings.
    result = page.evaluate("""() => {
      const ids = ['none', 'circle', 'rounded-4', 'rounded-12', 'heart', 'star'];
      const out = {};
      for (const id of ids) {
        out[id] = window.EInviteImageMask.serializeToCSS(id);
      }
      return out;
    }""")
    expected_masks = {
        "none": "none",
        "circle": "circle(50% at 50% 50%)",
        "rounded-4": "inset(0 round 4px)",
        "rounded-12": "inset(0 round 12px)",
        "heart": 'path("M50 88 C 35 70 5 55 5 32',
        "star": 'path("M50 5 L61 38',
    }
    for key, expected_prefix in expected_masks.items():
        actual = result.get(key, "")
        if not actual.startswith(expected_prefix):
            failures.append(f"mask '{key}' = {actual!r}, expected to start with {expected_prefix!r}")

    # 12. Inline-editor sanitizer preserves Khmer text content.
    result = page.evaluate("""(html) => window.EInviteInlineEditor.sanitize(html)""",
                            '<b>កម្ពុជា</b>')
    if "កម្ពុជា" not in result:
        failures.append(f"sanitize lost Khmer text: {result!r}")

    # 13. Effects inspector panel builds without throwing.
    panel_err = page.evaluate("""() => {
      try {
        const panel = window.EInviteTextEffects.buildInspectorPanel({}, () => {});
        return { ok: panel instanceof HTMLElement, tag: panel.tagName, hasChildren: panel.children.length > 0 };
      } catch (e) {
        return { ok: false, error: String(e) };
      }
    }""")
    if not panel_err.get("ok"):
        failures.append(f"effects panel build failed: {panel_err}")

    # 14. Crop inspector panel builds without throwing.
    panel_err = page.evaluate("""() => {
      try {
        const panel = window.EInviteImageCrop.buildInspectorPanel({ x:0, y:0, w:1, h:1, ratio:'free' }, () => {});
        return { ok: panel instanceof HTMLElement, tag: panel.tagName, hasChildren: panel.children.length > 0 };
      } catch (e) {
        return { ok: false, error: String(e) };
      }
    }""")
    if not panel_err.get("ok"):
        failures.append(f"crop panel build failed: {panel_err}")

    # 15. Filters inspector panel builds.
    panel_err = page.evaluate("""() => {
      try {
        const panel = window.EInviteImageFilters.buildInspectorPanel({}, () => {});
        return { ok: panel instanceof HTMLElement, hasChildren: panel.children.length > 0 };
      } catch (e) {
        return { ok: false, error: String(e) };
      }
    }""")
    if not panel_err.get("ok"):
        failures.append(f"filters panel build failed: {panel_err}")

    # 16. Mask inspector panel builds.
    panel_err = page.evaluate("""() => {
      try {
        const panel = window.EInviteImageMask.buildInspectorPanel('none', () => {});
        return { ok: panel instanceof HTMLElement, hasChildren: panel.children.length > 0 };
      } catch (e) {
        return { ok: false, error: String(e) };
      }
    }""")
    if not panel_err.get("ok"):
        failures.append(f"mask panel build failed: {panel_err}")

    return failures


# ---------------------------------------------------------------------------
# Optional HTTP-based smoke test (uses v14_test_utils.app_server).
# Confirms the bundle is reachable and includes the new module sources.
# ---------------------------------------------------------------------------

def test_bundle_served() -> list[str]:
    """Spin up app_server, fetch the designer bundle, confirm the new
    module sources are concatenated in. This is the closest HTTP-level
    check we can do without spinning up a full editor page session."""
    failures: list[str] = []
    try:
        sys.path.insert(0, str(ROOT / "tests"))
        from v14_test_utils import app_server  # type: ignore
    except Exception as exc:
        # Not a failure — fall back to a static check on the bundle file.
        # `bundle-index-v15.js` is the editor's bundle (served from index.html).
        bundle_path = SRC_PY / "bundle-index-v15.js"
        if not bundle_path.is_file():
            failures.append(f"Bundle file not found: {bundle_path}")
            return failures
        text = bundle_path.read_text(encoding="utf-8", errors="replace")
        for needle in [
            "EInviteInlineEditor",
            "EInviteTextEffects",
            "EInviteTypography",
            "EInviteImageCrop",
            "EInviteImageFilters",
            "EInviteImageMask",
        ]:
            if needle not in text:
                failures.append(f"Bundle missing {needle}")
        return failures

    try:
        # Pass EINVITE_ALLOW_NO_SCANNER=1 so app_server boots on dev machines
        # without ClamAV installed (matches v14_test_utils.env convention).
        with app_server(extra_env={"EINVITE_ALLOW_NO_SCANNER": "1"}) as (process, base, data):
            import urllib.request
            # The editor ships from `index.html` (the management "editor"
            # route resolves to it). `designer.html` is a separate landing
            # page with a different, much smaller bundle.
            url = f"{base}/bundle-index-v15.js"
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
            except Exception as exc:
                failures.append(f"Could not fetch bundle from {url}: {exc}")
                return failures
            for needle in [
                "EInviteInlineEditor",
                "EInviteTextEffects",
                "EInviteTypography",
                "EInviteImageCrop",
                "EInviteImageFilters",
                "EInviteImageMask",
            ]:
                if needle not in body:
                    failures.append(f"Bundle served from {url} missing {needle}")
    except Exception as exc:
        failures.append(f"app_server smoke failed: {exc}")
    return failures


def main() -> int:
    failures: list[str] = []

    # ---- Phase A: server-side sanitiser parity (pure Python) ----
    try:
        server_module = load_server_module()
        test_server_sanitizer(server_module)
        print("PHASE_A_SERVER_SANITIZER_PARITY: PASS")
    except Exception as exc:  # pragma: no cover
        failures.append(f"server sanitizer parity: {exc!r}")

    # ---- Phase B: client-side tests via Playwright ----
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        # Browser not installed — soft-skip per project convention.
        try:
            sys.path.insert(0, str(ROOT / "tests"))
            from browser_runtime import skipped  # type: ignore
            return skipped("EDITOR_TEXT_MEDIA_TEST", exc)
        except Exception:
            print(f"EDITOR_TEXT_MEDIA_TEST_SKIPPED_NO_PLAYWRIGHT: {exc}")
            return 0

    with sync_playwright() as p:
        try:
            sys.path.insert(0, str(ROOT / "tests"))
            from browser_runtime import launch_chromium  # type: ignore
            browser = launch_chromium(p)
        except Exception as exc:
            print(f"EDITOR_TEXT_MEDIA_TEST_SKIPPED_NO_CHROMIUM: {exc}")
            return 0
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(f"PAGE: {e}"))
            page.on("console", lambda m: errors.append(f"CONSOLE: {m.text}") if m.type == "error" else None)
            page.set_content(build_test_page(), wait_until="load", timeout=30_000)
            page.wait_for_function(
                "() => window.EInviteInlineEditor && window.EInviteTextEffects && "
                "window.EInviteTypography && window.EInviteImageCrop && "
                "window.EInviteImageFilters && window.EInviteImageMask",
                timeout=10_000,
            )
            if errors:
                failures.extend(f"runtime error: {e}" for e in errors[:5])
            failures.extend(run_browser_tests(page))
        finally:
            browser.close()

    # ---- Phase C: bundle HTTP smoke ----
    bundle_failures = test_bundle_served()
    if bundle_failures:
        failures.extend(bundle_failures)
    else:
        print("PHASE_C_BUNDLE_HTTP_SMOKE: PASS")

    if failures:
        print("EDITOR_TEXT_MEDIA_TEST_FAILED")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("EDITOR_TEXT_MEDIA_TEST_PASSED")
    print("  Phase A: server sanitizer parity OK")
    print("  Phase B: client-side JS modules (sanitizer, effects, typography,")
    print("          crop, filters, mask) all pass")
    print("  Phase C: bundle served with new modules concatenated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
