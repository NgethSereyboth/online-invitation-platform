"""LT-2.6 Khmer export sheet — deterministic fixture builder.

The sheet is a throwaway invitation whose text comes from the generated
`docs/i18n/TRANSLATIONS.csv` (itself produced from the three Khmer map files by
`tools/i18n-apply-khmer-map.py`).  No Khmer literal is typed in this file: the
phrases are selected by script from the `km` column.

`expected.sha256` pins the canonical fixture JSON and the export tolerances, so
a map/CSV change can never silently move the fidelity target.  Regenerate it
with:

    python3 docs/qa/khmer-text-sheet/build_sheet.py --write-hash

Committed files are only this script and `expected.sha256`; rendered PNG/PDF
proofs stay under the gitignored artifacts tree.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CSV = ROOT / 'docs/i18n/TRANSLATIONS.csv'
EXPECTED = Path(__file__).resolve().with_name('expected.sha256')
KHMER_RUN = re.compile(r'[\u1780-\u17FF\u200C\u200D]+(?:[ \u200B]+[\u1780-\u17FF\u200C\u200D]+)*')
TOLERANCE = {
    'png_1x_mae': 0.5,
    'png_1x_changed_over_8': 0.002,
    'png_scaled_mae': 1.5,
    'png_scaled_changed_over_8': 0.035,
    'pdf_mae': 4.5,
    'pdf_changed_over_8': 0.07,
    'pdf_text_box_px': 4,
}

sys.path.insert(0, str(ROOT / 'src' / 'python'))
from rich_text_document_model import export_legacy_html, export_plain_text, normalize_rich_text  # noqa: E402


def pick_phrases() -> list[str]:
    """Return three distinct-length Khmer phrases from the tracked CSV."""
    assert CSV.is_file(), f'missing {CSV}'
    seen: list[str] = []
    with CSV.open(encoding='utf-8', newline='') as handle:
        for row in csv.DictReader(handle):
            value = (row.get('km') or '').strip()
            if not (10 <= len(value) <= 80):
                continue
            if '\u17d2' not in value or not KHMER_RUN.fullmatch(value):
                continue
            if value in seen or any(len(value) == len(other) for other in seen):
                continue
            seen.append(value)
    assert len(seen) >= 3, f'only {len(seen)} suitable Khmer phrases in {CSV}'
    return seen[:3]


def rich_document(phrases: list[str]) -> dict:
    sizes = [36, 26, 20]
    paragraphs = []
    for index, (text, size) in enumerate(zip(phrases, sizes)):
        paragraphs.append({
            'id': f'p-{index}',
            'paragraphStyleId': 'body',
            'locale': 'km',
            'direction': 'ltr',
            'overrides': {'textAlign': 'left', 'lineHeight': 1.7},
            'list': {'type': 'none', 'level': 0, 'start': 1, 'marker': 'disc'},
            'tabStops': [],
            'runs': [{
                'id': f'r-{index}',
                'text': text,
                'locale': 'km',
                'marks': {'fontPairing': 'sans-modern', 'fontSize': size},
            }],
        })
    return normalize_rich_text({'version': 1, 'entities': {}, 'paragraphs': paragraphs}, strict=True)


def document(phrases: list[str], slug: str = 'lt-2-6-export') -> dict:
    rich = rich_document(phrases)
    return {
        'schemaVersion': 13,
        'eventType': 'Wedding',
        'canvasFormat': {'id': 'test-sheet', 'name': 'Test sheet', 'width': 420, 'height': 640},
        'fields': {
            'names': phrases[0],
            'namesKm': phrases[0],
            'date': '2029-12-27',
            'time': '16:05',
            'venue': 'Phnom Penh',
            'venueKm': '',
            'message': '',
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
            'sheet': {
                'id': 'sheet',
                'type': 'text',
                'layerName': 'Khmer test sheet',
                'left': '8%',
                'top': '8%',
                'width': '84%',
                'height': '70%',
                'textStyleId': 'body',
                'typographyModelVersion': 1,
                'fontPairing': 'sans-modern',
                'fontSize': 36,
                'textAutoFit': 'none',
                'textAutoFitMax': 36,
                'textMinFontSize': 10,
                'fontWeight': '400',
                'fontStyle': 'normal',
                'lineHeight': 1.7,
                'letterSpacing': 0,
                'colorToken': 'text',
                'textAlign': 'left',
                'textVerticalAlign': 'top',
                'textWrap': 'pretty',
                'textColumns': 1,
                'textColumnGap': 24,
                'textPadding': 0,
                'showInHero': True,
                'showInGallery': False,
                'zIndex': 20,
                'richTextModelVersion': 1,
                'richText': rich,
                'html': export_legacy_html(rich),
                'text': export_plain_text(rich),
            }
        },
        'slug': slug,
    }


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def digests(phrases: list[str], doc: dict) -> tuple[str, str]:
    return hashlib.sha256(canonical(phrases)).hexdigest(), hashlib.sha256(canonical(doc)).hexdigest()


def expected_text() -> str:
    phrases = pick_phrases()
    fixture, document_hash = digests(phrases, document(phrases))
    lines = [
        '# LT-2.6 Khmer export sheet. Regenerate with build_sheet.py --write-hash.',
        f'phrases_sha256 {fixture}',
        f'fixture_sha256 {document_hash}',
        'tolerance ' + ' '.join(f'{key}={value}' for key, value in TOLERANCE.items()),
        '',
    ]
    return '\n'.join(lines)


def read_expected(path: Path = EXPECTED) -> dict:
    data = {'tolerance': {}}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        key, _, value = line.partition(' ')
        if key == 'tolerance':
            for pair in value.split():
                name, _, number = pair.partition('=')
                data['tolerance'][name] = float(number)
        else:
            data[key] = value
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-hash', action='store_true', help='rewrite expected.sha256')
    parser.add_argument('--check', action='store_true', help='verify expected.sha256')
    parser.add_argument('--json', action='store_true', help='print the fixture document')
    args = parser.parse_args()

    if args.write_hash:
        EXPECTED.write_text(expected_text(), encoding='utf-8')
        print(EXPECTED)
        return 0

    phrases = pick_phrases()
    doc = document(phrases)
    phrase_hash, fixture_hash = digests(phrases, doc)
    if args.check or not (args.write_hash or args.json):
        expected = read_expected()
        assert expected['phrases_sha256'] == phrase_hash, 'phrases changed; regenerate expected.sha256'
        assert expected['fixture_sha256'] == fixture_hash, 'fixture changed; regenerate expected.sha256'
        print(f'KHMER_SHEET_OK {fixture_hash[:12]} phrases={len(phrases)}')
    if args.json:
        print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
