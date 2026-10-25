"""LT-2.5 — Khmer IME composition and paste through the real editor.

The strings are read from the three Khmer map files (falling back to the
generated TRANSLATIONS.csv when the map files are not checked out). The test
drives the real editor: inline editing on the canvas, progressive
compositionstart/insertCompositionText/end events, a ClipboardEvent paste, the
server save, a reload, and a code-point comparison of the text at every step.

The existing canvas gate's `khmer-ime` interaction only assigns textContent, so
it cannot catch a model/selection regression. This test closes that gap.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))

MAPS = [
    ROOT / 'docs/i18n/KHMER-TRANSLATION-MAP-2026-10-24.md',
    ROOT / 'docs/i18n/KHMER-TRANSLATION-MAP-ADDENDUM-2026-10-24.md',
    ROOT / 'docs/i18n/KHMER-TRANSLATION-MAP-ADDENDUM-2-2026-10-24.md',
]
KHMER_RUN = re.compile(r'[\u1780-\u17FF\u200C\u200D]+(?:[ \u200B]+[\u1780-\u17FF\u200C\u200D]+)*')


def _pick_phrases() -> tuple[str, str]:
    seen: list[str] = []
    for path in MAPS:
        if not path.is_file():
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            for match in KHMER_RUN.finditer(line):
                value = match.group(0).strip()
                if 8 <= len(value) <= 40 and '\u17d2' in value and value not in seen:
                    seen.append(value)
    if len(seen) < 2:
        with (ROOT / 'docs/i18n/TRANSLATIONS.csv').open(encoding='utf-8', newline='') as handle:
            for row in csv.DictReader(handle):
                value = (row.get('km') or '').strip()
                if 8 <= len(value) <= 40 and '\u17d2' in value and value not in seen:
                    seen.append(value)
    assert len(seen) >= 2, 'no suitable Khmer phrases found in the map or CSV'
    ime = next(value for value in seen if '\u17b6' in value or '\u17b7' in value)
    paste = next(value for value in seen if value != ime)
    return ime, paste


def _document(slug: str) -> dict:
    return {
        'schemaVersion': 13,
        'eventType': 'Wedding',
        'fields': {
            'names': 'Khmer input test',
            'namesKm': '',
            'date': '2029-12-27',
            'time': '16:05',
            'venue': 'Phnom Penh',
            'venueKm': '',
            'message': 'Welcome',
            'messageKm': '',
        },
        'settings': {
            'rsvpEnabled': False,
            'wishesEnabled': False,
            'scheduleEnabled': False,
            'venueEnabled': False,
            'galleryEnabled': False,
            'countdownEnabled': False,
            'musicEnabled': False,
            'openingEnabled': False,
            'contactEnabled': False,
        },
        'languageMode': 'both',
        'dateFormat': 'gregorian',
        'accent': '#9d4555',
        'palette': {'background': '#fff8f2', 'surface': '#ffffff', 'text': '#342c26', 'heading': '#9d4555'},
        'sectionOrder': [],
        'schedule': [],
        'venues': [],
        'customBlocks': [],
        'designPages': [],
        'objects': {
            'copy': {
                'id': 'copy',
                'type': 'text',
                'layerName': 'Khmer input',
                'left': '8%',
                'top': '20%',
                'width': '84%',
                'height': '180px',
                'textStyleId': 'body',
                'typographyModelVersion': 1,
                'fontPairing': 'sans-modern',
                'fontSize': 28,
                'textAutoFit': 'none',
                'textAutoFitMax': 28,
                'textMinFontSize': 12,
                'fontWeight': '400',
                'fontStyle': 'normal',
                'lineHeight': 1.6,
                'letterSpacing': 0,
                'colorToken': 'text',
                'textAlign': 'left',
                'textVerticalAlign': 'middle',
                'textWrap': 'pretty',
                'textColumns': 1,
                'textColumnGap': 24,
                'textPadding': 8,
                'showInHero': True,
                'showInGallery': False,
                'zIndex': 10,
                'richTextModelVersion': 1,
                'richText': {
                    'version': 1,
                    'entities': {},
                    'paragraphs': [{
                        'id': 'p-input',
                        'paragraphStyleId': 'body',
                        'locale': 'en',
                        'direction': 'ltr',
                        'overrides': {'textAlign': 'left', 'lineHeight': 1.6},
                        'list': {'type': 'none', 'level': 0, 'start': 1, 'marker': 'disc'},
                        'tabStops': [],
                        'runs': [{'id': 'r-input', 'text': 'Start', 'locale': 'en', 'marks': {}}],
                    }],
                },
                'html': 'Start',
                'text': 'Start',
            }
        },
        'slug': slug,
    }


IME = """(text) => {
  const content = document.querySelector('.object[data-id="copy"] .content');
  const paragraph = state.objects.copy.richText.paragraphs[0];
  const run = paragraph.runs.at(-1);
  const end = {paragraphId: paragraph.id, runId: run.id, offset: run.text.length};
  content.focus();
  RichTextEditing.restore(content, {anchor: end, focus: end});
  const graphemes = [...new Intl.Segmenter('km', {granularity: 'grapheme'}).segment(text)].map(part => part.segment);
  const chunks = [];
  for (let index = 2; index < graphemes.length; index += 2) chunks.push(graphemes.slice(0, index).join(''));
  if (!chunks.length || chunks.at(-1) !== text) chunks.push(text);
  content.dispatchEvent(new CompositionEvent('compositionstart', {bubbles: true, data: ''}));
  for (const chunk of chunks) {
    content.dispatchEvent(new InputEvent('beforeinput', {
      inputType: 'insertCompositionText', data: chunk, bubbles: true, cancelable: true, isComposing: true
    }));
  }
  content.dispatchEvent(new CompositionEvent('compositionend', {bubbles: true, data: text}));
  return {chunks: chunks.length, graphemes: graphemes.length};
}"""

PASTE = """(text) => {
  const content = document.querySelector('.object[data-id="copy"] .content');
  const paragraph = state.objects.copy.richText.paragraphs.at(-1);
  const run = paragraph.runs.at(-1);
  const end = {paragraphId: paragraph.id, runId: run.id, offset: run.text.length};
  content.focus();
  RichTextEditing.restore(content, {anchor: end, focus: end});
  const transfer = new DataTransfer();
  transfer.setData('text/plain', text);
  content.dispatchEvent(new ClipboardEvent('paste', {clipboardData: transfer, bubbles: true, cancelable: true}));
}"""

READ = """() => {
  const object = state.objects.copy;
  return {
    text: object.text,
    plain: RichTextDocumentModel.exportPlainText(object.richText),
    dom: document.querySelector('.object[data-id="copy"] .content')?.textContent || ''
  };
}"""


def test_khmer_ime_and_paste_survive_the_editor_round_trip() -> None:
    sync_playwright = pytest.importorskip('playwright.sync_api')
    from browser_runtime import dismiss_editor_onboarding, launch_chromium
    from v14_test_utils import app_server

    ime_phrase, paste_phrase = _pick_phrases()
    expected = 'Start' + ime_phrase + paste_phrase
    errors: list[str] = []

    with app_server() as (_process, base, _data):
        with sync_playwright.sync_playwright() as playwright:
            try:
                browser = launch_chromium(playwright)
            except Exception as exc:
                pytest.skip(f'Chromium unavailable: {exc}')
            context = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
            page.goto(base + '/dashboard.html', wait_until='domcontentloaded', timeout=30000)
            page.locator('#authRegisterTab').click()
            page.locator('#email').fill('lt-2-5-input@example.com')
            page.locator('#password').fill('Strong-lt-2-5-input-123')
            page.locator('#registerConfirmPassword').fill('Strong-lt-2-5-input-123')
            page.locator('#loginBtn').click()
            page.wait_for_selector('#dashboardView:not([hidden])', timeout=20000)

            document_model = _document('lt-2-5-input')
            created = page.evaluate(
                """async documentModel => {
                    const response = await fetch('/api/invitations', {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({slug: documentModel.slug, document: documentModel})
                    });
                    if (!response.ok) throw Error(await response.text());
                    return response.json();
                }""",
                document_model,
            )
            invitation_id = created['id']

            page.goto(base + f'/invitations/{invitation_id}/editor', wait_until='domcontentloaded', timeout=30000)
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            dismiss_editor_onboarding(page)
            page.wait_for_selector('.object[data-id="copy"]', timeout=20000)
            page.wait_for_timeout(400)

            page.locator('.object[data-id="copy"]').dblclick(position={'x': 30, 'y': 40})
            page.wait_for_function(
                "() => document.querySelector('.object[data-id=\"copy\"] .content')?.getAttribute('contenteditable') === 'true'",
                timeout=10000,
            )
            page.wait_for_timeout(200)

            ime = page.evaluate(IME, ime_phrase)
            assert ime['chunks'] >= 2 and ime['graphemes'] >= 4, ime
            page.wait_for_timeout(900)
            after_ime = page.evaluate(READ)
            assert after_ime['plain'] == 'Start' + ime_phrase, after_ime

            page.evaluate(PASTE, paste_phrase)
            page.wait_for_timeout(900)
            after_paste = page.evaluate(READ)
            assert after_paste['plain'] == expected, after_paste
            assert after_paste['text'] == expected, after_paste

            page.evaluate("() => RichTextEditing.flush()")
            page.wait_for_timeout(3000)
            persisted = page.evaluate(
                """async id => {
                    const response = await fetch('/api/invitations/' + id);
                    if (!response.ok) throw Error(await response.text());
                    const row = await response.json();
                    return {text: row.document.objects.copy.text, html: row.document.objects.copy.html};
                }""",
                invitation_id,
            )
            assert persisted['text'] == expected, persisted
            assert [ord(character) for character in persisted['text']] == [ord(character) for character in expected]

            page.reload(wait_until='domcontentloaded', timeout=30000)
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            dismiss_editor_onboarding(page)
            page.wait_for_selector('.object[data-id="copy"]', timeout=20000)
            page.wait_for_timeout(500)
            after_reload = page.evaluate(READ)
            assert after_reload['plain'] == expected, after_reload
            assert after_reload['dom'] == expected, after_reload
            assert [ord(character) for character in after_reload['plain']] == [ord(character) for character in expected]
            assert not errors, errors

            context.close()
            browser.close()
