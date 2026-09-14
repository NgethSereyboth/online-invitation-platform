#!/usr/bin/env python3
"""Served-browser coverage for the compact, non-overlapping editor controls."""
from __future__ import annotations

from browser_runtime import dismiss_editor_onboarding, launch_chromium, skipped
from v14_test_utils import app_server


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return skipped("V0_52_EDITOR_INTERACTION_REFINEMENT_BROWSER", exc)

    with app_server() as (_process, base, _data):
        with sync_playwright() as runtime:
            try:
                browser = launch_chromium(runtime)
            except Exception as exc:
                return skipped("V0_52_EDITOR_INTERACTION_REFINEMENT_BROWSER", exc)

            page = browser.new_page(viewport={"width": 1366, "height": 768})
            page.set_default_timeout(20_000)
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(f"PAGE:{error}"))
            page.on("console", lambda message: errors.append(f"CONSOLE:{message.text}") if message.type == "error" else None)
            page.on("dialog", lambda dialog: dialog.accept())

            page.goto(base + "/dashboard.html", wait_until="networkidle", timeout=30_000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("ux-refinement@example.com")
            page.locator("#password").fill("Strong-ux-refinement-123")
            page.locator("#registerConfirmPassword").fill("Strong-ux-refinement-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])")
            create = page.locator(".dashboard-home-hero .create")
            if not create.is_visible():
                create = page.locator("#emptyCreate")
            create.click()
            page.wait_for_selector("#createDialog[open]")
            page.locator("#newTitle").fill("Editor interaction refinement")
            page.locator("#confirmCreate").click()
            page.wait_for_url("**/invitations/*/editor")
            page.wait_for_selector('#stage .object[data-id="title"]')
            page.wait_for_function("()=>document.documentElement.dataset.editorReady==='true'")
            page.wait_for_function("()=>window.EInviteDirectManipulation?.version>=24.2")
            dismiss_editor_onboarding(page, timeout=20_000)
            errors.clear()

            title = page.locator('#stage .object[data-id="title"]')
            title.click()
            page.wait_for_timeout(250)
            toolbar_state = page.evaluate("""()=>{
              const bar=document.querySelector('#v20TypographyToolbar');
              return {visible:!!bar&&!bar.hidden,collapsed:bar?.classList.contains('collapsed'),
                inline:document.querySelectorAll('.v24-inline-toolbar').length,
                rich:document.querySelectorAll('.ei-rich-toolbar').length,
                quick:getComputedStyle(document.querySelector('#workflowQuickStrip')).display};
            """)
            assert toolbar_state == {"visible": True, "collapsed": True, "inline": 0, "rich": 0, "quick": "none"}, toolbar_state

            page.locator("#v20ToolbarToggle").click()
            assert not page.locator("#v20TypographyToolbar").evaluate("node=>node.classList.contains('collapsed')")
            page.locator("#v20ToolbarToggle").click()
            assert page.locator("#v20TypographyToolbar").evaluate("node=>node.classList.contains('collapsed')")

            title.dblclick()
            page.wait_for_timeout(180)
            inline_state = page.evaluate("""()=>({
              editable:document.querySelector('#stage .object[data-id="title"] .content')?.getAttribute('contenteditable'),
              inlineToolbar:document.querySelectorAll('.v24-inline-toolbar:not([hidden])').length,
              richToolbar:document.querySelectorAll('.ei-rich-toolbar.visible').length
            })""")
            assert inline_state == {"editable": "true", "inlineToolbar": 0, "richToolbar": 0}, inline_state
            page.keyboard.press("Control+Enter")

            page_more = page.locator(".workflow-page-chip[data-page-id] .workflow-page-more").first
            if page_more.count():
                page_more.click()
                page.wait_for_selector("#workflowV4PageMenu.open")
                collision = page.evaluate("""()=>{const menu=document.querySelector('#workflowV4PageMenu').getBoundingClientRect(),dock=document.querySelector('#workflowPageDock').getBoundingClientRect();return {separate:menu.bottom<=dock.top||menu.top>=dock.bottom,inViewport:menu.left>=0&&menu.top>=0&&menu.right<=innerWidth&&menu.bottom<=innerHeight,menu:{top:menu.top,bottom:menu.bottom},dock:{top:dock.top,bottom:dock.bottom}}}""")
                assert collision["separate"] and collision["inViewport"], collision
                page.keyboard.press("Escape")

            theme = page.locator(".ui-theme-button")
            theme.click()
            theme_state = page.evaluate("""()=>{const menu=document.querySelector('.ui-theme-menu'),r=menu.getBoundingClientRect();return {modes:[...menu.querySelectorAll('[data-mode]')].map(x=>x.dataset.mode),width:r.width,inViewport:r.left>=0&&r.right<=innerWidth}}""")
            assert theme_state["modes"] == ["light", "dark"], theme_state
            assert theme_state["width"] <= 130 and theme_state["inViewport"], theme_state
            page.locator('.ui-theme-menu [data-mode="dark"]').click()
            assert page.evaluate("()=>document.documentElement.dataset.theme") == "dark"

            rail_state = page.evaluate("""()=>({labels:[...document.querySelectorAll('.studio-nav-label')].every(label=>{const a=label.getBoundingClientRect(),b=label.closest('button').getBoundingClientRect();return a.left>=b.left-1&&a.right<=b.right+1}),shortcuts:[...document.querySelectorAll('.ei-tool-rail button>span')].every(x=>getComputedStyle(x).display==='none')})""")
            assert rail_state == {"labels": True, "shortcuts": True}, rail_state

            page.goto(base + "/account.html", wait_until="networkidle")
            page.wait_for_selector("#accountAppearance")
            assert page.locator("#accountAppearance [data-account-theme]").count() == 2
            assert not errors, errors
            browser.close()

    print("V0_52_EDITOR_INTERACTION_REFINEMENT_BROWSER_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
