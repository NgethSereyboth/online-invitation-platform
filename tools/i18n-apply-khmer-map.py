#!/usr/bin/env python3
"""i18n-apply-khmer-map.py — apply docs/i18n/KHMER-TRANSLATION-MAP-*.md to source.

FB-54 of FREEBUFF-REFINEMENT-ORDER-ROUND4-2026-10-23.md.  The map is the ONLY source
of Khmer: this script never contains a Khmer literal, it reads the file as UTF-8 and
copies the `KM` cell of each table row into src/.

Shapes handled
--------------
  *_txt(en, km), _html(en, km), b(en, km), langText(en, km)   (JS helper calls)
  STRINGS = { en: {key: '...'}, km: {key: '...'} }            (per-locale tables)
  <span class="... i18n-km ...">text</span>                   (src/html)
  data-km="..." / data-i18n-km="..."                          (src/html)

Modes
-----
  default     apply and report
  --dry-run   report only, write nothing
  --verify    re-read every applied (file, row) pair and assert the map's KM column is
              present byte-for-byte; prints VERIFIED n/n

Matching rules (map §0)
-----------------------
  * rows are matched by (file, EN) after trimming; JS escapes are decoded first
  * helper calls / HTML slots are only rewritten when their km value is still the
    English (a `fallback`); §3 key repairs rewrite the km value at the named key
  * the source's own leading/trailing whitespace is preserved around the new value
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = ROOT / "docs" / "i18n" / "KHMER-TRANSLATION-MAP-2026-10-24.md"
SKIP_DIRS = {"python"}  # src/python/* is a generated mirror; build.py copies src/js|html


# ---------------------------------------------------------------------------
# Map parsing
# ---------------------------------------------------------------------------

@dataclass
class Row:
    section: str            # "3-key" | "3-label" | "4" | "6"
    file: str               # repo-relative path ("" for the global label table)
    en: str
    km: str = ""
    find: str = ""
    replace: str = ""
    keys: tuple = ()
    index: int = 0


def parse_map(path: Path) -> list[Row]:
    text = path.read_text(encoding="utf-8")
    rows: list[Row] = []
    section = ""
    current_file = ""
    current_keys: tuple = ()
    idx = 0
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            m = re.match(r"## (\d+)\.", line)
            num = m.group(1) if m else ""
            if num == "3":
                section = "3"
            elif num == "4":
                section = "4"
                fm = re.search(r"`([^`]+\.(?:js|html))`", line)
                current_file = fm.group(1) if fm else ""
                current_keys = ()
            elif num == "6":
                section = "6"
                current_file = ""
            else:
                section = ""
            continue
        if line.startswith("### "):
            fm = re.search(r"`([^`]+\.(?:js|html))`", line)
            if fm:
                current_file = fm.group(1)
                km = re.search(r"\(keys? ((?:`[^`]+`(?:,\s*)?)+)\)", line)
                current_keys = tuple(re.findall(r"`([^`]+)`", km.group(1))) if km else ()
            else:
                # e.g. "### Wrong rail labels and other wrong terms — exact find → replace"
                current_file = ""
                current_keys = ()
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or set(cells[0]) <= set("-: "):
            continue
        if cells[0] in ("EN", "Where", "Where | EN"):
            continue
        if section == "3":
            if len(cells) >= 3 and not current_file:
                # global find -> replace table (EN | find | replace)
                rows.append(Row("3-label", "", cells[0], find=cells[1], replace=cells[2],
                                index=idx))
                idx += 1
            elif len(cells) >= 2 and current_file:
                rows.append(Row("3-key" if current_keys else "6", current_file,
                                cells[0], km=cells[1], keys=current_keys, index=idx))
                idx += 1
        elif section == "4" and current_file and len(cells) >= 2:
            rows.append(Row("4", current_file, cells[0], km=cells[1],
                            keys=current_keys, index=idx))
            idx += 1
        elif section == "6" and current_file and len(cells) >= 2:
            rows.append(Row("6", current_file, cells[0], km=cells[1], index=idx))
            idx += 1
    return rows


# ---------------------------------------------------------------------------
# JS string literal decoding / encoding
# ---------------------------------------------------------------------------

_SIMPLE = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v",
           "0": "\0", "\\": "\\", "'": "'", '"': '"', "`": "`"}


def js_decode(raw: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch != "\\" or i + 1 >= len(raw):
            out.append(ch)
            i += 1
            continue
        nxt = raw[i + 1]
        if nxt in _SIMPLE:
            out.append(_SIMPLE[nxt])
            i += 2
        elif nxt == "x" and i + 3 < len(raw):
            out.append(chr(int(raw[i + 2:i + 4], 16)))
            i += 4
        elif nxt == "u" and i + 2 < len(raw) and raw[i + 2] == "{":
            end = raw.find("}", i + 3)
            out.append(chr(int(raw[i + 3:end], 16)))
            i = end + 1
        elif nxt == "u" and i + 5 < len(raw):
            out.append(chr(int(raw[i + 2:i + 6], 16)))
            i += 6
        else:
            out.append(nxt)
            i += 2
    return "".join(out)


def js_encode(value: str, quote: str) -> str:
    out: list[str] = []
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == quote:
            out.append("\\" + quote)
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    return "".join(out)


def keep_edges(original: str, replacement: str) -> str:
    """Preserve the source literal's leading/trailing whitespace around the new value."""
    lead = original[:len(original) - len(original.lstrip())]
    trail = original[len(original.rstrip()):]
    return f"{lead}{replacement.strip()}{trail}"


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

HELPER_RE = re.compile(
    r"(?<![\w$])(?P<fn>_txt|_html|langText|b)\s*\(\s*"
    r"(?P<q1>['\"])(?P<en>(?:\\.|(?!(?P=q1)).)*)(?P=q1)\s*,\s*"
    r"(?P<q2>['\"])(?P<km>(?:\\.|(?!(?P=q2)).)*)(?P=q2)",
    re.DOTALL,
)
KM_SPAN_RE = re.compile(
    r'(?P<open><(?P<tag>[a-zA-Z][\w-]*)\b[^>]*class="[^"]*\bi18n-km\b[^"]*"[^>]*>)'
    r"(?P<body>.*?)"
    r"(?P<close></(?P=tag)\s*>)",
    re.DOTALL,
)
KM_ATTR_RE = re.compile(r'(?P<pre>\bdata-(?:i18n-)?km=")(?P<body>[^"]*)(?P<post>")')
PAIR_RE = re.compile(r"([A-Za-z_$][\w$]*)\s*:\s*(['\"])((?:\\.|(?!\2).)*)\2", re.DOTALL)
HTML_PAIR_RE = re.compile(
    r'<span[^>]*class="[^"]*\bi18n-en\b[^"]*"[^>]*>(?P<en>.*?)</span>\s*'
    r'<span[^>]*class="[^"]*\bi18n-km\b[^"]*"[^>]*>(?P<km>.*?)</span>',
    re.DOTALL,
)
HTML_ATTR_PAIR_RE = re.compile(
    r'data-(?:i18n-)?en="(?P<en>[^"]*)"[^>]*?data-(?:i18n-)?km="(?P<km>[^"]*)"',
    re.DOTALL,
)


def _find_block(text: str, start: int) -> tuple[int, int] | None:
    """Return the span of the {...} block that begins at/after ``start``."""
    i = text.find("{", start)
    if i < 0:
        return None
    depth = 0
    j = i
    while j < len(text):
        ch = text[j]
        if ch in "\"'`":
            q = ch
            j += 1
            while j < len(text):
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == q:
                    j += 1
                    break
                j += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i, j + 1
        j += 1
    return None


def _strings_tables(text: str) -> tuple[dict, dict] | None:
    """Parse the first ``STRINGS = { en: {...}, km: {...} }`` in a JS module."""
    m = re.search(r"\bSTRINGS\s*=\s*\{", text)
    if not m:
        return None
    span = _find_block(text, m.end() - 1)
    if not span:
        return None
    body = text[span[0]:span[1]]
    tables: list[dict] = []
    for locale in ("en", "km"):
        lm = re.search(rf"\b{locale}\s*:\s*\{{", body)
        if not lm:
            tables.append({})
            continue
        lspan = _find_block(body, lm.end() - 1)
        if not lspan:
            tables.append({})
            continue
        block = body[lspan[0]:lspan[1]]
        base = span[0] + lspan[0]
        entries = {}
        for pm in PAIR_RE.finditer(block):
            entries[pm.group(1)] = (js_decode(pm.group(3)), base + pm.start(3), pm.group(2))
        tables.append(entries)
    return tables[0], tables[1]


@dataclass
class FileState:
    path: Path
    text: str
    applied: int = 0
    rows_applied: set = field(default_factory=set)


def apply_helpers(state: FileState, rows: list[Row]) -> None:
    text = state.text
    matches = list(HELPER_RE.finditer(text))
    edits: list[tuple[int, int, str]] = []
    for m in matches:
        en = js_decode(m.group("en"))
        km = js_decode(m.group("km"))
        key = en.strip()
        for row in rows:
            if row.en.strip() != key:
                continue
            if km.strip() != key:
                continue
            quote = m.group("q2")
            new = js_encode(keep_edges(km, row.km), quote)
            edits.append((m.start("km"), m.end("km"), new))
            state.rows_applied.add(row.index)
    for start, end, new in sorted(edits, reverse=True):
        state.text = state.text[:start] + new + state.text[end:]
    state.applied += len(edits)


def apply_strings_table(state: FileState, rows: list[Row]) -> None:
    tables = _strings_tables(state.text)
    if not tables:
        return
    en_tab, km_tab = tables
    edits: list[tuple[int, int, str]] = []
    for row in rows:
        # §4: find the key whose EN value is this row's English.
        key = None
        for k, (val, _pos, _q) in en_tab.items():
            if val.strip() == row.en.strip():
                key = k
                break
        if key is None and row.keys:
            key = row.keys[0]
        if key is None or key not in km_tab:
            continue
        cur, pos, quote = km_tab[key]
        if row.section == "6" and cur.strip() != row.en.strip():
            continue
        new = js_encode(keep_edges(cur, row.km), quote)
        edits.append((pos, pos + len(cur), new))
        state.rows_applied.add(row.index)
        # keep the parsed table in sync so a second row cannot double-edit
        km_tab[key] = (row.km, pos, quote)
    for start, end, new in sorted(edits, reverse=True):
        state.text = state.text[:start] + new + state.text[end:]
    state.applied += len(edits)


def apply_html(state: FileState, rows: list[Row]) -> None:
    edits: list[tuple[int, int, str]] = []
    by_en = {r.en.strip(): r for r in rows}
    for m in KM_SPAN_RE.finditer(state.text):
        body = m.group("body")
        row = by_en.get(body.strip())
        if not row or body != row.en:
            continue
        edits.append((m.start("body"), m.end("body"), row.km))
        state.rows_applied.add(row.index)
    for m in KM_ATTR_RE.finditer(state.text):
        body = m.group("body")
        row = by_en.get(body.strip())
        if not row or body != row.en:
            continue
        edits.append((m.start("body"), m.end("body"), row.km))
        state.rows_applied.add(row.index)
    for start, end, new in sorted(edits, reverse=True):
        state.text = state.text[:start] + new + state.text[end:]
    state.applied += len(edits)


def apply_label_pairs(state: FileState, rows: list[Row]) -> None:
    """Repair a label whose `find` string drifted in the map (match by its English).

    §3 says the km value may be replaced wherever the English next to it matches;
    the Feature-flags row's `find` cell carries one extra letter and never appears
    in source, but the tab label still needs the map's replacement.
    """
    if not rows:
        return
    edits: list[tuple[int, int, str]] = []
    for m in HTML_PAIR_RE.finditer(state.text):
        en = re.sub(r"<[^>]+>", "", m.group("en")).strip()
        for row in rows:
            label_en = row.en.split(" (")[0].strip()
            if en == label_en and m.group("km") != row.replace:
                edits.append((m.start("km"), m.end("km"), row.replace))
                state.rows_applied.add(row.index)
    for m in HELPER_RE.finditer(state.text):
        en = js_decode(m.group("en")).strip()
        for row in rows:
            label_en = row.en.split(" (")[0].strip()
            if en == label_en and js_decode(m.group("km")) != row.replace:
                new = js_encode(keep_edges(js_decode(m.group("km")), row.replace),
                                m.group("q2"))
                edits.append((m.start("km"), m.end("km"), new))
                state.rows_applied.add(row.index)
    for start, end, new in sorted(edits, reverse=True):
        state.text = state.text[:start] + new + state.text[end:]
    state.applied += len(edits)


def apply_labels(state: FileState, rows: list[Row]) -> int:
    count = 0
    for row in rows:
        if not row.find:
            continue
        n = state.text.count(row.find)
        if n:
            state.text = state.text.replace(row.find, row.replace)
            state.rows_applied.add(row.index)
            count += n
    state.applied += count
    return count


def _head_text(rel: str) -> str | None:
    """The file's text at HEAD — the honest baseline for "what did the map change"."""
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "show", f"HEAD:{rel}"], cwd=ROOT, text=True,
            encoding="utf-8", stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _existing_translation(text: str, en: str, is_html: bool) -> str | None:
    """First non-English km value already written next to this EN in the file."""
    if is_html:
        for m in HTML_PAIR_RE.finditer(text):
            if m.group("en").strip() == en.strip() and m.group("km").strip() != en.strip():
                return m.group("km")
        for m in HTML_ATTR_PAIR_RE.finditer(text):
            if m.group("en").strip() == en.strip() and m.group("km").strip() != en.strip():
                return m.group("km")
        return None
    for m in HELPER_RE.finditer(text):
        source_en = js_decode(m.group("en"))
        km = js_decode(m.group("km"))
        if source_en.strip() == en.strip() and km.strip() != en.strip():
            return km
    tables = _strings_tables(text)
    if tables:
        en_tab, km_tab = tables
        for key, (val, _pos, _q) in en_tab.items():
            if val.strip() == en.strip() and key in km_tab:
                km = km_tab[key][0]
                if km.strip() != en.strip():
                    return km
    return None


def update_csv(csv_path: Path, rows: list[Row], report: dict) -> None:
    """Refresh the ledger by script: a row that has Khmer in source is not a fallback."""
    import csv
    by_key = {(r.file, r.en.strip()): r for r in rows if r.section in ("3-key", "4", "6")}
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        data = [r for r in reader]
    fi, ei, ki, si = (header.index("file"), header.index("en"),
                      header.index("km"), header.index("status"))
    changed = 0
    still_fallback = 0
    for r in data:
        if len(r) <= si or r[si] != "fallback":
            continue
        file, en = r[fi], r[ei]
        map_row = by_key.get((file, en.strip()))
        src = (ROOT / file)
        if map_row is None or not src.is_file():
            still_fallback += 1
            continue
        text = src.read_text(encoding="utf-8")
        if _row_present(text, map_row):
            r[ki] = map_row.km
            r[si] = "translated"
            changed += 1
            continue
        existing = _existing_translation(text, en, file.endswith(".html"))
        if existing is not None:
            r[ki] = existing
            r[si] = "translated"
            changed += 1
            continue
        still_fallback += 1
        report.setdefault("csv_still_fallback", []).append({"file": file, "en": en[:120]})
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\r\n", quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        writer.writerows(data)
    print(f"CSV_UPDATED fallback_to_translated={changed} still_fallback={still_fallback}")


def _row_present(text: str, row: Row) -> bool:
    """True when the file carries this row's KM byte-for-byte next to its EN."""
    if row.file.endswith(".html"):
        for m in HTML_PAIR_RE.finditer(text):
            if m.group("en").strip() == row.en.strip() and m.group("km") == row.km:
                return True
        for m in KM_ATTR_RE.finditer(text):
            if m.group("body") == row.km:
                return True
        return False
    for m in HELPER_RE.finditer(text):
        if js_decode(m.group("en")).strip() != row.en.strip():
            continue
        if js_decode(m.group("km")) == row.km:
            return True
    tables = _strings_tables(text)
    if tables:
        en_tab, km_tab = tables
        for key, (val, _pos, _q) in en_tab.items():
            if val.strip() != row.en.strip() or key not in km_tab:
                continue
            if km_tab[key][0] == row.km:
                return True
    return False


def source_files() -> list[Path]:
    out = []
    for base in ("js", "html"):
        for p in sorted((ROOT / "src" / base).rglob("*")):
            if not p.is_file() or p.suffix not in (".js", ".html"):
                continue
            if p.name.startswith("bundle-"):
                continue
            if p.relative_to(ROOT / "src").parts[0] in SKIP_DIRS:
                continue
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Apply the Khmer translation map to src/.")
    ap.add_argument("--map", default=str(DEFAULT_MAP))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--report", default="")
    ap.add_argument("--update-csv", action="store_true",
                    help="refresh docs/i18n/TRANSLATIONS.csv fallback rows from source")
    args = ap.parse_args(argv)

    rows = parse_map(Path(args.map))
    by_file: dict[str, list[Row]] = {}
    label_rows: list[Row] = []
    for row in rows:
        if row.section == "3-label":
            label_rows.append(row)
        else:
            by_file.setdefault(row.file, []).append(row)

    files = {p.relative_to(ROOT).as_posix(): p for p in source_files()}
    report = {
        "map": str(Path(args.map).relative_to(ROOT)),
        "parsed": len(rows),
        "files": {},
        "mismatches": [],
        "applied_total": 0,
        "verified": 0,
    }

    states: dict[str, FileState] = {}
    for rel, file_rows in sorted(by_file.items()):
        path = files.get(rel)
        if not path:
            for row in file_rows:
                report["mismatches"].append(
                    {"file": rel, "en": row.en, "reason": "file not found"})
            continue
        state = FileState(path, path.read_text(encoding="utf-8"))
        repairs = [r for r in file_rows if r.section in ("3-key", "4")]
        fallbacks = [r for r in file_rows if r.section == "6"]
        if rel.endswith(".html"):
            apply_html(state, repairs + fallbacks)
        else:
            if repairs:
                apply_strings_table(state, repairs)
            if fallbacks:
                apply_helpers(state, fallbacks)
                apply_strings_table(state, fallbacks)
        # Specific rows first so "Stored materials" wins over the generic label.
        if label_rows:
            specific = [r for r in label_rows if r.en.split("(")[-1].split(")")[0].endswith(
                Path(rel).name)]
            generic = [r for r in label_rows if r not in specific]
            apply_labels(state, specific)
            apply_labels(state, generic)
            apply_label_pairs(state, label_rows)
        applied_rows = [r for r in file_rows if r.index in state.rows_applied]
        for row in file_rows:
            if row.index not in state.rows_applied:
                report["mismatches"].append(
                    {"file": rel, "en": row.en,
                     "reason": "no fallback occurrence in this file"})
        states[rel] = state
        report["files"][rel] = {"applied": state.applied,
                                "rows": len(applied_rows),
                                "rows_total": len(file_rows)}
        report["applied_total"] += state.applied

    if label_rows and not by_file:
        # No file rows: still report unmatched global labels.
        pass
    unapplied_labels = [r for r in label_rows
                        if all(r.index not in s.rows_applied for s in states.values())]
    for row in unapplied_labels:
        report["mismatches"].append(
            {"file": "(global)", "en": row.en,
             "reason": "find string not present in src/js|src/html"})

    if not args.dry_run and not args.verify:
        for rel, state in states.items():
            if state.text != state.path.read_text(encoding="utf-8"):
                state.path.write_text(state.text, encoding="utf-8")

    if args.verify or not args.dry_run:
        total = 0
        ok = 0
        for rel, file_rows in sorted(by_file.items()):
            text = files[rel].read_text(encoding="utf-8")
            head = _head_text(rel)
            if head is None:
                continue
            sim = FileState(files[rel], head)
            fallbacks = [r for r in file_rows if r.section == "6"]
            repairs = [r for r in file_rows if r.section in ("3-key", "4")]
            if rel.endswith(".html"):
                apply_html(sim, repairs + fallbacks)
            else:
                if repairs:
                    apply_strings_table(sim, repairs)
                if fallbacks:
                    apply_helpers(sim, fallbacks)
                    apply_strings_table(sim, fallbacks)
            for row in file_rows:
                if row.index not in sim.rows_applied:
                    continue
                total += 1
                if _row_present(text, row):
                    ok += 1
                else:
                    report["mismatches"].append(
                        {"file": rel, "en": row.en, "reason": "post-apply byte check failed"})
        report["verified"] = ok
        report["verify_total"] = total
        print(f"VERIFIED {ok}/{total}")

    print(f"PARSED {report['parsed']} rows from {Path(args.map).name}")
    print(f"MATCHED {sum(1 for f in report['files'].values() if f['rows'])} files, "
          f"{sum(f['rows'] for f in report['files'].values())} rows")
    print(f"APPLIED {report['applied_total']} string occurrences")
    print(f"MISMATCHED {len(report['mismatches'])} rows (listed in the report)")
    for rel, info in sorted(report["files"].items()):
        print(f"  {rel}: {info['applied']} occurrences, {info['rows']}/{info['rows_total']} rows")
    if args.update_csv and not args.dry_run:
        update_csv(ROOT / "docs" / "i18n" / "TRANSLATIONS.csv", rows, report)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    if args.dry_run:
        print("DRY-RUN: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
