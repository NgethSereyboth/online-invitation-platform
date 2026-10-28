#!/usr/bin/env python3
"""LT-4.4: per-run font/size authoring for mixed Khmer/English text.

The first attempt put two controls on the shared rich-text toolbar and had to be
withdrawn: applying one mark re-renders the object, which dropped the selection and
hid the strip, so the second control was unreachable. This test proves the shipped
shape instead — the selection survives the re-render and the controls live in the
object inspector's typography panel, which does not depend on toolbar visibility.

Flow at 1440:

1. seed one paragraph with two runs (English ``serif-formal``/28, Khmer
   ``sans-modern``/20) through ``EInviteEditorBridge.transact``;
2. click the object (so the inspector shows), then select the Khmer run with a real
   DOM ``Range``;
3. set the run font pairing in the inspector and apply -> exactly that run moves,
   the English run keeps both marks, and the selection is restored over the Khmer
   text after the re-render (measured from ``getSelection()``);
4. without re-selecting, set the run size in the inspector and apply -> the size
   mark lands on the same run (this is the step that previously became unreachable);
5. the marks reach the local draft and the server document, and a **same-profile reload**
   restores both marks and both computed styles.

The reload leg deliberately keeps the editor's cached invitation and draft in place: that is the
path that used to boot one flattened run, because the boot capture ran before the lazily loaded
rich-text modules existed (FB-96, ``artifacts/next-work/lt-4-4/RELOAD-DEFECT.md``).

Screenshots are written when ``EINVITE_CAPTURE_DIR`` is set.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from browser_runtime import dismiss_editor_onboarding, launch_chromium

ROOT = Path(__file__).resolve().parents[1]
SLUG = "lt-4-4-run-typography"

# Built from code points: agents never write Khmer, not even in a fixture.
_KHMER = ''.join(chr(code) for code in (
    0x179F, 0x17BB, 0x1797, 0x17B6, 0x20, 0x1793, 0x17B7, 0x1784, 0x20, 0x178F, 0x17B6, 0x179A, 0x17B6,
))
_ENGLISH = "Sophea & Dara"

_TITLE = {
    "id": "title",
    "type": "text",
    "layerName": "Title",
    "textStyleId": "display",
    "left": "8%",
    "top": "10%",
    "width": "84%",
    "height": "110px",
    "zIndex": 3,
    "typographyModelVersion": 1,
    "fontPairing": "serif-formal",
    "fontSize": 28,
    "textAutoFit": "none",
    "textAutoFitMax": 28,
    "textMinFontSize": 10,
    "showInHero": True,
    "richTextModelVersion": 1,
    "richText": {
        "version": 1,
        "entities": {},
        "paragraphs": [
            {
                "id": "p-run",
                "runs": [
                    {"id": "r-en", "text": "Sophea & Dara", "marks": {"fontPairing": "serif-formal", "fontSize": 28}, "locale": "en"},
                    {"id": "r-km", "text": _KHMER, "marks": {"fontPairing": "sans-modern", "fontSize": 20}, "locale": "km"},
                ],
                "list": {"type": "none", "level": 0, "start": 1, "marker": "disc"},
            }
        ],
    },
}

_SELECT_KHMER = """() => {
    const run = document.querySelector('.object[data-id="title"] .rt-run[data-run-id="r-km"]');
    if (!run) return null;
    const range = document.createRange();
    range.selectNodeContents(run);
    const selection = getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    return {text: run.textContent, length: range.toString().length};
}"""

_STATE = """(payload) => {
    const doc = window.EInviteEditorBridge.getState();
    const object = doc.objects?.title || {};
    const model = object.richText || {paragraphs: []};
    const runs = (model.paragraphs?.[0]?.runs || []).map((run) => ({
        id: run.id, text: run.text, marks: run.marks || {}
    }));
    const nodes = [...document.querySelectorAll('.object[data-id="title"] .rt-run')].map((node) => ({
        text: node.textContent,
        size: getComputedStyle(node).fontSize,
        family: getComputedStyle(node).fontFamily
    }));
    const selection = getSelection();
    return {
        runs,
        nodes,
        selection: selection && selection.rangeCount ? selection.toString() : '',
        selectionCollapsed: selection ? selection.isCollapsed : null,
        status: document.querySelector('#v20RunStatus')?.textContent || '',
        applyDisabled: document.querySelector('#v20RunApply')?.disabled ?? null,
        fontValue: document.querySelector('#v20RunFont')?.value || '',
        sizeValue: document.querySelector('#v20RunSize')?.value || '',
    };
}"""

_CSRF_HEADERS = """() => {
    const match = document.cookie.match(/(?:^|;\\s*)einvite_csrf=([^;]*)/);
    return match ? {'X-CSRF-Token': decodeURIComponent(match[1])} : {};
}"""


def _document() -> dict:
    return {
        "schemaVersion": 13,
        "eventType": "Wedding",
        "fields": {
            "names": _ENGLISH,
            "namesKm": _KHMER,
            "date": "2029-12-27",
            "time": "16:05",
            "venue": "Phnom Penh",
            "venueKm": "",
            "message": "Welcome",
            "messageKm": "",
        },
        "settings": {
            "rsvpEnabled": True,
            "wishesEnabled": False,
            "scheduleEnabled": False,
            "venueEnabled": False,
            "galleryEnabled": False,
            "countdownEnabled": False,
            "musicEnabled": False,
            "openingEnabled": True,
            "contactEnabled": False,
        },
        "languageMode": "both",
        "dateFormat": "gregorian",
        "accent": "#9d4555",
        "palette": {"background": "#fff8f2", "surface": "#ffffff", "text": "#342c26", "heading": "#9d4555"},
        "sectionOrder": ["rsvp"],
        "schedule": [],
        "venues": [],
        "customBlocks": [],
        "designPages": [],
        "objects": {"title": _TITLE},
        "slug": SLUG,
    }


def _runs_by_text(state: dict) -> dict:
    return {run["text"]: run for run in state["runs"]}


def test_run_typography_from_inspector():
    sync_playwright = pytest.importorskip("playwright.sync_api")
    from v14_test_utils import app_server

    capture = Path(os.environ["EINVITE_CAPTURE_DIR"]) if os.environ.get("EINVITE_CAPTURE_DIR") else None
    if capture:
        capture.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    with app_server() as (_process, base, _data):
        with sync_playwright.sync_playwright() as play:
            try:
                browser = launch_chromium(play)
            except Exception as exc:  # pragma: no cover - environment dependent
                pytest.skip(f"Chromium unavailable: {exc}")

            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("lt-4-4-run@example.com")
            page.locator("#password").fill("Strong-lt-4-4-pass-123")
            page.locator("#registerConfirmPassword").fill("Strong-lt-4-4-pass-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)

            created = page.evaluate(
                """async ([documentModel, token]) => {
                    const response = await fetch('/api/invitations', {
                        method: 'POST', headers: {'Content-Type': 'application/json', ...token},
                        body: JSON.stringify({slug: documentModel.slug, document: documentModel})
                    });
                    if (!response.ok) throw Error(await response.text());
                    return response.json();
                }""",
                [_document(), page.evaluate(_CSRF_HEADERS)],
            )

            editor_url = base + f"/invitations/{created['id']}/editor"
            page.goto(editor_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            dismiss_editor_onboarding(page)

            page.wait_for_selector('.object[data-id="title"] .rt-run[data-run-id="r-km"]', timeout=15000)
            if capture:
                page.screenshot(path=str(capture / "lt-4-4-1440-seeded.png"))

            # A real click is what opens the object inspector; the run range is set
            # afterwards so the click cannot collapse it.
            page.locator('#stage .object[data-id="title"]').click(position={"x": 8, "y": 8})
            page.wait_for_selector("#typographyControls", state="visible", timeout=15000)
            selected = page.evaluate(_SELECT_KHMER)
            assert selected and selected["text"] == _KHMER, selected
            assert selected["length"] == len(_KHMER), selected

            page.wait_for_function(
                "() => document.querySelector('#v20RunApply')?.disabled === false", timeout=5000,
            )
            before = page.evaluate(_STATE, {})
            assert before["applyDisabled"] is False, before
            assert "Khmer" in before["status"], before
            assert before["fontValue"] == "sans-modern", before
            assert before["sizeValue"] == "20", before
            english_family = next(node["family"] for node in before["nodes"] if node["text"] == _ENGLISH)

            # 1) font pairing, applied from the inspector (not the toolbar strip).
            page.select_option("#v20RunFont", "ceremonial-khmer")
            page.click("#v20RunApply")
            page.wait_for_function(
                """(khmer) => {
                    const runs = window.EInviteEditorBridge.getState().objects?.title?.richText?.paragraphs?.[0]?.runs || [];
                    return runs.some((run) => run.text === khmer && run.marks?.fontPairing === 'ceremonial-khmer');
                }""",
                arg=_KHMER,
                timeout=10000,
            )
            after_font = page.evaluate(_STATE, {})
            runs = _runs_by_text(after_font)
            assert runs[_KHMER]["marks"].get("fontPairing") == "ceremonial-khmer", runs
            assert runs[_ENGLISH]["marks"].get("fontPairing") == "serif-formal", runs
            assert runs[_ENGLISH]["marks"].get("fontSize") == 28, runs
            # The selection survived the re-render: this is the measured failure mode.
            assert after_font["selectionCollapsed"] is False, after_font
            assert _KHMER in after_font["selection"], after_font
            khmer_family = next(node["family"] for node in after_font["nodes"] if node["text"] == _KHMER)
            assert khmer_family != english_family, (khmer_family, english_family)
            if capture:
                page.screenshot(path=str(capture / "lt-4-4-1440-after-font.png"))

            # 2) size, without re-selecting anything.
            page.select_option("#v20RunSize", "32")
            page.click("#v20RunApply")
            page.wait_for_function(
                """(khmer) => {
                    const runs = window.EInviteEditorBridge.getState().objects?.title?.richText?.paragraphs?.[0]?.runs || [];
                    return runs.some((run) => run.text === khmer && run.marks?.fontSize === 32);
                }""",
                arg=_KHMER,
                timeout=10000,
            )
            after_size = page.evaluate(_STATE, {})
            runs = _runs_by_text(after_size)
            assert runs[_KHMER]["marks"].get("fontSize") == 32, runs
            assert runs[_KHMER]["marks"].get("fontPairing") == "ceremonial-khmer", runs
            assert runs[_ENGLISH]["marks"].get("fontSize") == 28, runs
            assert runs[_ENGLISH]["marks"].get("fontPairing") == "serif-formal", runs
            khmer_node = next(node for node in after_size["nodes"] if node["text"] == _KHMER)
            english_node = next(node for node in after_size["nodes"] if node["text"] == _ENGLISH)
            assert khmer_node["size"] == "32px", khmer_node
            assert english_node["size"] == "28px", english_node
            if capture:
                page.screenshot(path=str(capture / "lt-4-4-1440-after-size.png"))

            # 3) The editor's own save path carried both marks into the local draft.
            page.wait_for_function(
                "() => document.documentElement.dataset.savePending === 'false'", timeout=10000,
            )
            stored = page.evaluate(
                """() => Object.entries({...localStorage})
                    .filter(([key]) => key.startsWith('sovan-invite-draft-v3:'))
                    .map(([, value]) => value).join('\\n')"""
            )
            assert "ceremonial-khmer" in stored, "the run font never reached the local draft"

            # The editor's server save is debounced; force it and read the stored runs
            # back from the API so the reload below can only succeed from the server.
            page.evaluate("() => window.EInviteEditorBridge.save()")
            deadline = time.time() + 15
            stored_runs = []
            while time.time() < deadline:
                stored_runs = page.evaluate(
                    """async (id) => {
                        const response = await fetch('/api/invitations/' + id);
                        const payload = await response.json();
                        const title = (((payload.invitation || payload).document || {}).objects || {}).title || {};
                        return ((title.richText || {}).paragraphs || [])
                            .flatMap((paragraph) => paragraph.runs || [])
                            .map((run) => ({text: run.text, marks: run.marks || {}}));
                    }""",
                    created["id"],
                )
                if any(run["text"] == _KHMER and run["marks"].get("fontSize") == 32 for run in stored_runs):
                    break
                page.wait_for_timeout(400)
            assert any(run["text"] == _KHMER and run["marks"].get("fontSize") == 32 for run in stored_runs), stored_runs

            # 4) Reload the same profile: the cached invitation and the draft stay in
            # place, which is the path that used to flatten the title (FB-96).
            page.reload(wait_until="domcontentloaded", timeout=30000)
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            dismiss_editor_onboarding(page)
            page.wait_for_selector('.object[data-id="title"] .rt-run', timeout=15000)
            page.wait_for_timeout(1500)
            reloaded = page.evaluate(_STATE, {})
            assert len(reloaded["runs"]) >= 2, reloaded["runs"]
            runs = _runs_by_text(reloaded)
            assert runs[_KHMER]["marks"].get("fontSize") == 32, runs
            assert runs[_KHMER]["marks"].get("fontPairing") == "ceremonial-khmer", runs
            assert runs[_ENGLISH]["marks"].get("fontSize") == 28, runs
            assert runs[_ENGLISH]["marks"].get("fontPairing") == "serif-formal", runs
            khmer_node = next(node for node in reloaded["nodes"] if node["text"] == _KHMER)
            english_node = next(node for node in reloaded["nodes"] if node["text"] == _ENGLISH)
            assert khmer_node["size"] == "32px", khmer_node
            assert english_node["size"] == "28px", english_node
            if capture:
                page.screenshot(path=str(capture / "lt-4-4-1440-reloaded.png"))

            assert errors == [], errors
            context.close()
            browser.close()
