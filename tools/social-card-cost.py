#!/usr/bin/env python3
"""social-card-cost.py — what does one OG image cost, and can Pillow shape Khmer?

Why this exists
---------------
``src/python/server.py`` already renders an Open Graph card server-side for
``/api/public/<slug>/social-card.png`` — ``render_social_card_png_bytes`` draws a
1200x630 (``og``), 1080x1080 (``square``) or 1080x1920 (``story``) composition
with Pillow and caches it on disk under ``DATA/social-cache`` keyed by invitation
id and publication version. A per-guest preview would need one more thing that
renderer does not have today: a name drawn on top.

Two numbers decide whether that is cheap or expensive, and neither was written
down anywhere:

  1. **Time and bytes per render.** A per-guest image multiplies the existing
     cost by the guest count. If one ``og`` render is 20 ms, a 300-guest list is
     seconds of worker time; if it is 900 ms, it is minutes and a queue.
  2. **Whether the font in use can actually shape Khmer.** Pillow only shapes
     complex scripts through its RAQM layout engine, and only with a font whose
     cmap covers the script. If RAQM is absent or the Khmer font does not resolve,
     ``image_font(..., khmer=True)`` quietly falls back to DejaVu and every Khmer
     name renders as a row of empty boxes — with no exception to catch. This tool
     reports the resolved font *path* and the cmap coverage of the corpus, so
     "Khmer names would render" is a measurement rather than a hope.

Where the Khmer input comes from
--------------------------------
**Nothing here is invented.** The Khmer used for the "guest name" overlay and the
coverage check is read out of ``docs/i18n/TRANSLATIONS.csv``, this repository's
own translation table.

Both measurements are reported as a median of ``--repeat`` renders, because a
single Pillow draw can land on a slow allocation and the first render of a
process also pays for imports and font files.

Read-only with respect to the application: it imports ``server`` and calls its
renderer, seeds nothing into the database, starts no server, and writes only
``tools/evidence/social-card-cost.json``.

Usage
    python3 tools/social-card-cost.py                 # human report
    python3 tools/social-card-cost.py --repeat 7 --json
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import resource
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOT_PATH = str(ROOT)
PY_PATH = str(ROOT / "src" / "python")
# ``src/python`` must win the name ``server``: the repo-root forwarder re-enters the
# real server with ``__name__ == "__main__"`` and starts listening.
for entry in (ROOT_PATH, PY_PATH):
    if entry not in sys.path:
        sys.path.insert(0, entry)

TRANSLATIONS = ROOT / "docs" / "i18n" / "TRANSLATIONS.csv"
EVIDENCE = ROOT / "tools" / "evidence" / "social-card-cost.json"
KHMER = re.compile(r"[\u1780-\u17ff]")


def khmer_strings() -> list[str]:
    """Every distinct Khmer-bearing value in the repository's translation table."""
    seen: list[str] = []
    with TRANSLATIONS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for value in row.values():
                if value and KHMER.search(value) and value not in seen:
                    seen.append(value)
    if not seen:
        raise SystemExit("social-card-cost: no Khmer values found in TRANSLATIONS.csv")
    return seen


def khmer_sample(strings: list[str]) -> str:
    for value in strings:
        if len(value) >= 6:
            return value
    return strings[0]


def khmer_codepoints(strings: list[str]) -> set[int]:
    """The distinct Khmer codepoints the corpus uses — the coverage question."""
    return {ord(c) for value in strings for c in value if KHMER.match(c)}


def document(names_km: str) -> dict:
    """A minimal published-document shape, matching the keys the renderer reads.

    ``render_social_card_png_bytes`` reads only ``fields``, ``socialCard``,
    ``palette`` and ``accent``; everything else it ignores, so this fixture stays
    deliberately small. ``namesKm`` is the probe's real-Khmer stand-in for what a
    guest name would occupy.
    """
    return {
        "fields": {
            "names": "Sok Dara and Sok Chantha",
            "namesKm": names_km,
            "date": "2026-12-05",
            "venue": "Phnom Penh",
            "venueKm": names_km,
        },
        "palette": {"background": "#fff8f2", "text": "#342c26"},
        "accent": "#9d4555",
        "socialCard": {"language": "both", "alignment": "center"},
    }


def rss_kb() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def timed(fn, repeat: int) -> tuple[float, int, int]:
    """Return (median ms, bytes, peak-RSS delta KB) for `repeat` calls."""
    before = rss_kb()
    samples = []
    size = 0
    for _ in range(repeat):
        start = time.perf_counter()
        payload = fn()
        samples.append((time.perf_counter() - start) * 1000)
        size = len(payload)
    return statistics.median(samples), size, max(0, rss_kb() - before)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    import PIL
    import PIL.features
    from PIL import Image, ImageDraw

    import server

    if Path(server.__file__).resolve() != (ROOT / "src" / "python" / "server.py"):
        raise SystemExit(f"social-card-cost: imported the wrong module: {server.__file__}")

    strings = khmer_strings()
    sample = khmer_sample(strings)
    codepoints = khmer_codepoints(strings)
    doc = document(sample)

    # Only names in ``PIL.features.features`` are legal here; ``freetype2`` is not
    # one of them and ``check_feature`` raises ValueError rather than returning
    # False (the first run of this tool died on exactly that). RAQM is the one that
    # matters: Pillow shapes complex scripts only through the RAQM layout engine.
    available = sorted(PIL.features.features)
    features = {
        "pillow_version": PIL.__version__,
        "features_available": available,
        "raqm": PIL.features.check_feature("raqm"),
        "harfbuzz": PIL.features.check_feature("harfbuzz"),
        "fribidi": PIL.features.check_feature("fribidi"),
    }

    # Which font file `image_font(..., khmer=True)` actually resolves to. If this is
    # a DejaVu path, the Khmer branch of the candidate list found nothing.
    khmer_font = server.image_font(48, True, False)
    resolved = {
        "path": getattr(khmer_font, "path", None),
        "family": khmer_font.getname() if khmer_font else None,
    }
    resolved["is_khmer_font"] = bool(
        resolved["path"] and "khmer" in str(resolved["path"]).lower()
    )

    # cmap coverage of every distinct Khmer codepoint the corpus uses.
    coverage = {"checked": False, "font": None, "codepoints": 0, "missing": 0}
    try:
        from fontTools.ttLib import TTFont

        if resolved["path"]:
            cmap = set()
            with TTFont(resolved["path"], fontNumber=0, lazy=True) as font:
                for table in font["cmap"].tables:
                    cmap |= set(table.cmap.keys())
            wanted = codepoints
            missing = sorted(cp for cp in wanted if cp not in cmap)
            coverage = {
                "checked": True,
                "font": resolved["path"],
                "codepoints": len(wanted),
                "missing": len(missing),
                "missing_codepoints": [f"U+{cp:04X}" for cp in missing],
                "corpus_strings": len(strings),
            }
    except Exception as exc:  # fontTools absent or unreadable: report, do not guess
        coverage["checked"] = False
        coverage["error"] = f"{type(exc).__name__}: {exc}"

    formats = ("og", "square", "story")
    renders = {}
    for fmt in formats:
        ms, size, delta = timed(
            lambda f=fmt: server.render_social_card_png_bytes(
                "probe-invitation", "unlisted", doc, f
            ),
            args.repeat,
        )
        renders[fmt] = {
            "median_ms": round(ms, 1),
            "png_bytes": size,
            "peak_rss_delta_kb": delta,
        }

    # The overlay strategy: render the project card once, then per guest draw one
    # extra line onto a decoded copy and re-encode. Measured the same way, for the
    # same fixture, so the difference is the overlay's own cost.
    name_font = server.image_font(56, True, True)
    base_png = server.render_social_card_png_bytes("probe-invitation", "unlisted", doc, "og")

    def overlay() -> bytes:
        with Image.open(io.BytesIO(base_png)) as image:
            canvas = image.convert("RGB")
        draw = ImageDraw.Draw(canvas, "RGBA")
        draw.text(
            (canvas.width // 2, round(canvas.height * 0.52)),
            sample,
            font=name_font,
            fill="#342c26",
            anchor="mm",
        )
        out = io.BytesIO()
        canvas.save(out, "PNG", optimize=True)
        return out.getvalue()

    overlay_ms, overlay_bytes, overlay_delta = timed(overlay, args.repeat)
    def reencode_only() -> bytes:
        """The overlay's work minus the draw: decode the cached PNG and re-encode it."""
        with Image.open(io.BytesIO(base_png)) as image:
            canvas = image.convert("RGB")
        out = io.BytesIO()
        canvas.save(out, "PNG", optimize=True)
        return out.getvalue()

    only_ms, only_bytes, only_delta = timed(reencode_only, args.repeat)

    def evidence_path(value):
        """A font path as the evidence should record it.

        Repo-relative when the file is inside the checkout, so the evidence does not
        carry one developer's absolute prefix — the same reason tools/README.md gives
        for this directory existing at all. Since the Khmer face is vendored under
        vendor/noto-khmer/, the recorded value is now identical on every machine:
        `vendor/noto-khmer/NotoSansKhmer-Regular.ttf`, not a system path.
        """
        if not value:
            return value
        resolved_path = Path(value).resolve()
        try:
            return str(resolved_path.relative_to(ROOT))
        except ValueError:
            return str(resolved_path)

    result = {
        "command": "python3 tools/social-card-cost.py --repeat %d" % args.repeat,
        "renderer": "src/python/server.py::render_social_card_png_bytes",
        "cache": "DATA/social-cache/<invitation>-v<version>-<fmt>.png",
        "fixture": {
            "note": "minimal published-document shape; the renderer reads fields/socialCard/palette/accent only",
            "khmer_source": str(TRANSLATIONS.relative_to(ROOT)),
            "khmer_sample_chars": len(sample),
        },
        "pillow": features,
        "khmer_font": {**resolved, "path": evidence_path(resolved.get("path"))},
        "khmer_cmap_coverage": {**coverage, "font": evidence_path(coverage.get("font"))},
        "renders": renders,
        "overlay_cost": {
            "note": "decode the cached og PNG + draw one Khmer line + re-encode",
            "median_ms": round(overlay_ms, 1),
            "reencode_only_median_ms": round(only_ms, 1),
            "draw_marginal_ms": round(overlay_ms - only_ms, 1),
            "png_bytes": overlay_bytes,
            "base_png_bytes": only_bytes,
            "peak_rss_delta_kb": overlay_delta,
        },
        "repeat": args.repeat,
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(
            "SOCIAL_CARD_COST repeat=%d pillow=%s raqm=%s harfbuzz=%s fribidi=%s (of %s)"
            % (
                args.repeat,
                features["pillow_version"],
                features["raqm"],
                features["harfbuzz"],
                features["fribidi"],
                ",".join(available),
            )
        )
        print(
            "khmer font resolved to %s (%s)"
            % (resolved["path"] or "(none)", resolved["family"] or "?")
        )
        if coverage["checked"]:
            print(
                "khmer cmap coverage: %d codepoints used by %d corpus strings, %d missing in that font%s"
                % (
                    coverage["codepoints"],
                    coverage["corpus_strings"],
                    coverage["missing"],
                    (
                        " (" + ", ".join(coverage["missing_codepoints"]) + ")"
                        if coverage["missing"]
                        else ""
                    ),
                )
            )
        else:
            print("khmer cmap coverage: not measured (%s)" % coverage.get("error", "fontTools absent"))
        print()
        print("format   size          median ms   png bytes   peak RSS delta")
        for fmt in formats:
            row = renders[fmt]
            print(
                "%-8s %-13s %9.1f   %9d   %d KB"
                % (
                    fmt,
                    {"og": "1200x630", "square": "1080x1080", "story": "1080x1920"}[fmt],
                    row["median_ms"],
                    row["png_bytes"],
                    row["peak_rss_delta_kb"],
                )
            )
        print()
        print(
            "overlay one Khmer name line onto the cached og png: %.1f ms "
            "(re-encode alone %.1f ms, so the draw costs %.1f ms); peak RSS delta %d KB"
            % (
                result["overlay_cost"]["median_ms"],
                result["overlay_cost"]["reencode_only_median_ms"],
                result["overlay_cost"]["draw_marginal_ms"],
                result["overlay_cost"]["peak_rss_delta_kb"],
            )
        )
        print(f"evidence written to {EVIDENCE.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
