"""LT-2.2 (OD-29) — Khmer numerals and Khmer-formatted dates.

Two layers:
  * the pure `core/khmer-format.js` contract (digits generated from code points,
    fixed-timestamp dates in EN and KM, CE/BE, time and number formatting);
  * the real editor/public wiring: the per-invitation setting defaults off,
    round-trips through the editor draft, and published dates/countdowns use
    Khmer digits when it is on.

Khmer characters are never written here. Assertions build them with chr(0x17E0+n),
the same code points the module uses, and the page test reads them from the DOM.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'src' / 'js' / 'core' / 'khmer-format.js'


def _node(payload: dict) -> dict:
    script = (
        "const fs=require('fs'),vm=require('vm');"
        "global.window=global;"
        "vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));"
        "const K=global.EInviteKhmerFormat;"
        "const input=JSON.parse(process.argv[2]);"
        "const out={"
        "digits:K.toKhmerDigits('0123456789'),"
        "back:K.toLatinDigits(K.toKhmerDigits('0123456789')),"
        "has:K.hasKhmerDigits(K.toKhmerDigits('7')),"
        "none:K.hasKhmerDigits('7'),"
        "en:K.formatDate(input.date,{lang:'en'}),"
        "enKhmer:K.formatDate(input.date,{lang:'en',numerals:'khmr'}),"
        "kmKhmr:K.formatDate(input.date,{lang:'km',numerals:'khmr'}),"
        "enBe:K.formatDate(input.date,{lang:'en',numerals:'latn',era:'be'}),"
        "kmBe:K.formatDate(input.date,{lang:'km',numerals:'khmr',era:'be'}),"
        "bad:K.formatDate('not-a-date',{lang:'en'}),"
        "time:K.formatTime('16:05',{numerals:'khmr'}),"
        "number:K.formatNumber(1234,{numerals:'khmr'})"
        "};console.log(JSON.stringify(out));"
    )
    result = subprocess.run(
        ['node', '-e', script, str(MODULE), json.dumps(payload)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _digit(n: int) -> str:
    return chr(0x17E0 + n)


def _has_khmer_digit(text: str) -> bool:
    return any(_digit(n) in text for n in range(10))


def _has_ascii_digit(text: str) -> bool:
    return any('0' <= character <= '9' for character in text)


def test_module_contract() -> None:
    out = _node({'date': '2026-12-27'})
    expected_digits = ''.join(_digit(n) for n in range(10))

    assert out['digits'] == expected_digits
    assert out['back'] == '0123456789'
    assert out['has'] is True and out['none'] is False

    assert out['en'] == 'December 27, 2026'
    assert not _has_khmer_digit(out['en'])
    assert _digit(2) in out['enKhmer'] and _digit(0) in out['enKhmer']
    assert not _has_ascii_digit(out['enKhmer'])
    assert _digit(2) in out['kmKhmr'] and not _has_ascii_digit(out['kmKhmr'])

    assert '2569' in out['enBe']
    assert '2569' not in out['kmBe']
    assert all(_digit(n) in out['kmBe'] for n in (2, 5, 6, 9))

    assert out['bad'] == 'not-a-date'
    assert out['time'] == _digit(1) + _digit(6) + ':' + _digit(0) + _digit(5)
    assert out['number'] == _digit(1) + ',' + _digit(2) + _digit(3) + _digit(4), out['number']


def _document(*, numerals: bool, slug: str) -> dict:
    return {
        'schemaVersion': 13,
        'eventType': 'Wedding',
        'fields': {
            'names': 'Formatting test invitation',
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
            'scheduleEnabled': True,
            'venueEnabled': False,
            'galleryEnabled': False,
            'countdownEnabled': True,
            'musicEnabled': False,
            'openingEnabled': False,
            'contactEnabled': False,
            'khmerNumerals': numerals,
        },
        'languageMode': 'both',
        'dateFormat': 'gregorian',
        'accent': '#9d4555',
        'palette': {'background': '#fff8f2', 'surface': '#ffffff', 'text': '#342c26', 'heading': '#9d4555'},
        'sectionOrder': ['countdown', 'schedule', 'rsvp'],
        'schedule': [{'time': '16:05', 'title': 'Ceremony', 'titleKm': ''}],
        'venues': [],
        'customBlocks': [],
        'designPages': [],
        'objects': {},
        'slug': slug,
    }


def test_public_rendering_and_editor_round_trip() -> None:
    sync_playwright = pytest.importorskip('playwright.sync_api')
    sys.path.insert(0, str(ROOT / 'tests'))
    from browser_runtime import dismiss_editor_onboarding, launch_chromium, open_event_details
    from v14_test_utils import app_server

    with app_server() as (_process, base, _data):
        with sync_playwright.sync_playwright() as playwright:
            try:
                browser = launch_chromium(playwright)
            except Exception as exc:  # no installed Chromium on this host
                pytest.skip(f'Chromium unavailable: {exc}')
            context = browser.new_context(viewport={'width': 1600, 'height': 1000})
            page = context.new_page()
            page.goto(base + '/dashboard.html', wait_until='domcontentloaded', timeout=30000)
            page.locator('#authRegisterTab').click()
            page.locator('#email').fill('lt-2-2-format@example.com')
            page.locator('#password').fill('Strong-lt-2-2-pass-123')
            page.locator('#registerConfirmPassword').fill('Strong-lt-2-2-pass-123')
            page.locator('#loginBtn').click()
            page.wait_for_selector('#dashboardView:not([hidden])', timeout=20000)

            created = page.evaluate(
                """async docs => {
                    const out = [];
                    for (const doc of docs) {
                        const response = await fetch('/api/invitations', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({slug: doc.slug, document: doc})
                        });
                        if (!response.ok) throw Error(await response.text());
                        out.push(await response.json());
                    }
                    return out;
                }""",
                [_document(numerals=True, slug='lt-2-2-khmer'), _document(numerals=False, slug='lt-2-2-editor')],
            )
            public_row, editor_row = created
            publish = page.evaluate(
                """async row => {
                    const response = await fetch('/api/invitations/' + row.id + '/publish', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({document: row.document})
                    });
                    if (!response.ok) throw Error(await response.text());
                    return response.json();
                }""",
                public_row,
            )
            assert publish.get('url', '').startswith('/i/')

            page.goto(base + publish['url'], wait_until='domcontentloaded', timeout=30000)
            page.wait_for_selector('#publicRoot .guest-hero', timeout=20000)
            page.wait_for_function(
                """() => {
                    const date = document.querySelector('[data-guest-gregorian]');
                    const days = document.querySelector('.countdown [data-unit="days"]');
                    return !!date && !!days && days.textContent.trim().length > 0;
                }""",
                timeout=20000,
            )
            rendered = page.evaluate(
                """() => ({
                    date: document.querySelector('[data-guest-gregorian]')?.textContent || '',
                    times: [...document.querySelectorAll('.schedule-list article strong')].map(node => node.textContent),
                    units: [...document.querySelectorAll('.countdown [data-unit]')].map(node => node.textContent),
                    body: document.querySelector('#publicRoot .guest-hero')?.textContent || ''
                })"""
            )
            assert _has_khmer_digit(rendered['date']), rendered
            assert not _has_ascii_digit(rendered['date']), rendered
            assert rendered['times'] and all(_has_khmer_digit(value) and not _has_ascii_digit(value) for value in rendered['times']), rendered
            assert rendered['units'] and all(_has_khmer_digit(unit) for unit in rendered['units']), rendered

            for width in (375, 1440):
                page.set_viewport_size({'width': width, 'height': 900})
                page.reload(wait_until='domcontentloaded', timeout=30000)
                page.wait_for_selector('#publicRoot .guest-hero', timeout=20000)
                assert page.evaluate(
                    "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
                ) <= 1, f'public page overflows at {width}px'
            page.set_viewport_size({'width': 1600, 'height': 1000})

            page.goto(base + f"/invitations/{editor_row['id']}/editor", wait_until='domcontentloaded', timeout=30000)
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            dismiss_editor_onboarding(page)
            open_event_details(page)
            checkbox = page.locator('#khmerNumerals')
            checkbox.wait_for(state='attached', timeout=15000)
            assert checkbox.is_checked() is False
            checkbox.check()
            page.wait_for_function(
                "() => document.querySelector('#saveState')?.textContent === 'Saved'",
                timeout=15000,
            )
            assert page.evaluate("() => state.settings.khmerNumerals") is True

            page.reload(wait_until='domcontentloaded', timeout=30000)
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            dismiss_editor_onboarding(page)
            open_event_details(page)
            assert page.locator('#khmerNumerals').is_checked() is True

            page.evaluate("() => EInviteEditorBridge.select(['title'])")
            text = page.locator('#textContent')
            text.wait_for(state='visible', timeout=15000)
            text.fill('Couple 2')
            page.locator('#convertDigits').click()
            page.wait_for_function(
                "() => { const node = document.querySelector('[data-id=\"title\"] .content'); return !!node && node.textContent.includes(String.fromCodePoint(0x17E0 + 2)); }",
                timeout=15000,
            )
            converted = page.evaluate("() => document.querySelector('[data-id=\"title\"] .content').textContent")
            assert _has_khmer_digit(converted) and not _has_ascii_digit(converted), converted

            context.close()
            browser.close()
