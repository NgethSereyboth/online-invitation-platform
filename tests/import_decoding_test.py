#!/usr/bin/env python3
"""Permanent harness for the bulk guest import's encoding detection.

Phase A of `docs/reviews/bulk-guest-import-research.md` §5.7 is the one phase of the
bulk-guest-import feature whose evidence had no permanent carrier: the implementation
pass exercised `decodeImportText` from a throwaway `/tmp` harness, which the same pass
deleted, so nothing in the repository proved the decoding path still worked. This
module is that carrier.

The reported failure mode it exists to rule out, from §2 of the research report: a
designer on Windows saves an Excel sheet as CSV, Excel writes it as UTF-16LE with a
BOM, and an importer that assumes UTF-8 either throws or imports mojibake — Khmer
names arrive as boxes or as `Ã¡Âžâ€¦`. What has to be true is that the four encodings
below all decode, that Khmer survives byte-for-byte, and that a stream which is none of
them is refused rather than guessed at.

HOW THIS TEST EXECUTES THE SHIPPED CODE
---------------------------------------
`decodeImportText` is a browser function: `src/js/guests.js` reads `window`,
`document` and `localStorage` at load time and calls `load()` at the end, so the file
cannot simply be imported. Rather than load it behind a large hand-written DOM shim —
which would test the shim as much as the code — this module extracts the exact source
text of the declarations it needs from `src/js/guests.js` and pipes them to Node, which
offers the same WHATWG `TextDecoder` the browser does (verified: Node 22 with full ICU
decodes `utf-8`, `utf-16le` and `utf-16be`, and `{fatal:true}` throws on a malformed
sequence, which is the behaviour the shipped code relies on).

The extraction refuses to guess: each declaration must appear exactly once, and the
span is taken by balancing braces and quotes over the real file, so the code under test
is the repository's own bytes. If a declaration is renamed or removed, these tests fail
loudly instead of passing against a stale copy.

The pipeline tests (the Windows-Excel sheet) also run the shipped `parseCsv`,
`csvCells`, `importStateFor`, `importEntries`, `importFindings` and
`importRowsToImport`, so the end-to-end claim is about the same functions the page runs.

Khmer fixture strings are taken from `docs/i18n/TRANSLATIONS.csv`; none is invented.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUESTS_JS = ROOT / "src" / "js" / "guests.js"
NODE = shutil.which("node")

# The declarations the decoding path needs, in dependency order.
DECLARATIONS = (
    "decodeImportText",
    "parseCsv",
    "csvCells",
    "importStateFor",
    "importEntries",
    "importFindings",
    "importRowsToImport",
)

# Khmer fixtures, every one of them present in docs/i18n/TRANSLATIONS.csv:
#   ឈ្មោះ = "name", ទូរស័ព្ទ = "phone", ឈ្មោះភ្ញៀវ = "guest name"
# Reusing the approved corpus as fixture DATA (not as UI copy) is deliberate: no Khmer
# is invented here, and the strings carry the same codepoints the product's copy does.
KHMER_NAME_HEADER = "ឈ្មោះ"
KHMER_PHONE_HEADER = "ទូរស័ព្ទ"
KHMER_NAMES = ("អ្នកប្រើ", "គណនី", "បញ្ចូលភ្ញៀវ")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed, so the shipped browser decoder cannot be executed")


def _scan_declaration(source: str, start: int) -> str:
    """The exact source text of one declaration, from balanced braces and quotes."""
    depth = 0
    index = start
    quote = None
    while index < len(source):
        char = source[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in "\"'`":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        elif char == ";" and depth == 0 and not source[start:].lstrip().startswith("function"):
            return source[start:index + 1]
        index += 1
    raise AssertionError(f"unbalanced declaration starting at offset {start}: {source[start:start + 80]!r}")


def declaration(name: str) -> str:
    """One shipped declaration, taken from src/js/guests.js, refusing to guess."""
    source = GUESTS_JS.read_text(encoding="utf-8")
    for pattern in (f"function {name}(", f"const {name}="):
        if source.count(pattern) == 1:
            return _scan_declaration(source, source.index(pattern))
    raise AssertionError(
        f"src/js/guests.js must define exactly one of 'function {name}(' or 'const {name}=' "
        f"— found {source.count(f'function {name}(')} and {source.count(f'const {name}=')}"
    )


def _run_node(program: str):
    # Node reads the program from a temp file, not from stdin. Piping to
    # `node -` is fine when pytest runs nothing else, but under pytest the child
    # never sees EOF on its stdin pipe on Windows, so every test times out at
    # 60 s with the same program it was about to run. Writing the exact program
    # (declarations + driver, byte-identical) to a file removes the stdin race
    # without changing what is executed; stdout is still a single JSON line.
    assert NODE, "node is required"
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8", newline="\n") as script:
        script.write(program)
        script_name = script.name
    try:
            # text=True without an encoding uses the Windows locale codec
            # (cp1252), which throws on Khmer output; stdout is our own JSON so
            # UTF-8 it is. text decoding for stdout/stderr only — input no longer
            # goes through a pipe at all.
            result = subprocess.run(
                [NODE, script_name], capture_output=True, timeout=60,
                text=True, encoding="utf-8",
            )
    finally:
        os.unlink(script_name)
    assert result.returncode == 0, f"node exited {result.returncode}:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def decode(payload: bytes, pipeline: bool = False):
    """Run the shipped decoder (and optionally the rest of the import path) on bytes."""
    tail = ""
    if pipeline:
        tail = """
const rows = csvCells(parseCsv(decoded.text));
const state = importStateFor(rows, 'CSV');
const findings = importFindings(state);
out.rows = rows;
out.state = {header: state.header, columns: state.columns, start: state.start};
out.entries = findings.entries;
out.blank = findings.blank;
out.duplicates = findings.duplicates;
out.importable = importRowsToImport(state).length;
"""
    program = "\n".join(declaration(name) for name in DECLARATIONS) + f"""
const BYTES = Uint8Array.from(Buffer.from('{payload.hex()}', 'hex'));
const decoded = decodeImportText(BYTES.buffer);
const out = {{ decoded }};
{tail}
console.log(JSON.stringify(out));
"""
    return _run_node(program)


# ── fixtures as byte strings, never files on disk ──────────────────────────────

def utf8(text: str) -> bytes:
    return text.encode("utf-8")


def utf8_bom(text: str) -> bytes:
    return b"\xef\xbb\xbf" + text.encode("utf-8")


def utf16le_bom(text: str) -> bytes:
    return b"\xff\xfe" + text.encode("utf-16-le")


def utf16be_bom(text: str) -> bytes:
    return b"\xfe\xff" + text.encode("utf-16-be")


# ── the eight cases the brief names ───────────────────────────────────────────

def test_utf8_without_bom_decodes():
    result = decode(utf8("Name,Phone\nSok Dara,012000001\n"))["decoded"]
    assert result == {"text": "Name,Phone\nSok Dara,012000001\n", "encoding": "UTF-8"}, result


def test_utf8_with_bom_is_stripped():
    result = decode(utf8_bom("Name,Phone\nSok Dara,012000001\n"))["decoded"]
    assert result["encoding"] == "UTF-8 with BOM", result
    assert result["text"] == "Name,Phone\nSok Dara,012000001\n", result
    assert "\ufeff" not in result["text"], "the BOM must not survive into the first cell"


def test_utf16le_with_bom_decodes():
    result = decode(utf16le_bom("Name,Phone\r\nSok Dara,012000001\r\n"))["decoded"]
    assert result["encoding"] == "UTF-16LE with BOM", result
    assert result["text"] == "Name,Phone\r\nSok Dara,012000001\r\n", result


def test_utf16be_with_bom_decodes():
    result = decode(utf16be_bom("Name,Phone\r\nSok Dara,012000001\r\n"))["decoded"]
    assert result["encoding"] == "UTF-16BE with BOM", result
    assert result["text"] == "Name,Phone\r\nSok Dara,012000001\r\n", result


def test_invalid_byte_sequence_is_refused():
    """A legacy codepage is neither UTF-8, UTF-16LE nor UTF-16BE: refuse, never guess.

    Three things have to hold together for the refusal to mean anything: the decoder
    reports the failure, the reader short-circuits on it *before* parsing, and the
    designer is told why rather than shown an empty import.
    """
    payload = b"\xc3\x28Name,Phone\nSok Dara\n"
    result = decode(payload)["decoded"]
    assert result["failed"] is True, result
    assert result["text"] == "" and result["encoding"] == "", result

    # readImportFile's guard, taken verbatim from the shipped file: the failure returns
    # an empty parsed result, so no caller can reach parseCsv with a refused stream.
    source = GUESTS_JS.read_text(encoding="utf-8")
    assert "if(decoded.failed)return{rows:[],source:'CSV',decodeFailure:true}" in source, (
        "the reader's decode-failure guard moved; the refusal is no longer enforced where it was"
    )
    assert "This CSV is neither UTF-8, UTF-16LE nor UTF-16BE." in source, (
        "the refusal must still tell the designer which encodings are accepted"
    )

    # And if the guard were bypassed, the empty decode still yields nothing importable.
    bypassed = decode(payload, pipeline=True)
    assert bypassed["rows"] in ([], [""]) and bypassed["importable"] == 0, bypassed


def test_empty_file_yields_nothing_to_import():
    """Documented behaviour: an empty file decodes to an empty string, not an error."""
    result = decode(b"", pipeline=True)
    assert result["decoded"]["text"] == "", result["decoded"]
    assert result["decoded"].get("failed") is not True, result["decoded"]
    assert result["rows"] == [], result["rows"]
    assert result["entries"] == [] and result["importable"] == 0


def test_khmer_utf8_round_trips_byte_for_byte():
    text = f"{KHMER_NAME_HEADER},{KHMER_PHONE_HEADER}\n" + "\n".join(
        f"{name},01{n:07d}" for n, name in enumerate(KHMER_NAMES)
    ) + "\n"
    payload = utf8(text)
    result = decode(payload, pipeline=True)
    assert result["decoded"]["text"] == text, result["decoded"]
    assert result["decoded"]["encoding"] == "UTF-8", result["decoded"]
    assert result["decoded"]["text"].encode("utf-8") == payload, "UTF-8 must round-trip byte-for-byte"
    for name in KHMER_NAMES:
        assert name in result["decoded"]["text"], name


def test_khmer_utf16le_round_trips_byte_for_byte():
    text = f"{KHMER_NAME_HEADER},{KHMER_PHONE_HEADER}\n" + "\n".join(
        f"{name},01{n:07d}" for n, name in enumerate(KHMER_NAMES)
    ) + "\n"
    payload = utf16le_bom(text)
    result = decode(payload, pipeline=True)
    assert result["decoded"]["encoding"] == "UTF-16LE with BOM", result["decoded"]
    assert result["decoded"]["text"] == text, result["decoded"]
    assert b"\xff\xfe" + result["decoded"]["text"].encode("utf-16-le") == payload, "UTF-16LE must round-trip"
    for name in KHMER_NAMES:
        assert name in result["decoded"]["text"], name


# ── the case §2 of the research report is actually about ───────────────────────

def test_windows_excel_utf16le_sheet_imports_khmer_names():
    """Excel on Windows: UTF-16LE + BOM, CRLF rows, a Khmer header, quoted commas.

    The whole page path, not just the decoder: bytes → decodeImportText → parseCsv →
    csvCells → importStateFor → importFindings, so this asserts what the import dialog
    would show — the header detected, the Khmer header recognised as the name column,
    and every Khmer name intact and free of mojibake.
    """
    rows = [
        f"{KHMER_NAME_HEADER},{KHMER_PHONE_HEADER}",
        *[f"{name},01{n:07d}" for n, name in enumerate(KHMER_NAMES)],
        # A quoted comma, as a spreadsheet writes it. The Khmer in this field is the
        # corpus string 'អ្នកប្រើ'; ', Jr' is Latin, so the rule below still holds: no Khmer
        # here was assembled from parts.
        f'"{KHMER_NAMES[0]}, Jr",010000099',
    ]
    text = "\r\n".join(rows) + "\r\n"
    result = decode(utf16le_bom(text), pipeline=True)

    assert result["decoded"]["encoding"] == "UTF-16LE with BOM", result["decoded"]
    assert result["state"]["header"] is True, result["state"]
    assert result["state"]["start"] == 1, "the header row must not be imported as a guest"
    assert result["state"]["columns"] == 2, result["state"]
    assert result["blank"] == [], result["blank"]
    assert result["duplicates"] == [], result["duplicates"]

    imported = [entry["name"] for entry in result["entries"]]
    assert imported == [*KHMER_NAMES, f"{KHMER_NAMES[0]}, Jr"], imported
    for name in KHMER_NAMES:
        assert name in imported, f"{name} did not survive the Windows-Excel path"
    assert not any("\ufffd" in name for name in imported), f"mojibake: {imported}"
    assert not any("Ã" in name for name in imported), f"double-decoded: {imported}"
    assert result["importable"] == 4, result["importable"]
    assert [entry["phone"] for entry in result["entries"]][0] == "010000000"


def test_khmer_fixtures_are_corpus_strings():
    """No invented Khmer — the project's hard rule, enforced rather than promised.

    Every Khmer substring this module feeds the decoder is asserted to appear in
    docs/i18n/TRANSLATIONS.csv. If a future edit invents a fixture name, this fails here
    instead of quietly shipping Khmer that no reviewer approved.
    """
    corpus = (ROOT / "docs" / "i18n" / "TRANSLATIONS.csv").read_text(encoding="utf-8")
    for value in (KHMER_NAME_HEADER, KHMER_PHONE_HEADER, *KHMER_NAMES):
        assert value in corpus, f"fixture Khmer {value!r} is not in docs/i18n/TRANSLATIONS.csv"
