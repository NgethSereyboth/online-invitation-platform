#!/usr/bin/env python3
"""Geometry checks for the responsive editor shell at common device widths."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from browser_runtime import launch_chromium

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "tests" / "inline_editor_runtime_test.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("inline_runtime_builder", RUNTIME)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_inline_editor


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f"EDITOR_LAYOUT_GEOMETRY_SKIPPED_NO_PLAYWRIGHT: {exc}")
        return 0

    html = load_builder()()
    viewports = [(360, 800), (390, 844), (430, 900), (820, 900), (1024, 768), (1180, 800), (1181, 800), (1280, 800), (1440, 900), (1920, 900)]

    with sync_playwright() as p:
        try:
            browser = launch_chromium(p)
        except Exception as exc:
            print(f"EDITOR_LAYOUT_GEOMETRY_SKIPPED_NO_CHROMIUM: {exc}")
            return 0

        for width, height in viewports:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.set_content(html, wait_until="load", timeout=30_000)
            page.wait_for_timeout(1_200)
            if page.locator("#finalTourDismiss").count() and page.locator("#finalTourDismiss").is_visible():
                page.locator("#finalTourDismiss").click()
                page.wait_for_timeout(60)

            geometry = page.evaluate(
                """()=>{const rect=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};return{
                  scrollWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,header:rect('.studio-topbar'),main:rect('main'),left:rect('.left'),stage:rect('.stage-wrap'),inspector:rect('aside.right'),
                  toolbar:rect('.stage-wrap .studio-canvas-toolbar'),canvasViewport:rect('#canvasViewport'),canvasFrame:rect('#canvasFrame'),statusbar:rect('.studio-statusbar'),statusDisplay:getComputedStyle(document.querySelector('.studio-statusbar')).display,
                  leftResizer:rect('.studio-panel-resizer.l'),rightResizer:rect('.studio-panel-resizer.r'),
                  leftResizerDisplay:document.querySelector('.studio-panel-resizer.l')?getComputedStyle(document.querySelector('.studio-panel-resizer.l')).display:'missing',
                  rightResizerDisplay:document.querySelector('.studio-panel-resizer.r')?getComputedStyle(document.querySelector('.studio-panel-resizer.r')).display:'missing',
                  rightResizerPointer:document.querySelector('.studio-panel-resizer.r')?getComputedStyle(document.querySelector('.studio-panel-resizer.r')).pointerEvents:'missing',
                  visibleInspectorControl:(()=>{const e=[...document.querySelectorAll('aside.right input,aside.right select,aside.right textarea,aside.right button')].find(n=>{const r=n.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(n).visibility!=='hidden'});if(!e)return null;const r=e.getBoundingClientRect(),hit=document.elementFromPoint(r.left+Math.min(8,r.width/2),r.top+Math.min(8,r.height/2));return{tag:e.tagName,hitClass:hit?.className||'',hitIsResizer:!!hit?.closest?.('.studio-panel-resizer')}})(),
                  headerScroll:document.querySelector('.studio-topbar').scrollWidth,headerClient:document.querySelector('.studio-topbar').clientWidth,
                  headerChildren:[...document.querySelector('.studio-topbar').children].filter(e=>getComputedStyle(e).display!=='none').map(e=>{const r=e.getBoundingClientRect();return{top:r.top,bottom:r.bottom,left:r.left,right:r.right}})
                }}"""
            )
            assert not errors, (width, height, errors[:5])
            assert geometry["scrollWidth"] <= width + 1, (width, height, geometry)
            assert geometry["headerScroll"] <= geometry["headerClient"] + 1, (width, height, geometry)
            assert all(child["top"] >= geometry["header"]["y"] - 1 and child["bottom"] <= geometry["header"]["bottom"] + 1 for child in geometry["headerChildren"]), (width, height, geometry)
            assert geometry["main"]["h"] > height * 0.72, (width, height, geometry)
            assert geometry["main"]["y"] >= geometry["header"]["bottom"] - 1, geometry
            assert geometry["stage"]["w"] > 0 and geometry["stage"]["h"] > 0
            assert geometry["toolbar"]["h"] <= 60, (width, height, geometry)
            assert geometry["toolbar"]["w"] <= geometry["stage"]["w"] + 1, (width, height, geometry)
            assert geometry["canvasViewport"]["y"] >= geometry["toolbar"]["bottom"] - 1, (width, height, geometry)
            assert geometry["canvasFrame"]["y"] >= geometry["canvasViewport"]["y"] - 1, (width, height, geometry)

            if width <= 1180:
                assert geometry["leftResizerDisplay"] == "none", (width, height, geometry)
                assert geometry["rightResizerDisplay"] == "none", (width, height, geometry)
                assert geometry["rightResizerPointer"] == "none", (width, height, geometry)
            else:
                assert geometry["leftResizerDisplay"] != "none", (width, height, geometry)
                assert geometry["rightResizerDisplay"] != "none", (width, height, geometry)

            if width > 1180:
                # True non-overlapping three-column desktop shell.
                assert abs(geometry["left"]["right"] - geometry["stage"]["x"]) < 1.5, geometry
                assert abs(geometry["stage"]["right"] - geometry["inspector"]["x"]) < 1.5, geometry
                assert abs((geometry["leftResizer"]["x"] + geometry["leftResizer"]["w"] / 2) - geometry["left"]["right"]) <= 1, geometry
                assert abs((geometry["rightResizer"]["x"] + geometry["rightResizer"]["w"] / 2) - geometry["inspector"]["x"]) <= 1, geometry
                assert geometry["visibleInspectorControl"] and not geometry["visibleInspectorControl"]["hitIsResizer"], geometry
                assert geometry["left"]["w"] >= 300, geometry
                assert geometry["stage"]["w"] >= 480, geometry
                assert geometry["inspector"]["w"] >= 300, geometry
            elif width > 820:
                # Compact workspace: persistent rail, stage offset by the rail, drawers closed.
                assert abs(geometry["left"]["x"]) < 1 and abs(geometry["left"]["w"] - 66) < 2, geometry
                assert abs(geometry["stage"]["x"] - 66) < 2, geometry
                assert abs(geometry["stage"]["right"] - width) < 2, geometry
                assert geometry["inspector"]["x"] >= width - 1, geometry
                assert geometry["statusDisplay"] == "none", (width, height, geometry)
            else:
                # Mobile drawer model: full-width stage and completely off-canvas closed drawers.
                assert abs(geometry["stage"]["x"]) < 1 and abs(geometry["stage"]["w"] - width) < 1.5, geometry
                assert geometry["left"]["right"] <= 1, geometry
                assert geometry["inspector"]["x"] >= width - 1, geometry
                assert geometry["statusDisplay"] == "none", (width, height, geometry)
                assert geometry["canvasFrame"]["right"] > 24, geometry
                assert geometry["canvasFrame"]["x"] < width - 24, geometry
                frame_center = geometry["canvasFrame"]["x"] + geometry["canvasFrame"]["w"] / 2
                assert abs(frame_center - width / 2) <= 18, geometry
            page.close()
        browser.close()

    print("EDITOR_LAYOUT_GEOMETRY_TEST_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
