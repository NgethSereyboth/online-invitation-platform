#!/usr/bin/env python3
"""Live desktop/mobile regression for uncluttered editor chrome and account layout."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_runtime import launch_chromium, skipped
from v14_test_utils import app_server


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return skipped("V0_52_FINAL_UX_REFINEMENT", exc)

    with app_server() as (_process, base, _data):
        with sync_playwright() as pw:
            try:
                browser = launch_chromium(pw)
            except Exception as exc:
                return skipped("V0_52_FINAL_UX_REFINEMENT", exc)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "console",
                lambda message: errors.append(message.text)
                if message.type == "error"
                and "favicon" not in message.text.lower()
                and "failed to load resource" not in message.text.lower()
                else None,
            )
            page.add_init_script("localStorage.setItem('einvite-final-tour-seen-v1','1')")
            page.goto(base + "/", wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_selector("#stage", timeout=20_000)
            page.wait_for_function("()=>window.EInviteWorkspaceExperience&&document.querySelector('.v24-footer-tools')", timeout=20_000)

            desktop = page.evaluate("""()=>{
 const header=document.querySelector('.studio-topbar'),tabs=document.querySelector('.studio-inspector-tabs'),footer=document.querySelector('.studio-statusbar');
 const ys=[...header.children].filter(e=>e.getBoundingClientRect().width&&getComputedStyle(e).display!=='none').map(e=>Math.round(e.getBoundingClientRect().y));
 return{headerHeight:header.getBoundingClientRect().height,headerSpread:Math.max(...ys)-Math.min(...ys),tabsOverflow:tabs.scrollWidth-tabs.clientWidth,footerOverflow:footer.scrollWidth-footer.clientWidth,documentOverflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,emptyVisible:!!document.querySelector('.v24-inspector-empty')&&!document.querySelector('.v24-inspector-empty').hidden};
}""")
            assert desktop["headerHeight"] <= 60 and desktop["headerSpread"] <= 10, desktop
            assert desktop["tabsOverflow"] <= 1 and desktop["footerOverflow"] <= 1 and desktop["documentOverflow"] <= 1, desktop
            assert desktop["emptyVisible"], desktop

            first_count = page.locator("#v23ContextToolbar button").count()
            page.wait_for_timeout(700)
            second_count = page.locator("#v23ContextToolbar button").count()
            assert first_count == second_count and second_count <= 10, (first_count, second_count)

            page.locator('#stage .object[data-id="title"]').click()
            page.wait_for_timeout(120)
            assert page.locator("body.v24-has-selection").count() == 1
            page.locator("[data-v24-inspector-toggle]").click()
            assert page.locator('[data-inspector-pane="object"]>.v24-advanced-control').evaluate_all("els=>els.filter(e=>getComputedStyle(e).display!=='none').length") > 0
            page.locator("[data-v24-inspector-toggle]").click()

            page.locator(".canvas-header-more-trigger").click()
            assert page.locator(".canvas-header-more-menu").is_visible()
            assert page.locator(".canvas-header-more-menu #eiAdvancedStudio").count() == 1
            page.locator(".canvas-header-more-trigger").click()
            page.locator(".v24-footer-tools-trigger").click()
            assert page.locator(".v24-footer-tools-menu").is_visible()
            assert page.locator(".v24-footer-tools-menu button").count() >= 10
            page.locator(".v24-footer-tools-trigger").click()

            page.set_viewport_size({"width": 390, "height": 844})
            page.reload(wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_selector("#stage", timeout=20_000)
            page.wait_for_function("()=>window.EInviteWorkspaceExperience&&document.querySelector('#mobileToolsMode')", timeout=20_000)
            page.wait_for_timeout(500)
            mobile = page.evaluate("""()=>({
 documentOverflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
 canvasOverflow:document.querySelector('#canvasViewport').scrollWidth-document.querySelector('#canvasViewport').clientWidth,
 toolbarDisplay:getComputedStyle(document.querySelector('.studio-canvas-toolbar')).display,
 zoom:document.querySelector('.v24-zoom-value')?.textContent
})""")
            assert mobile["documentOverflow"] <= 1 and mobile["canvasOverflow"] <= 1, mobile
            assert mobile["toolbarDisplay"] == "none" and mobile["zoom"] != "100%", mobile
            page.locator("#mobileToolsMode").click()
            page.wait_for_function("()=>document.querySelector('aside.left').getBoundingClientRect().left>=-1", timeout=2_000)
            drawer = page.evaluate("""()=>{const left=document.querySelector('aside.left').getBoundingClientRect(),rail=document.querySelector('.studio-tool-rail').getBoundingClientRect(),pane=document.querySelector('.studio-pane-host').getBoundingClientRect();return{left:[left.x,left.y,left.right,left.bottom],rail:[rail.x,rail.y,rail.right,rail.bottom],pane:[pane.x,pane.y,pane.right,pane.bottom],text:document.querySelector('.studio-pane.active').innerText.trim().slice(0,80)}}""")
            assert drawer["left"][0] >= -1 and drawer["left"][2] <= 391, drawer
            assert drawer["rail"][2] <= drawer["pane"][0] + 1 and drawer["pane"][2] <= 391, drawer
            assert drawer["pane"][1] < 70 and drawer["text"], drawer
            page.locator("#mobileCanvasMode").click()

            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_selector("#loginView,#dashboardView", timeout=15_000)
            if page.locator("#loginView:not([hidden])").count():
                email = f"final-ux-{int(time.time() * 1000)}@example.test"
                password = "Strong-final-ux-123"
                page.locator("#authRegisterTab").click()
                page.locator("#email").fill(email)
                page.locator("#password").fill(password)
                page.locator("#registerConfirmPassword").fill(password)
                page.locator("#loginBtn").click()
                page.wait_for_selector("#dashboardView:not([hidden])", timeout=15_000)
            page.goto(base + "/account.html", wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_selector(".account-grid", timeout=15_000)
            account = page.evaluate("""()=>({overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,columns:getComputedStyle(document.querySelector('.account-grid')).gridTemplateColumns,children:[...document.querySelector('.account-grid').children].map(e=>{const r=e.getBoundingClientRect();return{left:r.left,right:r.right,width:r.width}})})""")
            assert account["overflow"] <= 1, account
            assert all(item["left"] >= -1 and item["right"] <= 391 for item in account["children"]), account
            assert not errors, errors
            context.close()
            browser.close()

    print("V0_52_FINAL_UX_REFINEMENT_BROWSER_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
