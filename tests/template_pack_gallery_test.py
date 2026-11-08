#!/usr/bin/env python3
"""TP-1.4: the Khmer events gallery lists the pack, filters it, and creates an invitation.

Runs against the real test server in a real browser: the section mounts on
``templates.html``, the 100 cards render with lazy, sized thumbnails, the filters and
search narrow the list, and choosing a design creates an invitation and lands in
the editor. The pack must stay out of the bundles, so no pack document is requested
until a card is chosen.
"""
from __future__ import annotations

import pytest

from browser_runtime import launch_chromium


def _register(page, base: str) -> None:
    page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
    page.locator("#authRegisterTab").click()
    page.locator("#email").fill("template-pack-gallery@example.com")
    page.locator("#password").fill("Strong-template-pack-123")
    page.locator("#registerConfirmPassword").fill("Strong-template-pack-123")
    page.locator("#loginBtn").click()
    page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)


def test_pack_gallery_lists_filters_and_opens_a_design():
    sync_playwright = pytest.importorskip("playwright.sync_api")
    from v14_test_utils import app_server

    errors: list[str] = []
    with app_server() as (_process, base, _data):
        with sync_playwright.sync_playwright() as play:
            try:
                browser = launch_chromium(play)
            except Exception as exc:  # pragma: no cover - environment dependent
                pytest.skip(f"Chromium unavailable: {exc}")
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            requests: list[str] = []
            page.on("request", lambda request: requests.append(request.url))
            _register(page, base)
            page.goto(base + "/templates.html", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("#templatePackGallery", timeout=20000)
            page.wait_for_selector("#templatePackGallery .pack-card", timeout=20000)

            assert page.locator("#templatePackGallery .pack-card").count() == 100
            assert not [url for url in requests if "/assets/template-pack/built/" in url], requests
            assert page.locator("#packGalleryTitle").inner_text().strip().lower() == "event designs"

            images = page.eval_on_selector_all(
                "#templatePackGallery .pack-card img",
                """nodes => nodes.map(node => ({
                    loading: node.getAttribute('loading'),
                    width: node.getAttribute('width'),
                    height: node.getAttribute('height'),
                    alt: node.getAttribute('alt'),
                    src: node.getAttribute('src'),
                }))""",
            )
            assert len(images) == 100
            for image in images:
                assert image["loading"] == "lazy", image
                assert image["width"] == "420" and image["height"], image
                assert image["alt"] == "", image
                assert image["src"].startswith("/assets/template-pack/thumbs/"), image

            # Bilingual name: the visible name plus the other language line.
            first = page.eval_on_selector(
                "#templatePackGallery .pack-card",
                """card => ({
                    primary: card.querySelector('.pack-name-primary').textContent.trim(),
                    secondary: card.querySelector('.pack-name-secondary').textContent.trim(),
                    meta: card.querySelector('.pack-meta').textContent.trim(),
                    label: card.querySelector('.pack-card-open').getAttribute('aria-label'),
                })""",
            )
            assert first["primary"] and first["secondary"] and first["primary"] != first["secondary"], first
            assert "A5 portrait" in first["meta"] and "2 pages" in first["meta"], first
            assert first["label"].startswith("Use "), first

            # Filters: the studio toolbar owns search and category (PW-7) and the
            # gallery follows it through `einvite:studio-filter`. Wedding is the
            # largest group, Ceremony is seventeen; the counts are the same contract the
            # old per-gallery chips asserted.
            page.select_option("#studioCategory", "wedding")
            page.wait_for_timeout(150)
            wedding = page.locator("#templatePackGallery .pack-card").count()
            assert wedding == 34, wedding
            assert page.locator("#studioCategory").input_value() == "wedding"
            page.select_option("#studioCategory", "ceremony")
            page.wait_for_timeout(150)
            assert page.locator("#templatePackGallery .pack-card").count() == 17
            page.select_option("#studioCategory", "all")
            page.wait_for_timeout(150)
            assert page.locator("#templatePackGallery .pack-card").count() == 100

            # Search narrows the same list.
            page.fill("#studioSearch", "maroon")
            page.wait_for_timeout(150)
            assert page.locator("#templatePackGallery .pack-card").count() == 1
            page.fill("#studioSearch", "")
            page.wait_for_timeout(150)

            # Touch targets at 375 and no horizontal overflow at either width.
            page.set_viewport_size({"width": 375, "height": 812})
            page.wait_for_timeout(150)
            assert page.evaluate("document.documentElement.scrollWidth") <= 375
            small = page.eval_on_selector_all(
                "#templatePackGallery .pack-filter, #templatePackGallery .pack-card-open",
                "nodes => nodes.map(node => node.getBoundingClientRect().height)",
            )
            assert small and min(small) >= 44, min(small)
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.wait_for_timeout(150)
            assert page.evaluate("document.documentElement.scrollWidth") <= 1440

            # Choosing a design creates an invitation and opens its editor.
            page.locator('#templatePackGallery [data-pack-template="wd-royal-maroon-gold"]').click()
            page.wait_for_selector("dialog.ei-dialog[open]", timeout=20000)
            page.locator("dialog.ei-dialog input").fill("Pack gallery smoke")
            page.locator("dialog.ei-dialog [data-confirm]").click()
            page.wait_for_url("**/editor", timeout=30000)
            page.wait_for_function(
                "() => document.documentElement.dataset.editorReady === 'true'",
                timeout=45000,
            )
            state = page.evaluate(
                """() => {
                    const doc = window.EInviteEditorBridge.getState();
                    return {
                        pages: doc.designPages.length,
                        canvas: doc.posterCanvas,
                        firstPageObjects: Object.keys(doc.designPages[0].objects).length,
                        images: [...document.querySelectorAll('#stage img')].map(img => img.getAttribute('src')),
                    };
                }"""
            )
            assert state["pages"] == 2, state
            assert state["canvas"] == {"width": 1000, "height": 1414}, state
            assert state["firstPageObjects"] > 10, state

            page.close()
            browser.close()
    assert not errors, errors
