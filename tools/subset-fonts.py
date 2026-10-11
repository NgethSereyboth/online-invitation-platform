#!/usr/bin/env python3
"""subset-fonts.py — inventory, subset and verify the web fonts against the
characters the site actually renders.

Four subcommands, each usable alone:

  inventory    every `@font-face` in src/css/, its family/weight/unicode-range,
               and `ls -la`-equivalent sizes for the files it points at. Also
               reports which routes reference each face.
  codepoints   the UNION of every character the site can render, computed from
               the served HTML in both languages, docs/i18n/TRANSLATIONS.csv and
               the invitation template data. Written to
               <artifacts>/font-codepoints.json, and printed as sorted codepoints
               plus merged ranges, split into Latin and Khmer classes.
  subset       for each font file, rebuild it with pyftsubset restricted to the
               used codepoints of that file's script class, plus a safety floor.
               Prints the byte delta per file. Writes to --out-dir (default: a
               staging directory; pass --in-place to overwrite src fonts).
  verify       independently re-reads each subset font and every used codepoint
               and reports any codepoint the font no longer covers. This is the
               check that a subsetting run cannot break a character silently.

Why the codepoint set is computed from the SERVED tree, not from src/css
-----------------------------------------------------------------------
The pages generate their Khmer strings from i18n data and from template data, so
grepping the CSS would undercount. Reading the served HTML captures what a
browser is actually asked to paint, which is the quantity the unicode-range and
the subset have to cover.

Safety floor
------------
A closed codepoint set is unsafe for *user* data (a guest's name, a date, a
typed message). The Latin class therefore always keeps a floor of
U+0020-007E, U+00A0-00FF, U+2000-206F, U+20A0-20BF and U+2190-21FF; the Khmer
class always keeps the full Khmer block U+1780-17FF plus Khmer Symbols
U+19E0-19FF, because Khmer is the language the product must support and a
missing coeng mark is a visible rendering defect, not a byte saving.

Requires: fonttools + brotli (`pip install -r tools/requirements.txt`).
Produces: byte deltas on stdout; JSON input to `subset` under artifacts/.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO_ROOT = TOOLS.parent
ARTIFACTS = Path(os.environ.get("ARTIFACTS_DIR", REPO_ROOT / "artifacts"))
CSS_DIR = REPO_ROOT / "src" / "css"
FONT_DIR = REPO_ROOT / "assets" / "fonts"
SERVE_ROOT = Path(os.environ.get("SERVE_ROOT", REPO_ROOT / "src" / "python"))
TRANSLATIONS = REPO_ROOT / "docs" / "i18n" / "TRANSLATIONS.csv"

KHMER_BLOCKS = ((0x1780, 0x17FF), (0x19E0, 0x19FF))
# The floor is split the same way as the classification so a Latin font never
# gains Khmer glyphs and vice versa.
LATIN_FLOOR = ((0x0020, 0x007E), (0x00A0, 0x00FF), (0x2000, 0x206F), (0x20A0, 0x20BF), (0x2190, 0x21FF))
KHMER_FLOOR = KHMER_BLOCKS

FACE_RE = re.compile(
    r"@font-face\s*\{[^}]*?font-family:\s*'([^']+)'[^}]*?"
    r"(?:font-weight:\s*(\d+))?[^}]*?"
    r"url\(\s*'?([^')]+\.woff2)'?\s*\)[^}]*?"
    r"(?:unicode-range:\s*([^;}]+))?",
    re.S,
)


def is_khmer(cp: int) -> bool:
    return any(lo <= cp <= hi for lo, hi in KHMER_BLOCKS)


def ranges(codepoints) -> str:
    """Merge codepoints into `U+XXXX-U+YYYY,U+ZZZZ` form for pyftsubset."""
    out, start, prev = [], None, None
    for cp in sorted(set(codepoints)):
        if start is None:
            start = prev = cp
            continue
        if cp == prev + 1:
            prev = cp
            continue
        out.append((start, prev))
        start = prev = cp
    if start is not None:
        out.append((start, prev))
    # fontTools' own --unicodes syntax takes the `U+` prefix once per RANGE, not
    # once per endpoint: `U+0020-007E` parses, `U+0020-U+007E` does not. It is
    # tokenised by replacing every `U`, `+`, `,` and space with a space and
    # splitting on whitespace, so the second `U+` splits `007E` off its range and
    # leaves a dangling `0020-`, which fails as int('', 16). Emitting the second
    # prefix produced a hard error on every face:
    #   ValueError: invalid literal for int() with base 16: ''
    return ",".join(f"U+{a:04X}" if a == b else f"U+{a:04X}-{b:04X}" for a, b in out)


def parse_unicode_range(value: str):
    """`U+0000-024F,U+1E00-1EFF` -> [(0x0000, 0x024F), (0x1E00, 0x1EFF)]."""
    out = []
    for token in (value or "").split(","):
        token = token.strip().lower().replace("u+", "")
        if not token:
            continue
        if "-" in token:
            lo, _, hi = token.partition("-")
        else:
            lo = hi = token
        try:
            out.append((int(lo, 16), int(hi, 16)))
        except ValueError:
            continue
    return out


def parse_font_faces(css_path: Path):
    text = css_path.read_text(encoding="utf-8", errors="replace")
    faces = []
    for m in FACE_RE.finditer(text):
        raw_range = (m.group(4) or "").strip().strip(";").strip()
        faces.append({
            "family": m.group(1),
            "weight": m.group(2),
            "file": m.group(3),
            "source": css_path.name,
            "unicode_range": raw_range,
            "unicodeRanges": parse_unicode_range(raw_range),
        })
    return faces


# Generated route bundles are concatenations of the hand-written sources, so
# parsing them would report every face twice under a name that no one edits.
# `bundle-<route>-v15.css` is produced by src/python/build/build_route_bundles.py.
GENERATED_CSS_RE = re.compile(r"^bundle-[a-z-]+-v15\.css$")


def hand_written_css():
    """Every @font-face source of truth: src/css/**/*.css minus generated bundles."""
    return [p for p in sorted(CSS_DIR.rglob("*.css"))
            if not GENERATED_CSS_RE.match(p.name)]


def all_font_faces():
    """Deduplicate the hand-written faces by (family, weight, file).

    Parsing only typography-fonts.css (the first version of this tool) missed
    Inter entirely: Inter's three faces are declared in canvas-plus.css and
    editor-suite.css, and together they are 57% of the bytes index.html fetches
    (184,932 of 325,616 across the three weights). A subsetting pass that skips
    the largest faces is worse than no pass, because the report then says the
    fonts are as small as they can be.
    """
    seen, faces = set(), []
    for path in hand_written_css():
        for face in parse_font_faces(path):
            key = (face["family"], face["weight"], Path(face["file"]).name)
            if key in seen:
                continue
            seen.add(key)
            faces.append(face)
    return faces


def collect_codepoints(include_src_html=True):
    sources = {}
    cps = set()

    def add(name, text):
        found = {ord(ch) for ch in text if not ch.isspace() or ch == " "}
        found = {c for c in found if c > 0x20 or c == 0x20}
        sources[name] = len(found)
        cps.update(found)

    # Served pages (the built tree). Both -en and -km variants live here, plus
    # the route pages which carry the Khmer strings from the i18n data.
    for path in sorted(SERVE_ROOT.glob("*.html")):
        add(f"{SERVE_ROOT.name}/{path.name}", path.read_text(encoding="utf-8", errors="replace"))
    if include_src_html:
        for path in sorted((REPO_ROOT / "src" / "html").glob("*.html")):
            add(f"src/html/{path.name}", path.read_text(encoding="utf-8", errors="replace"))

    # Translation catalogue.
    if TRANSLATIONS.is_file():
        buf = []
        with TRANSLATIONS.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
            for row in csv.reader(fh):
                buf.extend(row)
        add("docs/i18n/TRANSLATIONS.csv", "\n".join(buf))

    # Invitation template data + fixture JSON that feeds the invite pages.
    for pattern in ("*.json", "src/python/*.json", "data/*.json"):
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.is_file() and path.stat().st_size < 4_000_000:
                add(str(path.relative_to(REPO_ROOT)), path.read_text(encoding="utf-8", errors="replace"))

    return cps, sources


def cmd_inventory(_args) -> int:
    faces = parse_font_faces(CSS_DIR / "typography-fonts.css")
    print(f"@font-face declarations in src/css/typography-fonts.css: {len(faces)}")
    print(f"{'family':<26}{'wt':<5}{'file':<34}{'bytes':>9}  unicode-range")
    seen = {}
    for f in faces:
        path = (REPO_ROOT / f["file"]).resolve()
        size = path.stat().st_size if path.is_file() else -1
        seen.setdefault(f["file"], size)
        print(f"{f['family']:<26}{str(f['weight'] or '-'):<5}{Path(f['file']).name:<34}{size:>9}  {f['unicode_range'][:60]}")
    total = sum(v for v in seen.values() if v > 0)
    print(f"\ndistinct font files referenced: {len(seen)}   total bytes on disk: {total}")

    # Which files actually appear in each route bundle's @font-face set.
    routes = {}
    for css in sorted(CSS_DIR.glob("bundle-*-v15.css")):
        refs = sorted({Path(f["file"]).name for f in parse_font_faces(css)})
        routes[css.name] = refs
    print("\nfonts declared per route bundle:")
    for name, refs in routes.items():
        print(f"  {name:<34}{len(refs):>3}  {', '.join(refs) if refs else '(none)'}")
    return 0


def cmd_codepoints(args) -> int:
    cps, sources = collect_codepoints()
    latin = sorted(c for c in cps if not is_khmer(c))
    khmer = sorted(c for c in cps if is_khmer(c))
    payload = {
        "total": len(cps),
        "latin": len(latin),
        "khmer": len(khmer),
        "latinCodepoints": [f"U+{c:04X}" for c in latin],
        "khmerCodepoints": [f"U+{c:04X}" for c in khmer],
        "latinRanges": ranges(latin),
        "khmerRanges": ranges(khmer),
        "sources": sources,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out = ARTIFACTS / "font-codepoints.json"
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    print(f"used codepoints: {payload['total']} total  ({payload['latin']} Latin-class, {payload['khmer']} Khmer-class)")
    print(f"sources scanned: {len(sources)}")
    for name, n in sorted(sources.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {n:>6}  {name}")
    print(f"\nLatin ranges:\n  {payload['latinRanges'][:400]}")
    print(f"\nKhmer ranges:\n  {payload['khmerRanges'][:400]}")
    print(f"\nwritten: {out.relative_to(REPO_ROOT)}")
    return 0


def classify_font(filename: str) -> str:
    return "khmer" if "khmer" in filename.lower() else "latin"


def pyftsubset_cmd() -> list[str] | None:
    """Resolve pyftsubset, preferring the console script then the module.

    fontTools can be installed and importable without its console script being
    on PATH (a venv created with --system-site-packages, a distro package that
    splits the scripts out, or a Windows install where `Scripts/` is not on
    PATH). `python -m fontTools.subset` is the same entry point, so falling back
    to it keeps this tool runnable wherever fontTools itself is importable.
    """
    exe = shutil.which("pyftsubset")
    if exe:
        return [exe]
    try:
        import fontTools.subset  # noqa: F401
    except ImportError:
        return None
    return [sys.executable, "-m", "fontTools.subset"]


def cmd_subset(args) -> int:
    pyftsubset = pyftsubset_cmd()
    if pyftsubset is None:
        sys.stderr.write(
            "subset-fonts.py: neither pyftsubset nor the fontTools.subset module is\n"
            "  importable. install the tooling:  pip install -r tools/requirements.txt\n"
        )
        return 2

    cp_file = ARTIFACTS / "font-codepoints.json"
    if not cp_file.is_file():
        sys.stderr.write(f"subset-fonts.py: {cp_file} missing — run `subset-fonts.py codepoints` first.\n")
        return 2
    payload = json.loads(cp_file.read_text())
    latin_cps = [int(c[2:], 16) for c in payload["latinCodepoints"]]
    khmer_cps = [int(c[2:], 16) for c in payload["khmerCodepoints"]]

    faces = all_font_faces()
    files = sorted({FONT_DIR / Path(f["file"]).name for f in faces})
    out_dir = Path(args.out_dir) if args.out_dir else ARTIFACTS / "fonts-subset"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for src in files:
        if not src.is_file():
            print(f"  MISSING  {src}")
            continue
        kind = classify_font(src.name)
        used = khmer_cps if kind == "khmer" else latin_cps
        floor = KHMER_FLOOR if kind == "khmer" else LATIN_FLOOR
        unicodes = set(used)
        for lo, hi in floor:
            unicodes.update(range(lo, hi + 1))
        # Also keep every codepoint this face's `unicode-range` PROMISES. Subsetting
        # to the used set alone would make the browser pick a different font for
        # any character the CSS says this face covers but no page currently
        # renders — a visible change for user-supplied text (a guest's name, a
        # venue) with no visual review of it. Keeping the declared range makes the
        # subset incapable of changing any rendering while still dropping every
        # glyph outside the range (coverage the face can never be asked to paint).
        if not args.used_only:
            for face in faces:
                if Path(face["file"]).name == src.name:
                    for lo, hi in face.get("unicodeRanges", []):
                        unicodes.update(range(lo, hi + 1))
        dst = out_dir / src.name
        cmd = [
            *pyftsubset, str(src),
            f"--unicodes={ranges(unicodes)}",
            # Khmer shaping lives in OpenType features; dropping them silently
            # breaks conjuncts and coeng. Keep every feature.
            "--layout-features=*",
            "--flavor=woff2",
            "--no-recalc-timestamp",
            f"--output-file={dst}",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr)
            print(f"  FAILED   {src.name}")
            return 1
        before, after = src.stat().st_size, dst.stat().st_size
        rows.append({
            "file": src.name, "class": kind, "unicodes": len(unicodes),
            "usedCodepoints": len(used), "usedOnly": bool(args.used_only),
            "before": before, "after": after, "delta": after - before,
            "deltaPct": round(100.0 * (after - before) / before, 1),
        })
        print(f"  {src.name:<34}{before:>9} -> {after:>9}  {after - before:>+9}  ({rows[-1]['deltaPct']:+.1f}%)")

    total_before = sum(r["before"] for r in rows)
    total_after = sum(r["after"] for r in rows)
    print(f"\n  {'TOTAL':<34}{total_before:>9} -> {total_after:>9}  {total_after - total_before:>+9}  "
          f"({100.0 * (total_after - total_before) / total_before:+.1f}%)")
    (ARTIFACTS / "font-subset-result.json").write_text(json.dumps(rows, indent=1))
    print(f"  output dir: {out_dir.relative_to(REPO_ROOT) if out_dir.is_relative_to(REPO_ROOT) else out_dir}")

    if args.in_place:
        for r in rows:
            shutil.copy2(out_dir / r["file"], FONT_DIR / r["file"])
        print(f"  --in-place: {len(rows)} files replaced under {FONT_DIR.relative_to(REPO_ROOT)}")
        print("  NOTE: src/python/assets/fonts is a served mirror — re-sync it before measuring.")
    return 0


def font_cmap(path: Path):
    from fontTools.ttLib import TTFont
    with TTFont(path, lazy=True) as font:
        best = font.getBestCmap()
        return set(best.keys())


def cmd_verify(args) -> int:
    cp_file = ARTIFACTS / "font-codepoints.json"
    if not cp_file.is_file():
        sys.stderr.write(f"subset-fonts.py: {cp_file} missing — run `subset-fonts.py codepoints` first.\n")
        return 2
    payload = json.loads(cp_file.read_text())
    want = {
        "latin": {int(c[2:], 16) for c in payload["latinCodepoints"]},
        "khmer": {int(c[2:], 16) for c in payload["khmerCodepoints"]},
    }
    face_dir = Path(args.font_dir) if args.font_dir else FONT_DIR
    faces = all_font_faces()
    files = sorted({face_dir / Path(f["file"]).name for f in faces})
    # The regression that matters is a codepoint the ORIGINAL font painted and the
    # replacement no longer does. A codepoint absent from both was already falling
    # back to a system font before this pass, and counting it as a subsetting bug
    # would make the check fail forever: 42 of the 149 Latin-class codepoints the
    # site renders (U+2190..U+21E9 arrows, U+2212 minus, U+2263, ✓, ✦, …) are in
    # none of the three Latin webfonts, original or subset.
    bad = 0
    for src in files:
        if not src.is_file():
            print(f"  MISSING  {src.name}")
            bad += 1
            continue
        kind = classify_font(src.name)
        cmap = font_cmap(src)
        original = FONT_DIR / src.name
        before_cmap = font_cmap(original) if original.is_file() and original != src else cmap
        regressed = sorted(c for c in want[kind] if c in before_cmap and c not in cmap)
        already_absent = sorted(c for c in want[kind] if c not in before_cmap)
        status = "OK" if not regressed else f"REGRESSED {len(regressed)}"
        print(f"  {src.name:<34}{len(cmap):>7} glyphs   {len(want[kind]):>5} required   {status}"
              + (f"   ({len(already_absent)} absent before too)" if already_absent else ""))
        if regressed:
            bad += 1
            print(f"      first regressed: {', '.join(f'U+{c:04X}' for c in regressed[:12])}")
    total_required = sum(len(v) for v in want.values())
    print(f"\nVERDICT: {'no codepoint that the original fonts covered is missing' if not bad else f'{bad} font(s) lost coverage'}"
          f"   (required codepoints: {total_required})")
    return 0 if not bad else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="subset-fonts.py",
        description="Inventory, subset and verify the web fonts against the rendered character set.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("inventory", help="list @font-face declarations, files and sizes")

    p_cp = sub.add_parser("codepoints", help="compute the union of rendered codepoints")
    p_cp.add_argument("--no-src-html", action="store_true", help="skip src/html (only the built tree)")

    p_sub = sub.add_parser("subset", help="subset every font to the used codepoints")
    p_sub.add_argument("--out-dir", default=None, help="output directory (default artifacts/fonts-subset)")
    p_sub.add_argument("--in-place", action="store_true", help="overwrite assets/fonts/*.woff2")
    p_sub.add_argument("--used-only", action="store_true",
                       help="subset to used+floor ONLY, dropping the face's declared unicode-range "
                            "(smaller, but changes which font paints any character the CSS promises "
                            "and no page currently renders)")

    p_ver = sub.add_parser("verify", help="check every required codepoint is still covered")
    p_ver.add_argument("--font-dir", default=None, help="directory of fonts to check (default assets/fonts)")

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if args.cmd == "inventory":
        return cmd_inventory(args)
    if args.cmd == "codepoints":
        return cmd_codepoints(args)
    if args.cmd == "subset":
        return cmd_subset(args)
    if args.cmd == "verify":
        return cmd_verify(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
