#!/usr/bin/env python3
"""Build the OKID template pack into the app's native document format (TP-1.2).

Reads the design source in ``template-pack/`` and writes browser-served files under
``assets/template-pack/``:

  catalog.js                  ES module: the 36 catalogue entries the gallery lists
  built/<id>.js               ES module: one template as a native invitation document
  ornaments/<stem>~<colours>.svg   recoloured copies of the 27 ornaments

The output is ES modules, not ``.json``, because ``ServerHandler.public_static_path``
refuses every ``.json`` (a disclosure fix) and the gallery must fetch these lazily
without a new API route. Nothing here is inlined into an editor bundle.

Stdlib only (TP-OD-2). Deterministic and idempotent: unchanged files are not
rewritten, and ``--check`` fails when anything on disk is stale.

This script never contains Khmer: it copies strings out of
``template-pack/copy-bank.json`` and writes them into the built documents.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "template-pack"
OUT = ROOT / "assets" / "template-pack"
SERVED = "/assets/template-pack"

CATALOG_FILE = OUT / "catalog.js"
BUILT_DIR = OUT / "built"
ORNAMENT_DIR = OUT / "ornaments"
THUMB_DIR = OUT / "thumbs"

# Font roles in template-pack/fonts.json -> ids in the app's registry
# (src/js/typography-contract.js). Only four real families are registered, so a
# role whose family the registry lacks takes the nearest registered family; the
# substitution is recorded in docs/templates/FONT-SUBSTITUTIONS.md (TP-2.2) and
# could be replaced by a self-hosted OFL face under TP-OD-1 without touching any
# other part of this converter.
FONT_ROLES = {
    "kh.moul": "noto-serif-khmer",
    "kh.moulpali": "noto-serif-khmer",
    "kh.koulen": "noto-sans-khmer",
    "kh.bokor": "noto-serif-khmer",
    "kh.serif": "noto-serif-khmer",
    "kh.sans": "noto-sans-khmer",
    "kh.battambang": "noto-sans-khmer",
    "kh.kantumruy": "noto-sans-khmer",
    "lat.cormorant": "noto-serif",
    "lat.playfair": "noto-serif",
    "lat.script": "noto-serif",
    "lat.cinzel": "noto-serif",
    "lat.montserrat": "noto-sans",
    "lat.jost": "noto-sans",
}

CATEGORY_EVENT = {
    "wedding": "Wedding",
    "birthday": "Birthday",
    "ceremony": "Ceremony",
    "greeting": "Greeting",
    "business": "Business",
}

CATEGORY_LABEL = {
    "wedding": "Wedding",
    "birthday": "Birthday",
    "ceremony": "Ceremony",
    "greeting": "Greetings",
    "business": "Business",
}

# Pack slot -> (document field for the Khmer line, document field for the English line).
SLOT_FIELDS = {
    "groom": ("groomKm", "groom"),
    "bride": ("brideKm", "bride"),
    "name": ("nameKm", "name"),
    "host": ("hostKm", "host"),
}

# Placeholder copy key per slot, used to prefill the document fields.
SLOT_COPY = {
    "groom": "ph.groom",
    "bride": "ph.bride",
    "name": "ph.name",
    "host": "ph.host",
}

MAGIC_FILLS = ("#AA0001", "#AA0002", "#AA0003")

SHAPE_KINDS = {"rectangle": "rectangle", "rect": "rectangle", "ellipse": "circle", "circle": "circle", "line": "line"}

PHOTO_MASKS = {"rect": "none", "rectangle": "none", "ellipse": "circle", "circle": "circle", "arch": "arch"}

TEXT_TRANSFORMS = {
    "none": "none",
    "upper": "uppercase",
    "uppercase": "uppercase",
    "lower": "lowercase",
    "lowercase": "lowercase",
    "title": "capitalize",
    "capitalize": "capitalize",
}

MAX_PATTERN_TILES = 36


class PackError(RuntimeError):
    pass


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def dump_module(payload) -> str:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    return "export default " + body + ";\n"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def hex_colour(palette: dict, role: str, where: str) -> str:
    if role not in palette:
        raise PackError(f"{where}: colour role {role!r} is not in the palette")
    value = str(palette[role]).upper()
    if not re.fullmatch(r"#[0-9A-F]{6}", value):
        raise PackError(f"{where}: colour role {role!r} is not #RRGGBB ({value!r})")
    return value


def recolor_svg(source: str, palette: dict, layer: dict, where: str) -> tuple[str, str]:
    """Return (svg text, colour slug) with the layer's colours baked in."""
    text = source
    magic = any(token in text for token in MAGIC_FILLS)
    if magic:
        recolor = layer.get("recolor") or {}
        roles = [recolor.get("c1", "accent"), recolor.get("c2", "accent2"), recolor.get("c3", "bg")]
        hexes = [hex_colour(palette, role, where) for role in roles]
        for token, value in zip(MAGIC_FILLS, hexes):
            text = text.replace(token, value)
        slug = "-".join(value.lstrip("#").lower() for value in hexes)
    else:
        colour = hex_colour(palette, layer.get("color", "accent"), where)
        if "currentColor" not in text:
            raise PackError(f"{where}: monotone ornament has no currentColor to recolour")
        text = text.replace("currentColor", colour)
        slug = colour.lstrip("#").lower()
    if "<script" in text.lower() or re.search(r"\son[a-z]+\s*=", text, re.I):
        raise PackError(f"{where}: ornament carries script or an inline handler")
    if re.search(r"(?:href|src)\s*=\s*[\"'](?!#)", text, re.I):
        raise PackError(f"{where}: ornament references an external resource")
    # TP-2.1: the editor's SVG sanitiser drops ``preserveAspectRatio`` because it
    # is not on its allow-list. Strip it here so every served ornament passes the
    # sanitiser byte-for-byte instead of being silently rewritten on import.
    text = re.sub(r"\s+preserveAspectRatio\s*=\s*\"[^\"]*\"", "", text)
    return text, slug


def ornament_url(stem: str, slug: str) -> str:
    return f"{SERVED}/ornaments/{stem}~{slug}.svg"


def px(value, canvas_h: int, where: str) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise PackError(f"{where}: {value!r} is not a number")
    return max(1, int(round(number / 100.0 * canvas_h)))


def text_html(layer: dict, copy: dict, where: str) -> str:
    if "literal" in layer:
        return str(layer["literal"])
    key = layer.get("copy")
    if not key:
        raise PackError(f"{where}: text layer has neither copy nor literal")
    if key not in copy:
        raise PackError(f"{where}: copy key {key!r} is not in the copy bank")
    lang = layer.get("lang", "en")
    entry = copy[key]
    if lang not in entry:
        raise PackError(f"{where}: copy key {key!r} has no {lang!r} value")
    return str(entry[lang])


def base_object(layer: dict, z: int, canvas_h: int) -> dict:
    return {
        "type": "text",
        "left": f"{layer.get('x', 0)}%",
        "top": f"{layer.get('y', 0)}%",
        "width": f"{layer.get('w', 100)}%",
        "height": f"{px(layer.get('h', 10), canvas_h, layer.get('id', 'layer'))}px",
        "zIndex": z,
        "opacity": float(layer.get("opacity", 1)),
        "rotation": float(layer.get("rot", 0) or 0),
        "visible": True,
        "locked": False,
        "animation": "none",
        "duration": "900",
        "showInHero": False,
        "showInGallery": False,
        "lockedLayer": False,
    }


def text_object(layer, z, canvas_h, palette, copy, where) -> dict:
    obj = base_object(layer, z, canvas_h)
    # The pack's height is the designed line box; the rich-text renderer adds the
    # font's own line spacing, which is slightly taller after substitution. Give
    # the box at least the measured line count so a line is never clipped (A3).
    size_px = float(layer.get("size", 24))
    lines = max(1, int(layer.get("lines", 1) or 1))
    line_px = float(layer.get("lineHeight", 1.4) or 1.4)
    needed = int(round(lines * size_px * line_px * 1.06)) + 18
    obj["height"] = f"{max(int(obj['height'][:-2]), needed)}px"
    role = layer.get("font", "lat.cinzel")
    if role not in FONT_ROLES:
        raise PackError(f"{where}: font role {role!r} is not mapped")
    # The document model accepts only 400/700 (server.py:1182,
    # typography_document_model.py:59); nearest allowed weight wins.
    weight = 700 if float(layer.get("weight", 400) or 400) >= 600 else 400
    obj.update(
        {
            "html": text_html(layer, copy, where),
            "font": FONT_ROLES[role],
            "fontPairing": "ceremonial-khmer" if role.startswith("kh.") else "serif-formal",
            "fontSize": float(layer.get("size", 24)),
            "fontWeight": str(weight),
            "fontStyle": "normal",
            "colorToken": "heading" if layer.get("color") in ("accent", "ink") else "text",
            "color": hex_colour(palette, layer.get("color", "ink"), where),
            "textAlign": layer.get("align", "center"),
            "textVerticalAlign": "middle",
            # The pack's boxes are measured to the text itself. The rich-text
            # default padding of 8 px per side made every box overflow by 8 px
            # (TP-3 A3), so the padding is removed for pack text.
            "textPadding": 0,
            # Substituted families are wider than the pack's display faces. Fit
            # keeps the designed box and only shrinks a line that would clip.
            "textAutoFit": "fit",
            "textAutoFitMax": float(layer.get("size", 24)),
            "textMinFontSize": 10,
            "letterSpacing": 0,
            "lineHeight": float(layer.get("lineHeight", 1.4)),
            "textWrap": "balance",
            # The document model accepts none/uppercase/lowercase/capitalize
            # (server.py:1209); the pack writes the short form.
            "textTransform": TEXT_TRANSFORMS.get(str(layer.get("transform", "none")).lower(), "none"),
            "layerName": str(layer.get("name") or layer.get("copy") or "Text"),
            "alt": "",
            "caption": "",
        }
    )
    slot = layer.get("slot")
    if slot:
        base_slot = slot[:-3] if slot.endswith("_en") else slot
        if base_slot not in SLOT_FIELDS:
            raise PackError(f"{where}: unknown slot {slot!r}")
        km_field, en_field = SLOT_FIELDS[base_slot]
        obj["contentBinding"] = "fields." + (en_field if slot.endswith("_en") else km_field)
    return obj


def shape_object(layer, z, canvas_h, palette, where) -> dict:
    obj = base_object(layer, z, canvas_h)
    kind = SHAPE_KINDS.get(str(layer.get("shape", "rectangle")).lower())
    if kind is None:
        raise PackError(f"{where}: shape {layer.get('shape')!r} is not supported")
    # A stroke-only rule carries fill=None; the app paints shapeKind 'line' as a
    # filled bar, so the stroke colour becomes the fill and the bar keeps its
    # stroked thickness.
    fill_role = layer.get("fill") or layer.get("stroke") or "accent"
    if kind == "line":
        stroke = float(layer.get("strokeWidth", 0) or 0)
        if stroke:
            obj["height"] = f"{max(1, int(round(stroke)))}px"
    obj.update(
        {
            "type": "shape",
            "shapeKind": kind,
            "fillColor": hex_colour(palette, fill_role, where),
            "fillMode": "solid",
            "borderColor": hex_colour(palette, layer.get("stroke") or fill_role, where),
            "borderWidth": float(layer.get("strokeWidth", 0) or 0),
            "borderRadius": float(layer.get("radius", 0) or 0),
            "layerName": str(layer.get("name") or "Shape"),
        }
    )
    return obj


def image_object(layer, z, canvas_h, src, where, mask="none", frame="none", fit="contain") -> dict:
    obj = base_object(layer, z, canvas_h)
    obj.update(
        {
            "type": "image",
            "src": src,
            "originalSrc": src,
            "alt": "",
            "caption": "",
            "imageFit": fit,
            "imagePositionX": 50,
            "imagePositionY": 50,
            "imageMask": mask,
            "imageFrame": frame,
            "imageFlipX": bool(layer.get("flipX", False)),
            "imageFlipY": bool(layer.get("flipY", False)),
            "layerName": str(layer.get("name") or "Ornament"),
            "decorative": True,
        }
    )
    return obj


def build_page(page, template, ctx, page_index) -> tuple[dict, dict]:
    """Return (native page, ornaments to write)."""
    canvas = template["canvas"]
    canvas_h = int(canvas["h"])
    palette = template["palette"]
    copy = ctx["copy"]
    where = f"{template['id']} page {page_index + 1}"
    objects: dict[str, dict] = {}
    ornaments: dict[str, str] = {}
    background = hex_colour(palette, "bg", where)
    counter = 0
    z = 1

    def add(obj_id, obj):
        nonlocal z
        objects[obj_id] = obj
        z += 1

    for layer_index, layer in enumerate(page["layers"]):
        kind = layer.get("type")
        counter += 1
        layer_where = f"{where} layer {layer_index + 1} ({kind})"
        oid = f"{template['id']}-p{page_index + 1}-{layer.get('id') or counter}"
        if kind == "bg":
            fill = layer.get("fill", "bg")
            if isinstance(fill, dict) and "gradient" in fill:
                stops = fill["gradient"].get("stops") or []
                if len(stops) < 2:
                    raise PackError(f"{layer_where}: gradient needs two stops")
                first = hex_colour(palette, stops[0][0], layer_where)
                last = hex_colour(palette, stops[-1][0], layer_where)
                gradient = base_object(layer, 0, canvas_h)
                gradient.update(
                    {
                        "type": "shape",
                        "shapeKind": "rectangle",
                        "fillMode": "gradient",
                        "gradientStart": first,
                        "gradientEnd": last,
                        "gradientAngle": float(fill["gradient"].get("angle", 180)),
                        "fillColor": first,
                        "layerName": "Background",
                    }
                )
                objects[oid] = gradient
            else:
                background = hex_colour(palette, fill, layer_where)
        elif kind == "svg":
            src = layer.get("src") or ""
            stem = Path(src).name.rsplit(".", 1)[0]
            source_path = PACK / src
            if not source_path.is_file():
                raise PackError(f"{layer_where}: ornament {src!r} does not exist")
            text, slug = recolor_svg(source_path.read_text(encoding="utf-8"), palette, layer, layer_where)
            ornaments[f"{stem}~{slug}.svg"] = text
            add(oid, image_object(layer, z, canvas_h, ornament_url(stem, slug), layer_where))
        elif kind == "pattern":
            src = layer.get("src") or ""
            stem = Path(src).name.rsplit(".", 1)[0]
            source_path = PACK / src
            if not source_path.is_file():
                raise PackError(f"{layer_where}: ornament {src!r} does not exist")
            text, slug = recolor_svg(source_path.read_text(encoding="utf-8"), palette, layer, layer_where)
            ornaments[f"{stem}~{slug}.svg"] = text
            # `tile` is px at the declared canvas width, so the grid is measured
            # in canvas pixels. The grid is thinned until it fits the object cap.
            tile_px = max(1.0, float(layer.get("tile", 84)))
            width_px, height_px = int(canvas["w"]), int(canvas["h"])
            cols = max(1, math.ceil(width_px / tile_px))
            rows = max(1, math.ceil(height_px / tile_px))
            while cols * rows > MAX_PATTERN_TILES:
                tile_px *= 1.25
                cols = max(1, math.ceil(width_px / tile_px))
                rows = max(1, math.ceil(height_px / tile_px))
            cell_w = float(layer.get("w", 100)) / cols
            cell_h = float(layer.get("h", 100)) / rows
            for row in range(rows):
                for col in range(cols):
                    tile = dict(layer)
                    tile.update({"x": float(layer.get("x", 0)) + col * cell_w,
                                 "y": float(layer.get("y", 0)) + row * cell_h,
                                 "w": cell_w, "h": cell_h})
                    tile.pop("radius", None)
                    add(f"{oid}-{row}-{col}",
                        image_object(tile, z, canvas_h, ornament_url(stem, slug), layer_where, fit="fill"))
        elif kind == "shape":
            add(oid, shape_object(layer, z, canvas_h, palette, layer_where))
        elif kind == "photo":
            mask = PHOTO_MASKS.get(str(layer.get("shape", "rect")).lower())
            if mask is None:
                raise PackError(f"{layer_where}: photo mask {layer.get('shape')!r} is not supported")
            panel = dict(layer)
            panel["shape"] = "rect" if mask == "none" else ("ellipse" if mask == "circle" else "rect")
            panel["fill"] = "soft"
            panel["stroke"] = "line"
            panel["strokeWidth"] = 0
            panel["opacity"] = 0.10
            panel["name"] = "Photo placeholder"
            add(f"{oid}-panel", shape_object(panel, z, canvas_h, palette, layer_where))
            frame = {"none": "none", "white": "white", "gold": "gold", "dark": "dark"}.get(
                str(layer.get("frame", "none")), "none")
            add(oid, image_object(layer, z, canvas_h, "", layer_where, mask=mask, frame=frame, fit="cover"))
        elif kind == "text":
            add(oid, text_object(layer, z, canvas_h, palette, copy, layer_where))
        else:
            raise PackError(f"{layer_where}: unknown layer type")

    page_id = f"{template['id']}-page-{page_index + 1}"
    native = {
        "id": page_id,
        "name": str(page.get("name") or f"Page {page_index + 1}"),
        "preset": str(page.get("builder") or "pack"),
        "enabled": True,
        "background": background,
        "backgroundImage": "",
        "backgroundSize": "cover",
        "backgroundOverlay": 0,
        "useMasterBackground": False,
        "animation": {"preset": "fade-up", "duration": 900},
        "transition": {"preset": "none", "duration": 600},
        "objects": objects,
    }
    return native, ornaments


def document_fields(copy: dict, category: str) -> dict:
    fields = {}
    for slot, key in SLOT_COPY.items():
        entry = copy.get(key, {})
        km_field, en_field = SLOT_FIELDS[slot]
        fields[en_field] = str(entry.get("en", ""))
        fields[km_field] = str(entry.get("km", ""))
    names_key = "ph.names" if "ph.names" in copy else "ph.name"
    fields["names"] = str(copy.get(names_key, {}).get("en", ""))
    fields["namesKm"] = str(copy.get(names_key, {}).get("km", ""))
    fields.setdefault("date", "")
    fields.setdefault("time", "")
    for slot in ("date", "time"):
        key = "ph." + slot
        if key in copy:
            fields[slot] = str(copy[key].get("en", ""))
    fields["venue"] = str(copy.get("ph.venue", {}).get("en", ""))
    fields["venueKm"] = str(copy.get("ph.venue", {}).get("km", ""))
    fields["message"] = ""
    fields["messageKm"] = ""
    return fields


def build_template(template: dict, catalog_entry: dict, copy: dict) -> tuple[dict, dict]:
    canvas = template["canvas"]
    pages = []
    ornaments: dict[str, str] = {}
    for index, page in enumerate(template.get("pages") or []):
        native, page_ornaments = build_page(page, template, {"copy": copy}, index)
        pages.append(native)
        ornaments.update(page_ornaments)
    if not pages:
        raise PackError(f"{template['id']}: no pages")
    category = template["category"]
    palette = template["palette"]
    # The pack is a designed card, not a section page: every guest section stays
    # off and the card pages are the whole guest page. Turning RSVP on from the
    # editor afterwards is the owner's choice; the app rebuilds sectionOrder from
    # its own panel on load, so a mixed order would put RSVP before the card.
    settings = {
        "rsvpEnabled": False,
        "wishesEnabled": False,
        "scheduleEnabled": False,
        "venueEnabled": False,
        "galleryEnabled": False,
        "countdownEnabled": False,
        "musicEnabled": False,
        "openingEnabled": False,
        "contactEnabled": False,
    }
    section_order = [f"page:{page['id']}" for page in pages]
    document = {
        "schemaVersion": 13,
        "eventType": CATEGORY_EVENT[category],
        "templateId": template["id"],
        "fields": document_fields(copy, category),
        "settings": settings,
        "languageMode": "both",
        "dateFormat": "gregorian",
        "accent": palette["accent"],
        "palette": {
            "background": palette["bg"],
            "surface": palette["paper"],
            "text": palette["ink"],
            "heading": palette["accent"],
        },
        "palettePreset": "custom",
        "theme": "rose",
        "posterCanvas": {"width": int(canvas["w"]), "height": int(canvas["h"])},
        "masterPageStyle": {
            "enabled": False,
            "background": palette["bg"],
            "backgroundImage": "",
            "backgroundSize": "cover",
            "backgroundOverlay": 0,
        },
        "backgroundEffects": {
            "mode": "none",
            "start": palette["bg"],
            "end": palette["paper"],
            "angle": 135,
            "texture": "none",
            "textureOpacity": 18,
        },
        "designPages": pages,
        "objects": {},
        "galleryOrder": [],
        "sectionOrder": section_order,
        "schedule": [],
        "venues": [],
        "customBlocks": [],
        "sectionAnimations": {},
        "sectionLayouts": {},
        "sectionStyles": {},
        "rsvpFields": [],
        "music": None,
        "video": None,
        "mapUrl": "",
        "openingScene": {
            "id": "minimal-editorial",
            "monogram": "",
            "subtitle": "",
            "backgroundColor": palette["bg"],
            "backgroundImage": "",
            "decorative": False,
            "enterText": "Open invitation",
            "enterTextKm": "",
            "duration": 1100,
            "textVariant": "dark",
            "skipAllowed": True,
        },
        "socialCard": {"photo": "", "alignment": "center", "textVariant": "dark", "language": "both", "monogram": ""},
    }
    built = {
        "id": template["id"],
        "name": catalog_entry["name"],
        "category": category,
        "canvas": {"key": canvas["key"], "width": int(canvas["w"]), "height": int(canvas["h"]), "label": canvas.get("label", "")},
        "typography": template.get("typography", ""),
        "tags": list(template.get("tags") or []),
        "document": document,
    }
    return built, ornaments


THUMB_WIDTH = 420


def thumb_size(canvas_key: str) -> tuple[int, int]:
    width, height = {
        "a5p": (1000, 1414),
        "p45": (1080, 1350),
        "sq": (1080, 1080),
        "story": (1080, 1920),
        "land": (1600, 900),
    }[canvas_key]
    return THUMB_WIDTH, max(1, int(round(THUMB_WIDTH * height / width)))


def catalog_module(catalog: dict, catalog_entries: list[dict]) -> dict:
    templates = []
    for entry in catalog_entries:
        thumb_width, thumb_height = thumb_size(entry["canvas"])
        templates.append(
            {
                "id": entry["id"],
                "category": entry["category"],
                "categoryLabel": CATEGORY_LABEL[entry["category"]],
                "canvas": entry["canvas"],
                "canvasLabel": entry.get("canvasLabel", ""),
                "name": entry["name"],
                "tags": list(entry.get("tags") or []),
                "pages": int(entry.get("pages") or 1),
                "typography": entry.get("typography", ""),
                "palette": entry.get("palette", {}),
                "photoSlots": list(entry.get("photoSlots") or []),
                "thumb": f"{SERVED}/thumbs/{entry['id']}.webp",
                "thumbWidth": thumb_width,
                "thumbHeight": thumb_height,
                "built": f"{SERVED}/built/{entry['id']}.js",
            }
        )
    return {"version": 1, "count": len(templates), "templates": templates}


CANVAS_LABELS = {
    "a5p": "A5 portrait",
    "p45": "4:5 portrait",
    "sq": "Square 1:1",
    "story": "Story 9:16",
    "land": "Banner 16:9",
}


def collect() -> tuple[dict[str, str], list[str]]:
    """Build every output in memory. Returns ({relative path: text}, [problems])."""
    files: dict[str, str] = {}
    problems: list[str] = []
    catalog = load_json(PACK / "catalog.json")
    copy_bank = load_json(PACK / "copy-bank.json")
    copy = copy_bank.get("copy") or {}
    entries = catalog.get("templates") or []
    if len(entries) != int(catalog.get("count", len(entries))):
        problems.append("catalog count does not match the template list")
    built_entries = []
    ornaments: dict[str, str] = {}
    for entry in entries:
        template_path = PACK / "templates" / f"{entry['id']}.json"
        if not template_path.is_file():
            problems.append(f"{entry['id']}: template file missing")
            continue
        template = load_json(template_path)
        entry = dict(entry)
        entry["canvasLabel"] = CANVAS_LABELS.get(entry["canvas"], entry["canvas"])
        try:
            built, template_ornaments = build_template(template, entry, copy)
        except PackError as error:
            problems.append(str(error))
            continue
        ornaments.update(template_ornaments)
        files[f"built/{entry['id']}.js"] = dump_module(built)
        built_entries.append(entry)
    for name, text in ornaments.items():
        files[f"ornaments/{name}"] = text if text.endswith("\n") else text + "\n"
    files["catalog.js"] = dump_module(catalog_module(catalog, built_entries))
    return files, problems


def write_outputs(files: dict[str, str], check: bool) -> int:
    stale: list[str] = []
    written = 0
    for relative, text in sorted(files.items()):
        target = OUT / relative
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        if current == text:
            continue
        stale.append(relative)
        if not check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            written += 1
    # Ornaments and built documents that no longer belong to the pack.
    known = set(files)
    for directory in (ORNAMENT_DIR, BUILT_DIR):
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if path.is_file() and f"{directory.name}/{path.name}" not in known:
                relative = f"{directory.name}/{path.name}"
                stale.append(f"{relative} (orphan)")
                if not check:
                    path.unlink()
                    written += 1
    if check:
        for relative in stale:
            print(f"STALE {relative}")
        if stale:
            print(f"TEMPLATE_PACK_STALE {len(stale)}")
            return 1
        print(f"TEMPLATE_PACK_CURRENT {len(files)}")
        return 0
    print(f"TEMPLATE_PACK_BUILT files={len(files)} written={written}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the OKID template pack.")
    parser.add_argument("--check", action="store_true", help="fail when the built files are stale")
    args = parser.parse_args(argv)
    if not PACK.is_dir():
        print("template-pack/ is missing", file=sys.stderr)
        return 1
    files, problems = collect()
    if problems:
        for problem in problems:
            print(f"TEMPLATE_PACK_ERROR {problem}", file=sys.stderr)
        return 1
    return write_outputs(files, args.check)


if __name__ == "__main__":
    raise SystemExit(main())
