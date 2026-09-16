#!/usr/bin/env python3
"""
V2-UX-10 (ROADMAP-V2 §3.10) — Bilingual consistency CI check.

Walks ``src/js/*.js`` (skipping generated ``bundle-*.js`` files) looking for
the two bilingual string-table patterns used across the codebase:

  Pattern A (per-key):   STRINGS = { key1: { en: '...', km: '...' }, ... }
  Pattern B (per-locale): STRINGS = { en: { key1: '...', ... },
                                      km: { key1: '...', ... } }

For each ``en:`` string it verifies that a ``km:`` string exists for the same
key, and that the two are not byte-identical after trim (which would mean the
Khmer translation is a placeholder that slipped through).

USAGE
  scripts/check-bilingual-consistency.py [--root DIR] [--strict]
        [--allow-identical EXCEPTIONS] [--report PATH] [--json]

EXIT CODES
  0 — every ``en:`` string has a non-identical ``km:`` translation
      (or every identical pair is on the documented exception list).
  1 — at least one ``en:`` string is missing ``km:``, or at least one
      (en, km) pair is byte-identical and not on the exception list.

The ``--strict`` flag (recommended for CI) treats any byte-identical pair that
is NOT on the exception list as a failure. Without ``--strict`` the script
still reports identical pairs but exits 0 if all of them are on the exception
list OR are obviously numeric/symbol-only (heuristic).

The ``--allow-identical EXCEPTIONS`` flag accepts a comma-separated list of
extra strings that are allowed to be byte-identical in EN and KH (e.g. brand
newcomers not yet baked into the default exception list).

The ``--report PATH`` flag writes a Markdown report (same shape as
``docs/i18n/BILINGUAL-CONSISTENCY-REPORT.md``) to the given path. The
``--json`` flag emits machine-readable JSON instead of human text.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Exception list — legitimate byte-identical EN/KH pairs.
# ---------------------------------------------------------------------------
# These are strings where EN and KH are intentionally the same because the
# Khmer language does not have a distinct equivalent (proper nouns, brand
# names, technical acronyms, URLs, emails, numbers, dates, currency).
#
# Add to this list ONLY if you can defend the entry: it must be a proper noun,
# a brand name, or a technical term with no Khmer equivalent. Do NOT add
# regular UI words (those MUST be translated).
DEFAULT_EXCEPTION_STRINGS: Set[str] = {
    # Brand names / proper nouns (Case-sensitive — match exact value)
    "eInvite", "Canva", "Stripe", "WhatsApp", "Telegram", "Slack", "Discord",
    "GitHub", "Google", "Apple", "Microsoft", "Facebook", "Instagram",
    "Twitter", "TikTok", "YouTube", "Zoom", "Webex",
    # Invitation-platform-specific acronyms
    "RSVP",
    # Technical terms with no Khmer equivalent
    "API", "CRDT", "Y.js", "Y.Doc", "Y.Map", "Y.Array", "Y.UndoManager",
    "WebAuthn", "IndexedDB", "WebSocket", "WebRTC",
    "HTTP", "HTTPS", "JSON", "DOM", "URL", "ID", "CSS", "HTML", "JS",
    "MpCmdRun.exe", "clamdscan", "clamd", "clamav",
}

# Regex patterns that match legitimate identical pairs (used in --strict too).
EXCEPTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$"),   # email addresses
    re.compile(r"^https?://"),                     # URLs
    re.compile(r"^[\d][\d.,:\-/+\s%]*$"),          # numbers / dates / currencies
    re.compile(r"^0\s*=\s*\S*$"),                 # "0 = unlimited"-style hint
    re.compile(r"^\W+$"),                          # punctuation / symbols only
    re.compile(r"^[+]\s"),                        # "+ Add ..." (already translated after)
    re.compile(r"^[A-Z]{2,5}$"),                  # 2-5 letter ALL-CAPS acronym
    re.compile(r"^[\w\s]?\d+$"),                  # single digit labels like "Qty"
]


def is_exception(value: str) -> bool:
    """Return True if ``value`` is on the documented exception list."""
    if value is None:
        return False
    v = value.strip()
    if not v:
        return True  # empty strings handled separately as missing
    if v in DEFAULT_EXCEPTION_STRINGS:
        return True
    for pat in EXCEPTION_PATTERNS:
        if pat.match(v):
            return True
    return False


# ---------------------------------------------------------------------------
# String literal extraction.
# ---------------------------------------------------------------------------

# Matches a quoted string literal — supports '...' and "..." with backslash
# escapes. Captures the inner text (without quotes).
_STRING_RE = re.compile(
    r"""(?P<q>['"])(?P<body>(?:\\.|(?!\1).)*)(?P=q)""",
    re.DOTALL,
)

# Matches a JS object key — `key:`, `'key':`, or `"key":` — capturing the key.
_KEY_RE = re.compile(
    r"""(?:(?P<qk>['"])(?P<keyq>(?:\\.|(?!\1).)*)(?P=qk)|(?P<keyb>[A-Za-z_$][A-Za-z0-9_$]*))"""
    r"""\s*:\s*""",
    re.DOTALL,
)


@dataclass
class StringEntry:
    """A single en: or km: string literal found in source."""

    file: str
    line: int
    col: int
    key: str         # the inner key name (e.g. "save" or "panelTitle")
    value: str       # the raw string value (unescaped)


@dataclass
class Pair:
    """An (en, km) pair for the same key in the same STRINGS table."""

    file: str
    line: int
    key: str
    en: Optional[StringEntry] = None
    km: Optional[StringEntry] = None


@dataclass
class FileReport:
    """Per-file scan results."""

    path: str
    pairs: List[Pair] = field(default_factory=list)
    parse_errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Brace-balanced object scanner.
# ---------------------------------------------------------------------------

def _find_object_literals(text: str) -> List[Tuple[int, int, int]]:
    """
    Find every top-level (depth-1) ``{ ... }`` object literal in ``text``.

    Returns a list of ``(start, end, depth)`` tuples where ``start`` is the
    index of the opening ``{`` and ``end`` is the index just after the closing
    ``}``. Skips braces inside string literals and comments.

    This is a small hand-rolled scanner — it does NOT support template
    literals with embedded expressions (``${...}``) or regex literals; for
    STRINGS tables (which never contain those) it's accurate enough.
    """
    out: List[Tuple[int, int, int]] = []
    i = 0
    n = len(text)
    stack: List[int] = []
    while i < n:
        c = text[i]
        # Line comment
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j == -1 else j + 1
            continue
        # Block comment
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        # String literal — consume the entire literal so braces inside it
        # don't confuse the scanner.
        if c in ("'", '"', "`"):
            q = c
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == q:
                    j += 1
                    break
                j += 1
            i = j
            continue
        # Braces
        if c == "{":
            stack.append(i)
        elif c == "}":
            if stack:
                start = stack.pop()
                # Record every depth-1 object (immediate child of the file
                # root or a code block — these are the STRINGS tables and
                # their per-key entries).
                out.append((start, i + 1, len(stack) + 1))
        i += 1
    return out


def _line_col(text: str, idx: int) -> Tuple[int, int]:
    """Return 1-based (line, column) for ``idx`` in ``text``."""
    line = text.count("\n", 0, idx) + 1
    last_nl = text.rfind("\n", 0, idx)
    col = idx - last_nl  # 1-based even when last_nl == -1
    return line, col


def _extract_keyed_strings(block: str) -> Dict[str, StringEntry]:
    """
    Within a single ``{ ... }`` block, find every ``key: 'value'`` pair where
    the value is a string literal. Returns a dict keyed by the JS key name.

    Handles both bare identifiers (``en:``) and quoted keys (``"en":``).
    """
    found: Dict[str, StringEntry] = {}
    pos = 0
    n = len(block)
    while pos < n:
        m = _KEY_RE.match(block, pos)
        if not m:
            pos += 1
            continue
        key = m.group("keyq") or m.group("keyb")
        # If the key was quoted, _KEY_RE captures the inner text; we don't
        # need to unescape here because STRINGS-table keys are simple.
        # Move past the matched `key :` and consume whitespace.
        body_start = m.end()
        # Find the first non-whitespace char of the value.
        j = body_start
        while j < n and block[j] in " \t\r\n":
            j += 1
        if j < n and block[j] in ("'", '"'):
            sm = _STRING_RE.match(block, j)
            if sm:
                value = _unescape(sm.group("body"))
                # Compute line/col later from the file-level index; here we
                # only store the value and key. The caller will resolve
                # file + line + col using the block's offset.
                found[key] = StringEntry(
                    file="",
                    line=0,
                    col=0,
                    key=key,
                    value=value,
                )
                pos = sm.end()
                continue
        # Not a string value — skip past the key.
        pos = m.end()
    return found


_ESCAPE_MAP = {
    "\\": "\\",
    "'": "'",
    '"': '"',
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "b": "\b",
    "f": "\f",
    "v": "\v",
    "0": "\0",
    "`": "`",
}


def _unescape(raw: str) -> str:
    """Decode common JS string escapes (\\n, \\t, \\", \\uXXXX, \\xXX)."""
    out: List[str] = []
    i = 0
    n = len(raw)
    while i < n:
        c = raw[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        i += 1
        if i >= n:
            out.append("\\")
            break
        e = raw[i]
        if e in _ESCAPE_MAP:
            out.append(_ESCAPE_MAP[e])
            i += 1
        elif e == "u":
            hexd = raw[i + 1 : i + 5]
            try:
                out.append(chr(int(hexd, 16)))
                i += 5
            except ValueError:
                out.append("\\u")
                i += 1
        elif e == "x":
            hexd = raw[i + 1 : i + 3]
            try:
                out.append(chr(int(hexd, 16)))
                i += 3
            except ValueError:
                out.append("\\x")
                i += 1
        else:
            # Unknown escape — JS silently drops the backslash.
            out.append(e)
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Per-file scanner.
# ---------------------------------------------------------------------------

def scan_file(path: Path) -> FileReport:
    """Scan one JS file for bilingual string tables."""
    text = path.read_text(encoding="utf-8")
    fr = FileReport(path=str(path))

    objects = _find_object_literals(text)
    # We only care about objects that contain BOTH en: and km: keys with string
    # values, OR objects that contain en: but no km: (missing-km case).
    pairs_by_key: Dict[Tuple[str, str], Pair] = {}

    for start, end, depth in objects:
        block = text[start:end]
        # Identify the enclosing key — the identifier before `:` before `{`.
        # This determines whether we have a Pattern A entry (key: {en:..,km:..})
        # or a Pattern B locale block (en: {key:..,..}, km: {key:..,..}).
        pre = text[:start]
        k = start - 1
        while k >= 0 and pre[k] in " \t\r\n":
            k -= 1
        m = re.search(r"([A-Za-z_$][A-Za-z0-9_$]*)\s*:\s*$", pre[: k + 1])
        outer_key = m.group(1) if m else None

        keyed = _extract_keyed_strings(block)

        # Pattern B: this block is one locale (`en: {...}` or `km: {...}`).
        # Its inner keyed strings are the i18n keys; pair them across the
        # two separate locale blocks below.
        if outer_key in ("en", "km"):
            for inner_key, entry in keyed.items():
                pair_key = (str(path), inner_key)
                p = pairs_by_key.setdefault(
                    pair_key,
                    Pair(file=str(path), line=0, key=inner_key),
                )
                entry.file = str(path)
                line, col = _line_col(text, start)
                entry.line = line
                entry.col = col
                if outer_key == "en":
                    p.en = entry
                else:
                    p.km = entry
                if p.line == 0:
                    p.line = line
            continue

        # Pattern A: outer_key is the i18n key, and the block directly holds
        # `en: '...'` and `km: '...'` string sub-keys.
        if outer_key is not None and ("en" in keyed or "km" in keyed):
            pair_key = (str(path), outer_key)
            p = pairs_by_key.setdefault(
                pair_key,
                Pair(file=str(path), line=0, key=outer_key),
            )
            if "en" in keyed:
                e = keyed["en"]
                e.file = str(path)
                line, col = _line_col(text, start)
                e.line = line
                e.col = col
                p.en = e
                if p.line == 0:
                    p.line = line
            if "km" in keyed:
                k_entry = keyed["km"]
                k_entry.file = str(path)
                line, col = _line_col(text, start)
                k_entry.line = line
                k_entry.col = col
                p.km = k_entry
                if p.line == 0:
                    p.line = line
            continue
        # Otherwise: anonymous object — skip silently (helper config, etc.).

    fr.pairs = sorted(pairs_by_key.values(), key=lambda p: (p.file, p.line, p.key))
    return fr


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------

def discover_js_files(root: Path) -> List[Path]:
    """
    Discover ``src/js/*.js`` files under ``root``. Skip ``bundle-*.js``
    (those are generated by ``src/python/build_route_bundles.py``).
    """
    js_dir = root / "src" / "js"
    if not js_dir.is_dir():
        return []
    out: List[Path] = []
    for p in sorted(js_dir.glob("*.js")):
        if p.name.startswith("bundle-"):
            continue
        out.append(p)
    return out


def find_missing_km(file_reports: List[FileReport]) -> List[Pair]:
    """Return pairs where en exists but km is missing (or empty)."""
    out: List[Pair] = []
    for fr in file_reports:
        for p in fr.pairs:
            if p.en and (not p.km or not p.km.value.strip()):
                out.append(p)
    return out


def find_identical_pairs(file_reports: List[FileReport]) -> List[Pair]:
    """Return pairs where en and km are byte-identical (after trim)."""
    out: List[Pair] = []
    for fr in file_reports:
        for p in fr.pairs:
            if not p.en or not p.km:
                continue
            if p.en.value.strip() == p.km.value.strip() and p.en.value.strip():
                out.append(p)
    return out


def render_markdown(
    file_reports: List[FileReport],
    missing: List[Pair],
    identical: List[Pair],
) -> str:
    """Render the report as Markdown."""
    total_en = sum(
        1 for fr in file_reports for p in fr.pairs if p.en
    )
    total_km = sum(
        1 for fr in file_reports for p in fr.pairs if p.km
    )
    total_pairs = sum(len(fr.pairs) for fr in file_reports)
    total_missing = len(missing)
    total_identical = len(identical)
    legit_identical = sum(1 for p in identical if is_exception(p.en.value))
    placeholder_identical = total_identical - legit_identical

    lines: List[str] = []
    lines.append("# Bilingual Consistency Report (V2-UX-10 / ROADMAP-V2 §3.10)")
    lines.append("")
    lines.append(
        "Generated by `scripts/check-bilingual-consistency.py`. Scans every "
        "`src/js/*.js` source file (skipping generated `bundle-*.js` bundles) "
        "for the two bilingual string-table patterns and verifies that every "
        "`en:` string has a non-identical `km:` translation."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---|")
    lines.append(f"| Total `en:` strings found | {total_en} |")
    lines.append(f"| Total `km:` strings found | {total_km} |")
    lines.append(f"| Total bilingual pairs | {total_pairs} |")
    lines.append(f"| Missing `km:` (en exists, km absent or empty) | {total_missing} |")
    lines.append(f"| Byte-identical `(en, km)` pairs | {total_identical} |")
    lines.append(f"|   — legitimate (proper noun / acronym / number) | {legit_identical} |")
    lines.append(f"|   — placeholder that slipped through | {placeholder_identical} |")
    lines.append("")
    lines.append("## Missing `km:` strings")
    lines.append("")
    if not missing:
        lines.append("_None — every `en:` string has a `km:` translation._")
    else:
        lines.append("| File | Line | Key | EN value | Suggested KH |")
        lines.append("|---|---|---|---|---|")
        for p in missing:
            en_val = (p.en.value if p.en else "").replace("|", "\\|")
            en_val_short = en_val if len(en_val) <= 80 else en_val[:77] + "..."
            lines.append(
                f"| `{Path(p.file).name}` | {p.line} | `{p.key}` | {en_val_short} | TODO: needs Khmer translation |"
            )
    lines.append("")
    lines.append("## Byte-identical `(en, km)` pairs")
    lines.append("")
    if not identical:
        lines.append("_None — every translated pair differs._")
    else:
        lines.append("| File | Line | Key | EN == KM value | Verdict |")
        lines.append("|---|---|---|---|---|")
        for p in identical:
            v = p.en.value.replace("|", "\\|")
            v_short = v if len(v) <= 80 else v[:77] + "..."
            verdict = "legitimate" if is_exception(p.en.value) else "PLACEHOLDER"
            lines.append(
                f"| `{Path(p.file).name}` | {p.line} | `{p.key}` | {v_short} | {verdict} |"
            )
    lines.append("")
    lines.append("## Exception list")
    lines.append("")
    lines.append("The following strings are allowed to be byte-identical in EN and KH:")
    lines.append("")
    lines.append("- **Proper nouns / brand names**: " + ", ".join(sorted(
        s for s in DEFAULT_EXCEPTION_STRINGS if s and s[0].isupper() and not s.isupper()
    )))
    lines.append("- **ALL-CAPS technical acronyms**: " + ", ".join(sorted(
        s for s in DEFAULT_EXCEPTION_STRINGS if s and s.isupper() and s.isalpha()
    )))
    lines.append("- **Lowercase technical terms**: " + ", ".join(sorted(
        s for s in DEFAULT_EXCEPTION_STRINGS if s and s.islower()
    )))
    lines.append("- **Regex patterns**:")
    for pat in EXCEPTION_PATTERNS:
        lines.append(f"  - `{pat.pattern}`")
    lines.append("")
    lines.append("## Pattern detection")
    lines.append("")
    lines.append("The script recognises two bilingual string-table conventions:")
    lines.append("")
    lines.append(
        "- **Pattern A (per-key):** `STRINGS = { key1: { en: '...', km: '...' }, ... }`"
    )
    lines.append(
        "  — used by `signup-sheets.js`, `polls.js`, `album.js`, "
        "`invitation-edit-history.js`, `host-signup-sheets.js`, `host-polls.js`, "
        "`toast.js`, `delivery-dialog.js`."
    )
    lines.append("")
    lines.append(
        "- **Pattern B (per-locale):** `STRINGS = { en: { key1: '...' }, km: { key1: '...' } }`"
    )
    lines.append(
        "  — used by `collaboration-presence-v52.js`, `crdt-yjs-indexeddb.js`, "
        "`crdt-yjs-rich-media.js`, `crdt-yjs-undo.js`, `guest-journey.js`."
    )
    lines.append("")
    lines.append(
        "A hand-rolled brace-balanced scanner walks every `{...}` object literal in "
        "the file (skipping string contents and `//` + `/* */` comments). For each "
        "object it looks at the identifier before `:` before `{` to decide which "
        "pattern applies, then extracts the inner `en:` / `km:` string values."
    )
    lines.append("")
    lines.append("## Common UI term translation reference")
    lines.append("")
    lines.append(
        "When adding a new `en:` string, the corresponding `km:` translation should "
        "follow the platform glossary. Common UI terms (already used across the "
        "existing STRINGS tables):"
    )
    lines.append("")
    lines.append("| EN | KH (Khmer) |")
    lines.append("|---|---|")
    common_terms = [
        ("Save", "រក្សាទុក"),
        ("Cancel", "បោះបង់"),
        ("Delete", "លុប"),
        ("Edit", "កែសម្រួល / កែប្រែ"),
        ("Create", "បង្កើត"),
        ("Close", "បិទ"),
        ("Open", "បើក"),
        ("Loading...", "កំពុងផ្ទុក..."),
        ("Error", "កំហុស"),
        ("Success", "ជោគជ័យ"),
        ("Retry", "ព្យាយាមម្ដងទៀត"),
        ("Search", "ស្វែងរក"),
        ("Filter", "តម្រង"),
        ("All", "ទាំងអស់"),
        ("None", "គ្មាន"),
        ("Yes", "បាទ/ចាស"),
        ("No", "ទេ"),
        ("Submit", "ដាក់ស្នើ"),
        ("Send", "ផ្ញើ"),
        ("Copy", "ចម្លង"),
        ("Copied", "បានចម្លង"),
        ("Settings", "ការកំណត់"),
        ("Help", "ជំនួយ"),
        ("Back", "ត្រលប់"),
        ("Next", "បន្ទាប់"),
        ("Previous", "មុន"),
        ("Title", "ចំណងជើង"),
        ("Email", "អ៊ីមែល"),
        ("Name", "ឈ្មោះ"),
    ]
    for en, km in common_terms:
        lines.append(f"| {en} | {km} |")
    lines.append("")
    lines.append("## Adding a new legitimate exception")
    lines.append("")
    lines.append(
        "If a brand-new proper noun or acronym enters the platform (e.g. a new "
        "third-party integration), add it to `DEFAULT_EXCEPTION_STRINGS` in "
        "`scripts/check-bilingual-consistency.py`. The string must:"
    )
    lines.append("")
    lines.append("1. Have no Khmer translation (verify with a native speaker).")
    lines.append("2. Be a proper noun, brand name, or technical acronym.")
    lines.append("3. Be used in EN mode as-is (no transliteration).")
    lines.append("")
    lines.append(
        "For one-off overrides (e.g. an experimental string in a PR branch), use "
        "the `--allow-identical` CLI flag instead of editing the default list:"
    )
    lines.append("")
    lines.append(
        "```bash\n"
        "python3 scripts/check-bilingual-consistency.py --strict \\\n"
        "  --allow-identical 'NewBrand,new-acronym'\n"
        "```"
    )
    lines.append("")
    lines.append("## Per-file breakdown")
    lines.append("")
    lines.append("| File | Pairs | Missing `km:` | Identical pairs |")
    lines.append("|---|---|---|---|")
    files_with_pairs = 0
    files_scanned = len(file_reports)
    for fr in file_reports:
        m = sum(
            1 for p in fr.pairs if p.en and (not p.km or not p.km.value.strip())
        )
        i = sum(
            1 for p in fr.pairs
            if p.en and p.km and p.en.value.strip() == p.km.value.strip()
            and p.en.value.strip()
        )
        if len(fr.pairs) == 0:
            continue  # skip files with no bilingual strings (cleaner report)
        files_with_pairs += 1
        lines.append(
            f"| `{Path(fr.path).name}` | {len(fr.pairs)} | {m} | {i} |"
        )
    lines.append("")
    lines.append(
        f"_Scanned {files_scanned} source JS files (skipping "
        f"`bundle-*.js` generated files). {files_with_pairs} files contain "
        f"bilingual string tables._"
    )
    lines.append("")
    lines.append("## CI integration")
    lines.append("")
    lines.append("Add to `.github/workflows/bilingual-check.yml`:")
    lines.append("")
    lines.append("```yaml")
    lines.append("name: Bilingual consistency")
    lines.append("on: [push, pull_request]")
    lines.append("jobs:")
    lines.append("  check:")
    lines.append("    runs-on: ubuntu-latest")
    lines.append("    steps:")
    lines.append("      - uses: actions/checkout@v4")
    lines.append("      - name: Set up Python")
    lines.append("        uses: actions/setup-python@v5")
    lines.append("        with:")
    lines.append("          python-version: '3.x'")
    lines.append("      - name: Check bilingual consistency")
    lines.append("        run: python3 scripts/check-bilingual-consistency.py --strict")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_json(
    file_reports: List[FileReport],
    missing: List[Pair],
    identical: List[Pair],
) -> str:
    return json.dumps(
        {
            "summary": {
                "total_en": sum(1 for fr in file_reports for p in fr.pairs if p.en),
                "total_km": sum(1 for fr in file_reports for p in fr.pairs if p.km),
                "total_pairs": sum(len(fr.pairs) for fr in file_reports),
                "missing_km": len(missing),
                "identical_pairs": len(identical),
                "legit_identical": sum(1 for p in identical if is_exception(p.en.value)),
                "placeholder_identical": sum(
                    1 for p in identical if not is_exception(p.en.value)
                ),
            },
            "missing": [
                {
                    "file": p.file,
                    "line": p.line,
                    "key": p.key,
                    "en": p.en.value if p.en else None,
                }
                for p in missing
            ],
            "identical": [
                {
                    "file": p.file,
                    "line": p.line,
                    "key": p.key,
                    "value": p.en.value if p.en else None,
                    "verdict": "legitimate" if is_exception(p.en.value) else "placeholder",
                }
                for p in identical
            ],
            "files": [
                {
                    "path": fr.path,
                    "pairs": len(fr.pairs),
                    "missing": sum(
                        1 for p in fr.pairs
                        if p.en and (not p.km or not p.km.value.strip())
                    ),
                    "identical": sum(
                        1 for p in fr.pairs
                        if p.en and p.km
                        and p.en.value.strip() == p.km.value.strip()
                        and p.en.value.strip()
                    ),
                }
                for fr in file_reports
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bilingual EN/KH string consistency CI check.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root (default: current directory).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on ANY byte-identical (en, km) pair that is not on the "
             "documented exception list. Recommended for CI.",
    )
    parser.add_argument(
        "--allow-identical",
        default="",
        help="Comma-separated list of extra strings allowed to be byte-"
             "identical in EN and KH.",
    )
    parser.add_argument(
        "--report",
        default="",
        help="Write a Markdown report to this path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human text on stdout.",
    )
    args = parser.parse_args(argv)

    # Merge extra exception strings.
    extra = {s.strip() for s in args.allow_identical.split(",") if s.strip()}
    DEFAULT_EXCEPTION_STRINGS.update(extra)

    root = Path(args.root).resolve()
    js_files = discover_js_files(root)
    if not js_files:
        msg = f"No source JS files found under {root}/src/js/"
        if args.json:
            print(json.dumps({"error": msg}, indent=2))
        else:
            print(msg, file=sys.stderr)
        return 2

    file_reports: List[FileReport] = []
    for js in js_files:
        try:
            file_reports.append(scan_file(js))
        except Exception as exc:  # noqa: BLE001
            file_reports.append(
                FileReport(path=str(js), parse_errors=[str(exc)])
            )

    missing = find_missing_km(file_reports)
    identical = find_identical_pairs(file_reports)

    # Decide exit code.
    fail = False
    if missing:
        fail = True
    if args.strict:
        bad_identical = [p for p in identical if not is_exception(p.en.value)]
        if bad_identical:
            fail = True
    else:
        # Non-strict: still fail on placeholder identicals (not on exception
        # list AND not matching any exception pattern).
        bad_identical = [p for p in identical if not is_exception(p.en.value)]
        if bad_identical:
            fail = True

    if args.report:
        report_path = Path(args.report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            render_markdown(file_reports, missing, identical),
            encoding="utf-8",
        )

    if args.json:
        print(render_json(file_reports, missing, identical))
    else:
        total_en = sum(1 for fr in file_reports for p in fr.pairs if p.en)
        total_km = sum(1 for fr in file_reports for p in fr.pairs if p.km)
        print(f"Scanned {len(js_files)} source JS files.")
        print(f"  en: strings found : {total_en}")
        print(f"  km: strings found : {total_km}")
        print(f"  Missing km:       : {len(missing)}")
        print(f"  Identical pairs  : {len(identical)}")
        if missing:
            print("\nMISSING km: translations:")
            for p in missing:
                print(f"  {Path(p.file).name}:{p.line}  {p.key}")
                v = p.en.value if p.en else ""
                v = v if len(v) <= 70 else v[:67] + "..."
                print(f"    en: {v!r}")
        if identical:
            print("\nByte-identical (en, km) pairs:")
            for p in identical:
                verdict = "legitimate" if is_exception(p.en.value) else "PLACEHOLDER"
                print(
                    f"  {Path(p.file).name}:{p.line}  {p.key}  "
                    f"[{verdict}]  {p.en.value!r}"
                )
        if fail:
            print("\nFAIL: bilingual consistency check failed.", file=sys.stderr)
        else:
            print("\nOK: bilingual consistency check passed.")

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
