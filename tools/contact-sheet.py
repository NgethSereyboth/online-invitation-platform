#!/usr/bin/env python3
"""Compose the 36 pack thumbnails into one contact sheet (TP-4.2).

Usage: .venv/bin/python tools/contact-sheet.py
Output: artifacts/next-work/review-tp/contact-sheet.png (not committed)
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
THUMBS = ROOT / "assets" / "template-pack" / "thumbs"
OUT = ROOT / "artifacts" / "next-work" / "review-tp" / "contact-sheet.png"
CATALOG = ROOT / "assets" / "template-pack" / "catalog.js"
COLUMNS, CELL_W, PAD, LABEL_H = 6, 300, 18, 60


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8")[len("export default "):].rstrip().rstrip(";"))
    entries = catalog["templates"]
    rows = (len(entries) + COLUMNS - 1) // COLUMNS
    cell_h = int(CELL_W * 1414 / 1000)
    width = COLUMNS * CELL_W + (COLUMNS + 1) * PAD
    height = rows * (cell_h + LABEL_H) + (rows + 1) * PAD
    sheet = Image.new("RGB", (width, height), "#17141A")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except OSError:  # pragma: no cover - font layout differs by host
        font = ImageFont.load_default()
        small = font
    for index, entry in enumerate(entries):
        column, row = index % COLUMNS, index // COLUMNS
        x = PAD + column * (CELL_W + PAD)
        y = PAD + row * (cell_h + LABEL_H + PAD)
        path = THUMBS / f"{entry['id']}.webp"
        if path.exists():
            with Image.open(path) as thumb:
                image = thumb.convert("RGB")
            image.thumbnail((CELL_W, cell_h))
            sheet.paste(image, (x + (CELL_W - image.width) // 2, y))
        else:  # pragma: no cover - a missing thumbnail is a build defect
            draw.rectangle([x, y, x + CELL_W, y + cell_h], outline="#8b2f3f", width=2)
            draw.text((x + 8, y + 8), "MISSING", font=font, fill="#ff8a9a")
        draw.text((x, y + cell_h + 6), entry["name"]["en"], font=font, fill="#F4EDE2")
        draw.text((x, y + cell_h + 26), f"{entry['id']}  ·  {entry['category']}", font=small, fill="#B9AFA2")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT, optimize=True)
    print(f"WROTE {OUT} ({sheet.width}x{sheet.height}, {len(entries)} templates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
