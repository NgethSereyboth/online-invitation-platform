#!/usr/bin/env python3
"""d1b_popover_flip_test.py — does `@position-try --studio-more-above` actually fire?

History
-------
`docs/reviews/D1b-2026-10-13.md` §9.1 closed the popover-overlaps-left-panel defect but
recorded one honest gap:

    The upward flip is unreachable on this route and is unverified. The trigger lives in
    the topbar, so `@position-try --studio-more-above` never fires on `index.html`; the
    `max-height: min(620px, ...)` clamp is what protects that case in practice. No fixture
    page was built to exercise the flip path.

This module is that fixture. It renders the real placement rules extracted verbatim from
`src/css/canvas-plus.css` (so the fixture cannot drift from the stylesheet) and places the
trigger at the top of the viewport (the editor route's case) and 12px off the bottom edge.

Root cause (found 2026-10-15) — §9.1's stated reason was wrong
--------------------------------------------------------------
The flip never fired, and not because of the topbar. **The menu was `position: absolute`
inside `.canvas-header-more`, a `position: relative` wrapper 42px wide and as tall as the
trigger.** Fallback options are evaluated against the popup's *containing block*, so the
browser was asking whether either placement fitted inside a 42x22 box — and neither did.
Per spec it then correctly reverted to the base position, which left the menu hanging off
the bottom of the viewport.

Measured, viewport 1280x420, trigger 12px off the bottom edge, menu 378px tall:

    containing block = .canvas-header-more (42px)   menu y[412,790]   no flip   (before)
    menu position: fixed (containing block = viewport) menu y[4,382]   flipped   (after)

The fix is one property in the two source stylesheets: `.canvas-header-more-menu` is now
`position: fixed` (`src/css/canvas-plus.css`, `src/css/editor-suite.css`). Horizontal
placement is untouched — it is still `left: anchor(right)`, which is the contract D1b
established — so this closes D1b's own open item without moving the menu sideways.

Hypotheses checked and eliminated
---------------------------------
* **`position-anchor` initial value (`none` -> `normal`, Chrome/Edge 151).** Not the cause:
  this rule sets an explicit `position-anchor: --studio-more-trigger`, and `anchor()`
  resolved correctly throughout (`top` computed to 412 = trigger bottom + 4). The failure
  reproduces with the explicit form on both browsers.
* **Popover UA stylesheet (`inset: 0; margin: auto`).** Not applicable: the menu is not a
  `[popover]` (`<div class="canvas-header-more-menu" hidden>`, `src/html/index.html:86`),
  and `popover` appears 0 times in that page.
* **Missing combined flip tactic.** Not the cause: `flip-block`, `flip-inline`,
  `flip-block flip-inline` and the custom `@position-try` all failed identically while the
  containing block was the 42px wrapper.
* **Renamed properties.** Not the cause: `grep -rn "position-try-options\\|inset-area"
  src/css src/js` excluding bundles → 0 matches. The stylesheet uses the current names.
* **Transition interference.** Not the cause: the fixture declares no transition at all.
* **Menu genuinely taller than the space above.** Eliminated by measurement: a 60px menu
  that fits comfortably above the anchor *also* failed to flip while the containing block
  was the wrapper.

Run:
    .venv/bin/python -m pytest tests/d1b_popover_flip_test.py -v
    .venv/bin/python tests/d1b_popover_flip_test.py            # prints the measurements
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

from browser_runtime import launch_chromium, skipped  # type: ignore  # noqa: E402

CANVAS_PLUS_CSS = REPO / "src" / "css" / "canvas-plus.css"

# Tokens the extracted rules depend on. Values are copied from src/css/tokens.css (lines
# 64-65) and src/css/modern-ui.css (line 2) — the light-mode set, which is what the
# measurement environment renders. They are inlined because the real cascades load per route.
TOKENS = """
:root{
  --space-1:4px; --space-4:16px; --space-16:64px;
  --app-surface:#ffffff; --app-line:#e3e4e9;
  --app-shadow-xl:0 30px 90px rgba(19,20,26,.20);
  --app-muted:#6c707a; --app-text:#20222a;
}
html,body{margin:0;padding:0;font:14px/1.4 system-ui,sans-serif;background:#f4f5f8}
"""

# Enough rows that the menu is substantially taller than any short viewport can host below
# a bottom-anchored trigger — the condition the fallback exists to handle.
MENU_ROWS = "".join(f"<button type='button'>Menu row {i}</button>" for i in range(1, 15))

# Horizontal placement of the fixture trigger. The menu opens at `left: anchor(right)` and is
# 286px wide, so a trigger near the right edge would push the menu past the viewport's inline
# edge. That is a *second, independent* overflow and the fixture must not create it: the
# browser would then be right to revert, because no block-axis flip can cure an inline
# overflow. 420px keeps the menu wholly inside a 1280px viewport (menu right edge ~1146).
HOST_RIGHT_PX = 420


def _extract(rule_start: str) -> str:
    """Pull one single-line CSS rule verbatim out of canvas-plus.css.

    The file stores each of these rules on one line, so a non-greedy match to the first
    `}` is exact. Raising on a miss is deliberate: a renamed selector must fail this test
    loudly rather than render a fixture with no placement rules at all.
    """
    text = CANVAS_PLUS_CSS.read_text(encoding="utf-8")
    match = re.search(re.escape(rule_start) + r"\{[^}]*\}", text)
    if not match:
        raise AssertionError(
            f"{CANVAS_PLUS_CSS.name}: rule {rule_start!r} not found — the D1b placement "
            "rules were renamed, so this fixture no longer tests them"
        )
    return match.group(0)


def popover_rules() -> str:
    """The three real rules that decide where the menu lands."""
    return "\n".join(
        [
            _extract(".canvas-header-more-trigger"),
            _extract(".canvas-header-more-menu"),
            _extract("@position-try --studio-more-above"),
        ]
    )


def build_fixture(anchor_placement: str) -> str:
    """anchor_placement: 'top' (editor route) or 'bottom' (the flip case)."""
    if anchor_placement == "top":
        anchor_css = f"position:fixed; top:12px; right:{HOST_RIGHT_PX}px;"
    elif anchor_placement == "bottom":
        anchor_css = f"position:fixed; bottom:12px; right:{HOST_RIGHT_PX}px;"
    else:
        raise ValueError(anchor_placement)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>D1b popover flip fixture</title>
<style>{TOKENS}{popover_rules()}
/* Fixture-only: place the real trigger at a chosen viewport edge. Nothing else is
   overridden — the menu's own rules above are the production ones, untouched. */
#fixtureHost{{ {anchor_css} }}
</style></head><body>
<div class="canvas-header-more" id="fixtureHost">
  <button id="studioMoreTrigger" class="canvas-header-more-trigger" type="button"
          aria-haspopup="true" aria-expanded="true">•••</button>
  <div id="studioMoreMenu" class="canvas-header-more-menu" role="menu">
    <strong>Menu</strong>{MENU_ROWS}
  </div>
</div>
</body></html>"""


def geometry(page) -> dict:
    return page.evaluate(
        """() => {
            const anchor = document.getElementById('studioMoreTrigger').getBoundingClientRect();
            const menu = document.getElementById('studioMoreMenu').getBoundingClientRect();
            const cs = getComputedStyle(document.getElementById('studioMoreMenu'));
            return {
                anchor: {top: anchor.top, bottom: anchor.bottom, right: anchor.right},
                menu: {top: menu.top, bottom: menu.bottom, height: menu.height, left: menu.left},
                position: cs.position,
                viewport: {w: innerWidth, h: innerHeight},
            };
        }"""
    )


def measure(playwright, html: str, viewport: dict) -> dict:
    """One measurement, on a fresh page.

    Do not reuse a page across measurements: an earlier revision of this fixture did, and
    produced intermittent phantom "flipped" readings. Fresh page per measurement is the
    only protocol that reproduced consistently.
    """
    browser = launch_chromium(playwright)
    try:
        page = browser.new_page(viewport=viewport)
        page.set_content(html, wait_until="load")
        page.wait_for_timeout(150)
        return geometry(page)
    finally:
        browser.close()


def _measure_or_skip(html: str, viewport: dict):
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            return measure(p, html, viewport)
    except Exception as exc:  # noqa: BLE001 — surfaced as a named skip, never a silent pass
        pytest.skip(f"browser unavailable for the D1b fixture: {type(exc).__name__}: {exc}")


def test_menu_is_fixed_positioned() -> None:
    """The regression guard for the fix itself.

    The flip only works while the menu's containing block is the viewport. Reverting this
    to `position: absolute` reintroduces the 42px containing block and silently kills the
    fallback again, so it is asserted directly rather than only through the geometry.
    """
    result = _measure_or_skip(build_fixture("bottom"), {"width": 1280, "height": 420})
    assert result["position"] == "fixed", (
        "the menu must be position:fixed so its containing block is the viewport — "
        f"fallback options cannot fit inside the 42px trigger wrapper: {result}"
    )


def test_menu_opens_downward_when_anchor_is_at_top() -> None:
    """The editor route: a top-of-viewport anchor uses the default placement, not the flip."""
    result = _measure_or_skip(build_fixture("top"), {"width": 1280, "height": 900})
    menu, anchor = result["menu"], result["anchor"]
    assert menu["top"] >= anchor["bottom"] - 1, (
        f"menu should open below a top-of-viewport anchor: {result}"
    )
    assert menu["bottom"] <= result["viewport"]["h"] + 1, (
        f"menu should stay inside the viewport: {result}"
    )
    # D1b's horizontal contract: the menu hangs from the trigger's right edge. Preserved by
    # this fix — the change is vertical only.
    assert abs(menu["left"] - anchor["right"]) <= 1, (
        f"menu left edge should sit on the trigger's right edge: {result}"
    )


def test_menu_flips_upward_when_anchor_is_near_bottom() -> None:
    """The D1b gap: a bottom-anchored trigger must flip above, not hang off the viewport."""
    result = _measure_or_skip(build_fixture("bottom"), {"width": 1280, "height": 420})
    menu, anchor = result["menu"], result["anchor"]
    assert menu["bottom"] <= anchor["top"] + 1, (
        "the upward flip did NOT fire: the menu was not placed above the anchor. "
        f"Check that .canvas-header-more-menu is still position:fixed: {result}"
    )
    assert menu["top"] >= -1, f"flipped menu should still start inside the viewport: {result}"
    assert menu["bottom"] <= result["viewport"]["h"] + 1, (
        f"flipped menu must be fully inside the viewport: {result}"
    )
    assert abs(menu["left"] - anchor["right"]) <= 1, (
        f"flip must not move the menu sideways (D1b contract): {result}"
    )


def _script() -> int:
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            for label, placement, vh in (
                ("anchor at TOP   ", "top", 900),
                ("anchor at BOTTOM", "bottom", 420),
            ):
                g = measure(p, build_fixture(placement), {"width": 1280, "height": vh})
                print(
                    f"{label} vh={g['viewport']['h']:4d} pos={g['position']:7s} "
                    f"anchor y[{g['anchor']['top']:.0f},{g['anchor']['bottom']:.0f}] "
                    f"menu x[{g['menu']['left']:.0f}] y[{g['menu']['top']:.0f},{g['menu']['bottom']:.0f}] "
                    f"flipped_up={g['menu']['bottom'] <= g['anchor']['top'] + 1}"
                )
    except Exception as exc:  # noqa: BLE001
        return skipped("D1B_FLIP", exc)
    return 0


if __name__ == "__main__":
    sys.exit(_script())
