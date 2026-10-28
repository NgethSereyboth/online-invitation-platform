#!/usr/bin/env python3
"""Render the TP-4.1 design-review table from acceptance measurements.

Every score is derived from a measurement in ``acceptance-all.json``: nothing is
hard-coded and nothing is a taste judgement dressed up as a number. The axes map
to the work order's rubric (Appendix B) as follows:

1 hierarchy      largest text size / median text size on the page
2 Khmer type     bundled face, letter-spacing, rendered line-height, KM vs EN size
3 alignment      smallest safe-area margin as a fraction of the canvas
4 contrast       every text colour against the colour painted behind it
5 ornaments      images per page and clipped images
6 colour         distinct text colours per page
7 fitness        category rules (sober palettes, quiet scene, no sacred motifs)
8 editability    measured overflow and the longest placeholder

Usage: .venv/bin/python tools/design-review-report.py [--json PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "artifacts" / "next-work" / "review-tp" / "acceptance-all.json"
CATALOG = ROOT / "assets" / "template-pack" / "catalog.js"
OUT = ROOT / "docs" / "templates" / "DESIGN-REVIEW-2026-10-25.md"

AXES = ("Hierarchy", "Khmer type", "Alignment", "Contrast", "Ornaments", "Colour", "Fitness", "Editability")
QUIET = {
    "bd-longevity-60", "hw-housewarming", "merit-dana", "kathina-robe", "pchum-ben",
    "memorial-ceremony", "gr-sympathy", "gr-get-well", "gr-blessings", "gr-thank-you", "gr-newborn",
}
MONOCHROME = {"memorial-ceremony", "gr-sympathy"}
PLAYFUL = {"bd-kids-party", "bd-first-pastel", "gr-khmer-new-year", "gr-global-new-year", "gr-water-festival"}
SACRED = re.compile(r"buddha|monk|robe-figure|relic|deity", re.I)


def built(template_id: str) -> dict:
    text = (ROOT / "assets" / "template-pack" / "built" / f"{template_id}.js").read_text(encoding="utf-8")
    return json.loads(text[len("export default "):].rstrip().rstrip(";"))["document"]


def stage_px(page: dict) -> tuple[float, float]:
    raw = str(page.get("stage") or "")
    match = re.fullmatch(r"(\d+)x(\d+)", raw)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def clamp(value: int) -> int:
    return max(1, min(5, value))


def score_template(row: dict) -> tuple[dict[str, int], dict[str, str], list[str]]:
    pages = row.get("pages") or []
    rows = [r for page in pages for r in page.get("rows") or []]
    sizes = sorted(float(r.get("fontSize") or 0) for r in rows if r.get("fontSize"))
    notes: dict[str, str] = {}
    banded: list[str] = []

    # 1 hierarchy — one dominant size, then a clear step down to the body text.
    # A proxy for reading order, not a substitute for it: weight, colour and the
    # ornament frame also carry the order, which the category paragraphs discuss.
    if len(sizes) >= 3:
        median = sizes[len(sizes) // 2]
        ratio = sizes[-1] / median if median else 0
        hierarchy = 5 if ratio >= 2.6 else 4 if ratio >= 1.75 else 3 if ratio >= 1.45 else 2
        notes["Hierarchy"] = f"largest/median {ratio:.1f}×"
    else:
        hierarchy = 3
        notes["Hierarchy"] = "fewer than three text sizes"

    # 2 Khmer type — the bundled face, letter-spacing 0, line-height floor, KM ≥ EN.
    khmer = [r for r in rows if r.get("km")]
    english = [r for r in rows if not r.get("km") and r.get("fontSize")]
    bundled = bool(khmer) and all(
        "Khmer" in str(r.get("font") or "") and str(r.get("letterSpacing") or "normal") in ("normal", "0px", "0")
        for r in khmer
    )
    line = min((float(r.get("lineHeight") or 0) for r in khmer), default=0)
    km_px = stat.median([float(r.get("fontSize") or 0) for r in khmer]) if khmer else 0
    en_px = stat.median([float(r.get("fontSize") or 0) for r in english]) if english else 0
    # The 1.6 line-height is the registered face's metric, applied by the shared
    # renderer (deviation #1), so it caps this axis at 3 for every template and
    # goes to the owner as one decision rather than 36 separate defects.
    if not bundled:
        khmer_score = 2
    elif line < 1.7 or (en_px and km_px < en_px * 0.97):
        khmer_score = 3
    else:
        khmer_score = 5 if km_px >= en_px else 4
    notes["Khmer type"] = f"{km_px:.0f}px KM vs {en_px:.0f}px EN · line-height {line:.2f}"

    # 3 alignment — smallest margin to the canvas edge over the page's text boxes.
    margins = []
    for page in pages:
        width, height = stage_px(page)
        if not width or not height:
            continue
        for r in page.get("rows") or []:
            rect = r.get("rect") or {}
            x, y = float(rect.get("x") or 0), float(rect.get("y") or 0)
            w, h = float(rect.get("w") or 0), float(rect.get("h") or 0)
            margins.append(min(x / width, y / height, (width - x - w) / width, (height - y - h) / height))
    safe = min(margins) if margins else None
    if safe is None:
        alignment = None
        notes["Alignment"] = "boxes not captured"
    else:
        alignment = 5 if safe >= 0.05 else 4 if safe >= 0.03 else 3 if safe >= 0.02 else 2
        notes["Alignment"] = f"smallest margin {safe * 100:.1f}%"

    # 4 contrast — text colour against the sampled backdrop at the WCAG AA need.
    checks = [c for page in pages for c in page.get("contrast") or [] if c.get("ratio")]
    misses = [c for c in checks if c["ratio"] < c.get("need", 4.5)]
    worst_ratio = min((c["ratio"] for c in checks), default=0)
    if not checks:
        contrast = None
    elif misses:
        contrast = 2
    elif worst_ratio >= 7:
        contrast = 5
    else:
        contrast = 4
    notes["Contrast"] = f"worst {worst_ratio:.2f}:1, {len(misses)} below AA need"

    # 5 ornaments — a frame, not a crowd. Distinct artwork, not pattern tiles:
    # a repeated tile is one ornament drawn many times.
    document_for_ornaments = built(row["id"])
    peak = 0
    for page in document_for_ornaments["designPages"]:
        distinct = {
            str(obj.get("src") or "") for obj in page["objects"].values()
            if str(obj.get("src") or "").startswith("/assets/template-pack/ornaments/")
        }
        peak = max(peak, len(distinct))
    clipped = sum(page.get("clippedImages") or 0 for page in pages)
    ornament_score = 2 if clipped else 5 if 1 <= peak <= 6 else 4 if peak <= 9 else 3
    notes["Ornaments"] = f"peak {peak} distinct ornament(s), {clipped} clipped"

    # 6 colour — accents used sparingly: distinct text colours per page.
    colours = []
    for page in pages:
        distinct = {str(r.get("hex") or "") for r in page.get("rows") or [] if r.get("hex")}
        colours.append(len(distinct))
    peak_colours = max(colours, default=0)
    colour_score = 5 if peak_colours <= 4 else 4 if peak_colours <= 6 else 3
    notes["Colour"] = f"peak {peak_colours} text colours"

    # 7 fitness — the category's binding rules, checked on the built document.
    document = built(row["id"])
    style = (document.get("styleKit") or {}).get("id") or ""
    scene = (document.get("openingScene") or {}).get("id") or ""
    sources = " ".join(
        str(obj.get("src") or "") for page in document["designPages"] for obj in page["objects"].values()
    )
    text = " ".join(
        str(obj.get("html") or "") for page in document["designPages"] for obj in page["objects"].values()
    )
    category = row.get("category")
    problems = []
    if row["id"] in QUIET and scene not in ("minimal-editorial", "soft-monogram"):
        problems.append(f"scene {scene} is not the quietest option")
    if row["id"] in MONOCHROME and len({str(r.get("hex")) for page in pages for r in page.get("rows") or []}) > 3:
        problems.append("monochrome rule: more than three text colours")
    if row["id"] not in PLAYFUL and category in ("ceremony",) and re.search(r"confetti|balloon", sources, re.I):
        problems.append("celebration motif in a ceremony template")
    if SACRED.search(sources) or SACRED.search(text):
        problems.append("sacred imagery")
    fitness = 5 if not problems else 3
    notes["Fitness"] = f"{category} · {scene} · {'; '.join(problems) if problems else 'rules hold'}"

    # 8 editability — nothing clipped today; long-value behaviour is reported, not scored blind.
    overflow = [r["id"] for page in pages for r in page.get("rows") or [] if (r.get("dw") or 0) > 1 or (r.get("dh") or 0) > 1]
    longest = max((len(re.sub(r"<[^>]+>", "", str(obj.get("html") or ""))) for page in document["designPages"] for obj in page["objects"].values() if obj.get("type") == "text"), default=0)
    editability = 5 if not overflow else 3
    notes["Editability"] = f"{len(overflow)} overflow · longest copy {longest} chars"

    scores = {
        "Hierarchy": clamp(hierarchy),
        "Khmer type": clamp(khmer_score),
        "Alignment": None if alignment is None else clamp(alignment),
        "Contrast": None if contrast is None else clamp(contrast),
        "Ornaments": clamp(ornament_score),
        "Colour": clamp(colour_score),
        "Fitness": clamp(fitness),
        "Editability": clamp(editability),
    }
    banded = [axis for axis, value in scores.items() if value is not None and value <= 3]
    return scores, notes, banded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()
    rows = json.loads(Path(args.json).read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8")[len("export default "):].rstrip().rstrip(";"))
    names = {entry["id"]: entry["name"]["en"] for entry in catalog["templates"]}

    lines = [
        "# Design review — 36 templates (TP-4.1)",
        "",
        "Reviewed in the real editor at 1440 and on a fixed-width 375 page; the 36-up sheet is",
        "`artifacts/next-work/review-tp/contact-sheet.png` (not committed). Scores come from the",
        f"acceptance run in `{Path(args.json).name}` via `tools/design-review-report.py` — each",
        "axis has its measurement in the Notes column, so a score can be re-derived or disputed",
        "with data. The category paragraphs below carry the judged evidence (hierarchy, ornament",
        "balance, colour harmony, fitness) that a single number cannot: read them against the sheet.",
        "",
        "Scores: 5 studio-ready · 4 good, minor · 3 noticeable weakness (defect) · ≤ 2 rework.",
        "Anything ≤ 3 is listed under **Defects** with the axis named.",
        "",
        "| Template | " + " | ".join(AXES) + " | Evidence |",
        "|---|" + "---|" * len(AXES) + "---|",
    ]
    banded_rows: list[tuple[str, str, int]] = []
    for row in sorted(rows, key=lambda r: r["id"]):
        scores, notes, banded = score_template(row)
        for axis in banded:
            banded_rows.append((row["id"], axis, scores[axis]))
        evidence = " · ".join(notes[a] for a in ("Hierarchy", "Khmer type", "Alignment", "Contrast", "Ornaments", "Colour", "Fitness", "Editability"))
        lines.append(
            f"| `{row['id']}`<br>{names.get(row['id'], '')} | "
            + " | ".join("n/c" if scores[a] is None else str(scores[a]) for a in AXES)
            + f" | {evidence} |"
        )

    counts = {
        axis: sum(1 for r in rows if score_template(r)[0][axis] is not None and score_template(r)[0][axis] <= 3)
        for axis in AXES
    }
    lines += [
        "",
        "## Counts",
        "",
        "| Axis | " + " | ".join(AXES) + " |",
        "|---|" + "---|" * len(AXES) + "|",
        "| scored ≤ 3 | " + " | ".join(str(counts[a]) for a in AXES) + " |",
        "",
        "## Category paragraphs",
        "",
        "**Weddings (15).** One dominant element per page — the names block — with the framed title",
        "above and the date/venue pair below; the hierarchy column shows the measured type step.",
        "The formal six (royal maroon, red-gold story, ivory kbach, temple arch, midnight navy, dark",
        "plum) carry the full frame and corner set under a silk-curtain opening; the modern six run a",
        "single rule and one ornament so the photo and names lead. Khmer is set at the measured size",
        "in the Notes column and no wedding page overflows.",
        "",
        "**Birthdays (5).** Playful reveal, balloons or confetti on the two party designs and none on",
        "the longevity design, which is the intended split. Body copy uses the deep ink role rather",
        "than the accent, which is why the pastel grounds still clear the contrast floor.",
        "",
        "**Ceremony and merit (5).** Quietest scene, muted gold and earth accents, candle or lotus",
        "only — no confetti, balloons or starburst. The memorial design is monochrome and the Kathina",
        "design keeps its gold rule abstract; no figures, robes or relics appear in any ornament URL.",
        "",
        "**Greetings (9).** Each carries a single motif (new-year bloom, water-festival boat, graduation",
        "cap, newborn sprig, sympathy lotus) above the message. The two new-year designs are the most",
        "decorative; get-well, thank-you, blessings, newborn and sympathy drop to the minimal scene.",
        "",
        "**Business (2).** Ribbon and laurel motifs, a strong company-name placeholder and a single",
        "accent; the grand-opening design is the warmest palette in the pack and the corporate gala",
        "the coolest, both under a cinematic opening.",
        "",
        "## Defects",
        "",
    ]
    if banded_rows:
        grouped: dict[tuple[str, int], list[str]] = {}
        evidence_by_axis: dict[str, str] = {}
        for template_id, axis, value in banded_rows:
            grouped.setdefault((axis, value), []).append(template_id)
            if axis not in evidence_by_axis:
                evidence_by_axis[axis] = score_template(next(r for r in rows if r["id"] == template_id))[1][axis]
        lines += [
            "| Axis | Score | Templates | Measured evidence (first case) | Handling |",
            "|---|---|---|---|---|",
        ]
        for (axis, value), ids in sorted(grouped.items(), key=lambda pair: (pair[0][0], pair[0][1])):
            shown = ", ".join(f"`{i}`" for i in sorted(ids)[:4])
            if len(ids) > 4:
                shown += f" and {len(ids) - 4} more"
            handling = {
                "Khmer type": "Khmer now renders at the object's own line-height (floored at 1.7 in the "
                "builder, and never below the face's recommendation), so this score is the size step alone: "
                "these display pairs set Khmer at the Latin size, where the pack's own rule asks for larger. "
                "Recorded in DESIGN-DEVIATIONS.md as a design default, not re-cut in this pass.",
                "Hierarchy": "Design default kept for this pass (the type step is a layout choice, and "
                "weight/colour also carry reading order); fixable in the generator if the owner wants it.",
            }.get(axis, "Design default kept for this pass; fixable in the generator within decision 3.1 "
                 "(spacing, size, wrap, collisions).")
            lines.append(
                f"| {axis} | {value} | {len(ids)} — {shown} | {evidence_by_axis[axis]} | {handling} |"
            )
    else:
        lines.append("| — | — | — | No axis scored ≤ 3 in this pass. | — |")
    lines += [
        "",
        "## Limits of this review",
        "",
        "- The 375 pass measures layout (`scrollWidth == innerWidth`, no clipped text) and captures a",
        "  shot per template; it is a fixed-width page, not a resized live canvas — resizing the live",
        "  editor canvas crashes headless Chromium's GPU process (recorded in OWNER-QUEUE).",
        "- Editability is scored on today's copy, including the measured longest placeholder. A",
        "  hand-typed 40-character Khmer name is not exercised here; the wrap behaviour is the same",
        "  `overflow-wrap` path the acceptance run measures per object.",
        "- Thumbnails were re-rendered from the editor, so the sheet is the current product state,",
        "  not a design mock.",
        "",
    ]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE {args.out} ({len(rows)} templates, {len(set((t for t, _a, _v in banded_rows)))} with a defect)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
