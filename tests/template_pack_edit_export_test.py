#!/usr/bin/env python3
"""TP-1.6: the flagship pack template opens, edits and exports in the real editor.

``wd-royal-maroon-gold`` is the template every later batch check copies, so this
test drives it end to end: both pages present at the pack canvas, an English and a
Khmer text edit (the Khmer string is read out of the copy bank, never typed here),
a nudge, a colour change through the inspector, a new page, undo/redo, and a PNG
1x export. The PDF path is exercised by opening the print surface with
``window.print`` stubbed (a headless browser has no print dialog).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from browser_runtime import launch_chromium

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = "wd-royal-maroon-gold"


def built_document(template_id: str = TEMPLATE) -> dict:
    text = (ROOT / "assets" / "template-pack" / "built" / f"{template_id}.js").read_text(encoding="utf-8")
    return json.loads(text[len("export default "):].rstrip().rstrip(";"))["document"]


def khmer_sample() -> str:
    """A Khmer string from the pack's copy bank (the repo never types Khmer)."""
    bank = json.loads((ROOT / "template-pack" / "copy-bank.json").read_text(encoding="utf-8"))["copy"]
    for entry in bank.values():
        value = str(entry.get("km") or "")
        if len(value) > 12 and value.strip().startswith("[") is False:
            return value
    raise AssertionError("the copy bank has no usable Khmer string")


def open_editor(page, base: str, document: dict) -> None:
    created = page.evaluate(
        """async documentModel => {
            const response = await fetch('/api/invitations', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({slug: documentModel.templateId, document: documentModel})
            });
            if (!response.ok) throw Error(await response.text());
            return response.json();
        }""",
        document,
    )
    page.goto(f"{base}/invitations/{created['id']}/editor", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_function(
        "() => document.documentElement.dataset.editorReady === 'true'", timeout=45000
    )
    page.evaluate(
        """() => {
            document.querySelector('#finalTourDismiss')?.click();
            document.querySelectorAll('dialog.final-tour[open]').forEach(d => d.close());
        }"""
    )
    page.wait_for_timeout(200)


def open_page(page, page_id: str) -> None:
    card = f'.v22-page-card[data-page-id="{page_id}"]'
    try:
        page.wait_for_selector(card, timeout=8000)
    except Exception:
        page.evaluate("() => window.EInviteCommandRegistry?.execute?.('workspace.pages')")
        page.wait_for_selector(card, timeout=15000)
    page.locator(f'{card} [data-page-thumb-id]').click()
    page.wait_for_function(
        "token => window.EInviteEditorBridge.getActiveCanvasId() === 'page:' + token"
        " && document.querySelectorAll('#stage .object').length > 0",
        arg=page_id,
        timeout=20000,
    )


def exported_width(svg: str, object_id: str) -> int | None:
    """The px width baked onto an object in an exported SVG (TP-3 A8 guard)."""
    import re

    marker = svg.find(f'data-id="{object_id}"')
    if marker < 0:
        return None
    start = svg.find(' style="', marker)
    if start < 0:
        return None
    end = svg.find('"', start + len(' style="'))
    match = re.search(r"width:(\d+(?:\.\d+)?)px", svg[start:end])
    return int(float(match.group(1))) if match else None


def test_flagship_template_opens_edits_and_exports(tmp_path):
    sync_playwright = pytest.importorskip("playwright.sync_api")
    from v14_test_utils import app_server

    document = built_document()
    pages = [page["id"] for page in document["designPages"]]
    khmer = khmer_sample()
    errors: list[str] = []
    with app_server() as (_process, base, _data):
        with sync_playwright.sync_playwright() as play:
            try:
                browser = launch_chromium(play)
            except Exception as exc:  # pragma: no cover - environment dependent
                pytest.skip(f"Chromium unavailable: {exc}")
            context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("pack-edit-export@example.com")
            page.locator("#password").fill("Strong-pack-edit-123")
            page.locator("#registerConfirmPassword").fill("Strong-pack-edit-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)

            open_editor(page, base, document)

            state = page.evaluate(
                """() => {
                    const doc = window.EInviteEditorBridge.getState();
                    return {pages: doc.designPages.map(p => p.id), canvas: doc.posterCanvas,
                            stage: document.querySelector('#stage').dataset.posterSize};
                }"""
            )
            assert state["pages"] == pages, state
            assert state["canvas"] == {"width": 1000, "height": 1414}
            assert state["stage"] == "1000x1414", state

            open_page(page, pages[0])
            first = page.evaluate(
                """() => {
                    const objects = [...document.querySelectorAll('#stage .object')];
                    const texts = objects.filter(o => o.querySelector('.content'));
                    return {
                        objects: objects.length,
                        texts: texts.length,
                        overflowing: texts.filter(o => {
                            const c = o.querySelector('.content');
                            return c.scrollHeight > c.clientHeight + 1 || c.scrollWidth > c.clientWidth + 1;
                        }).length,
                    };
                }"""
            )
            assert first["objects"] > 20, first
            assert first["texts"] >= 6, first

            # Colours: every canvas paragraph must render in its object colour,
            # never the muted app-chrome colour (regression guard for TP-2.1).
            colours = page.evaluate(
                """() => [...document.querySelectorAll('#stage .object')]
                    .filter(o => o.querySelector('.rt-paragraph'))
                    .map(o => {
                        const run = o.querySelector('.rt-run');
                        const hex = (getComputedStyle(run || o.querySelector('.content')).color.match(/\\d+/g) || [])
                            .slice(0, 3).map(n => Number(n).toString(16).padStart(2, '0')).join('');
                        return { hex, wanted: String(o.dataset.color || '').replace('#', '').toLowerCase() };
                    })"""
            )
            assert colours, "no rich-text paragraphs on the canvas"
            wrong = [row for row in colours if row["hex"] != row["wanted"]]
            assert wrong == [], wrong

            # A8: the SVG (and therefore the PNG) keeps every object's own
            # geometry. Regression guard for a style-snapshot offset that
            # stretched the pattern tiles over the whole canvas and gave the
            # frame's box to the corner ornaments.
            page.evaluate("() => window.EInviteCommandRegistry.execute('quality.open')")
            page.wait_for_selector('[data-tab="export"]', timeout=15000)
            page.locator('[data-tab="export"]').click()
            with page.expect_download(timeout=30000) as svg_info:
                page.locator("[data-export-svg]").click()
            svg_target = tmp_path / svg_info.value.suggested_filename
            svg_info.value.save_as(svg_target)
            svg = svg_target.read_text(encoding="utf-8")
            widths = page.evaluate(
                """() => Object.fromEntries([...document.querySelectorAll('#stage .object')]
                    .map(el => [el.dataset.id, Math.round(el.getBoundingClientRect().width
                        / document.querySelector('#stage').getBoundingClientRect().width * 1000)]))"""
            )
            for object_id in (
                "wd-royal-maroon-gold-p1-pattern-02-0-0",
                "wd-royal-maroon-gold-p1-svg-03",
                "wd-royal-maroon-gold-p1-svg-04",
            ):
                baked = exported_width(svg, object_id)
                assert baked is not None, object_id
                assert abs(baked - widths[object_id]) <= 2, (object_id, baked, widths[object_id])
            assert exported_width(svg, "wd-royal-maroon-gold-p1-pattern-02-0-0") < 400
            assert exported_width(svg, "wd-royal-maroon-gold-p1-svg-04") < 400
            page.evaluate("() => document.querySelector('#v24QualityDialog')?.close()")


            # English edit: double-click a text object, select all, type.
            english = page.locator("#stage .object .content").nth(3)
            english.scroll_into_view_if_needed()
            english.dblclick()
            page.keyboard.press("Control+a")
            page.keyboard.insert_text("Maria & Dara")
            page.keyboard.press("Escape")
            page.wait_for_timeout(250)

            # Khmer edit: the string comes from the copy bank, and the target is the
            # first text object that actually holds Khmer.
            km_index = page.evaluate(
                """() => {
                    const nodes = [...document.querySelectorAll('#stage .object .content')];
                    return nodes.findIndex(node => /[\\u1780-\\u17ff]/.test(node.textContent || ''));
                }"""
            )
            assert km_index >= 0, "no Khmer text object on the page"
            khmer_node = page.locator("#stage .object .content").nth(km_index)
            khmer_node.scroll_into_view_if_needed()
            khmer_node.dblclick()
            page.keyboard.press("Control+a")
            page.keyboard.insert_text(khmer)
            page.keyboard.press("Escape")
            page.wait_for_timeout(250)
            edited = page.evaluate(
                """(sample) => {
                    const doc = window.EInviteEditorBridge.getState();
                    const objects = Object.values(doc.designPages.find(p => 
                        'page:' + p.id === window.EInviteEditorBridge.getActiveCanvasId()).objects);
                    return {
                        khmer: objects.some(o => String(o.text || '').includes(sample)),
                        english: objects.some(o => String(o.text || '') === 'Maria & Dara'),
                    };
                }""",
                khmer.strip(),
            )
            assert edited["english"], "the English edit did not reach the document"
            assert edited["khmer"], "the Khmer edit did not reach the document"

            # Nudge a layer with the keyboard and change a text colour in the inspector.
            # Select the English text object (the topmost object at its own centre;
            # the page background is under an ornament, so clicking it would miss).
            page.locator("#stage .object .content").nth(3).click()
            before_left = page.evaluate("() => window.EInviteEditorBridge.getSelectedIds() && document.querySelector('#stage .object.selected')?.style.left")
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(120)
            after_left = page.evaluate("() => document.querySelector('#stage .object.selected')?.style.left")
            assert before_left != after_left, (before_left, after_left)

            page.locator("#color").evaluate(
                """(input) => { input.value = '#123456'; input.dispatchEvent(new Event('input', {bubbles: true})); }"""
            )
            page.wait_for_timeout(150)
            colour = page.evaluate(
                """() => {
                    const doc = window.EInviteEditorBridge.getState();
                    const page = doc.designPages.find(p => 'page:' + p.id === window.EInviteEditorBridge.getActiveCanvasId());
                    return Object.values(page.objects).some(o => String(o.color || '').toLowerCase() === '#123456');
                }"""
            )
            assert colour, "the inspector colour change did not reach the document"

            # A new page, then undo and redo it.
            page.evaluate("() => window.EInviteCommandRegistry.execute('page.addBlank')")
            page.wait_for_function(
                "() => window.EInviteEditorBridge.getState().designPages.length === 3", timeout=10000
            )
            page.evaluate("() => window.EInviteCommandRegistry.execute('history.undo')")
            page.wait_for_function(
                "() => window.EInviteEditorBridge.getState().designPages.length === 2", timeout=10000
            )
            page.evaluate("() => window.EInviteCommandRegistry.execute('history.redo')")
            page.wait_for_function(
                "() => window.EInviteEditorBridge.getState().designPages.length === 3", timeout=10000
            )
            page.evaluate("() => window.EInviteCommandRegistry.execute('history.undo')")
            page.wait_for_function(
                "() => window.EInviteEditorBridge.getState().designPages.length === 2", timeout=10000
            )

            # Export the current card as PNG 1x through the export panel (the
            # quality dialog opens on its check tab; export lives on the second).
            page.evaluate("() => window.EInviteCommandRegistry.execute('quality.open')")
            page.wait_for_selector('[data-tab="export"]', timeout=15000)
            page.locator('[data-tab="export"]').click()
            page.wait_for_selector('[data-export-png="1"]', timeout=15000)
            with page.expect_download(timeout=30000) as download_info:
                page.locator('[data-export-png="1"]').click()
            download = download_info.value
            target = tmp_path / download.suggested_filename
            download.save_as(target)
            assert target.stat().st_size > 20_000, target.stat().st_size

            # PDF: the current page opens in a print window that holds one sized
            # page image and calls print() itself.
            with page.expect_popup(timeout=30000) as popup_info:
                page.locator("[data-print]").click()
            printed = popup_info.value
            printed.wait_for_selector("img", timeout=20000)
            surface = printed.evaluate(
                """() => ({
                    images: document.querySelectorAll('img').length,
                    sized: [...document.querySelectorAll('img')].every(img => img.naturalWidth > 0 || img.src.startsWith('data:image/svg+xml')),
                    pageRule: [...document.querySelectorAll('style')].some(s => (s.textContent || '').includes('@page')),
                })"""
            )
            assert surface["images"] == 1 and surface["sized"] and surface["pageRule"], surface
            printed.close()

            page.close()
            context.close()
            browser.close()
    assert not errors, errors
