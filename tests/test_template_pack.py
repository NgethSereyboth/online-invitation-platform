#!/usr/bin/env python3
"""TP-1.2: the OKID template pack converts to valid native documents.

Checks the built output under ``assets/template-pack/`` against the design source in
``template-pack/``: 36 templates, unique ids that collide with nothing already
shipped, every copy key resolving, every ornament safe and small, native documents
the editor can open, a clean converter ``--check``, and a repo-wide scan proving no
Khmer was typed outside the files allowed to carry it.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "template-pack"
OUT = ROOT / "assets" / "template-pack"
CONVERTER = ROOT / "tools" / "build-template-pack.py"

KHMER = re.compile("[\u1780-\u17ff\uaa80-\uaaff]")
ALLOWED_KHMER_PATHS = (
    "docs/i18n/",
    "template-pack/",
    "assets/template-pack/",
    "tests/data/template-pack-khmer-allowlist.txt",
)
ALLOWED_EXISTING = ROOT / "tests" / "data" / "template-pack-khmer-allowlist.txt"
OBJECT_TYPES = {"text", "image", "shape", "decoration"}
# Negative offsets are deliberate bleed (an ornament that runs past the edge).
PERCENT = re.compile(r"^-?\d+(?:\.\d+)?%$")


def load_module(path: Path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("export default "), path
    return json.loads(text[len("export default "):].rstrip().rstrip(";"))


def catalog():
    return load_module(OUT / "catalog.js")


def built_files():
    return sorted((OUT / "built").glob("*.js"))


def test_thirty_six_templates_and_unique_ids():
    cat = catalog()
    assert cat["count"] == 36, cat["count"]
    ids = [item["id"] for item in cat["templates"]]
    assert len(ids) == len(set(ids)) == 36
    assert len(built_files()) == 36
    assert {path.stem for path in built_files()} == set(ids)
    assert all(re.fullmatch(r"[a-z0-9-]+", template_id) for template_id in ids)


def test_ids_do_not_collide_with_shipped_templates():
    builtins = set(re.findall(r"base\('([a-z-]+)'", (ROOT / "src/js/builtin-templates.js").read_text(encoding="utf-8")))
    adaptive = set(re.findall(r"\{id:'([a-z-]+)',name:'", (ROOT / "src/js/adaptive-templates.js").read_text(encoding="utf-8")))
    shipped = {f"builtin-{name}" for name in builtins} | adaptive
    pack_ids = {item["id"] for item in catalog()["templates"]}
    assert pack_ids & shipped == set()


def test_every_copy_key_resolves_in_the_bank():
    bank = json.loads((PACK / "copy-bank.json").read_text(encoding="utf-8"))["copy"]
    missing = []
    for path in sorted((PACK / "templates").glob("*.json")):
        template = json.loads(path.read_text(encoding="utf-8"))
        for page in template["pages"]:
            for layer in page["layers"]:
                if layer["type"] != "text" or "copy" not in layer:
                    continue
                key, lang = layer["copy"], layer.get("lang", "en")
                if key not in bank or lang not in bank[key]:
                    missing.append(f"{template['id']}:{key}:{lang}")
    assert missing == [], missing


def test_ornaments_exist_are_small_and_safe():
    sources = {path.name: path for path in (PACK / "ornaments").glob("*.svg")}
    assert len(sources) == 27, len(sources)
    for path in sources.values():
        assert path.stat().st_size <= 12 * 1024, (path.name, path.stat().st_size)
    built = list((OUT / "ornaments").glob("*.svg"))
    assert built, "no recoloured ornaments were written"
    for path in built:
        text = path.read_text(encoding="utf-8")
        size = path.stat().st_size
        assert size <= 12 * 1024, (path.name, size)
        assert "<script" not in text.lower(), path.name
        assert not re.search(r"\son[a-z]+\s*=", text, re.I), path.name
        assert not re.search(r"!important", text), path.name
        assert not re.search(r"(?:href|src)\s*=\s*[\"'](?!#)", text, re.I), path.name
        assert not re.search(r"url\((?:[\"']?)(?:https?:)?//", text), path.name
        assert "currentColor" not in text, path.name
        assert not re.search(r"#AA000[123]", text, re.I), path.name


def test_built_documents_match_the_native_shape():
    cat = catalog()
    by_id = {item["id"]: item for item in cat["templates"]}
    canvases = {"a5p": (1000, 1414), "p45": (1080, 1350), "sq": (1080, 1080), "story": (1080, 1920), "land": (1600, 900)}
    for path in built_files():
        payload = load_module(path)
        assert payload["id"] == path.stem
        entry = by_id[payload["id"]]
        document = payload["document"]
        assert document["schemaVersion"] == 13
        assert document["templateId"] == payload["id"]
        assert document["eventType"] in {"Wedding", "Birthday", "Ceremony", "Greeting", "Business"}
        assert document["posterCanvas"] == {
            "width": canvases[entry["canvas"]][0],
            "height": canvases[entry["canvas"]][1],
        }
        assert document["palettePreset"] == "custom"
        for key in ("fields", "settings", "designPages", "sectionOrder", "palette", "backgroundEffects"):
            assert key in document, (payload["id"], key)
        pages = document["designPages"]
        assert len(pages) == entry["pages"], (payload["id"], len(pages))
        page_tokens = [f"page:{page['id']}" for page in pages]
        assert [token for token in document["sectionOrder"] if token.startswith("page:")] == page_tokens
        for page in pages:
            assert re.fullmatch(r"#[0-9A-Fa-f]{6}", page["background"])
            assert page["objects"], payload["id"]
            z_indexes = []
            for object_id, obj in page["objects"].items():
                assert obj["type"] in OBJECT_TYPES, (payload["id"], object_id, obj["type"])
                assert PERCENT.match(obj["left"]) and PERCENT.match(obj["top"]), (payload["id"], object_id)
                assert PERCENT.match(obj["width"]), (payload["id"], object_id)
                assert re.fullmatch(r"\d+px", obj["height"]), (payload["id"], object_id)
                assert isinstance(obj["zIndex"], int) and obj["zIndex"] >= 0
                z_indexes.append(obj["zIndex"])
                assert 0 <= float(obj["opacity"]) <= 1
                if obj["type"] == "text":
                    assert obj["html"], (payload["id"], object_id)
                    assert obj["font"] in {
                        "noto-sans", "noto-serif", "noto-sans-khmer", "noto-serif-khmer",
                    }, obj["font"]
                    assert obj["letterSpacing"] == 0, (payload["id"], object_id)
                    assert float(obj["lineHeight"]) > 0
                    if obj.get("contentBinding"):
                        assert obj["contentBinding"].startswith("fields."), obj["contentBinding"]
                        assert obj["contentBinding"][7:] in document["fields"], obj["contentBinding"]
                if obj["type"] == "image":
                    assert obj["src"] == "" or obj["src"].startswith("/assets/template-pack/"), obj["src"]
                    assert obj["alt"] == "", (payload["id"], object_id)
            assert len(z_indexes) == len(set(z_indexes)), (payload["id"], "duplicate z-index")


def test_every_referenced_ornament_is_served():
    for path in built_files():
        payload = load_module(path)
        for page in payload["document"]["designPages"]:
            for obj in page["objects"].values():
                src = obj.get("src") or ""
                if not src.startswith("/assets/template-pack/ornaments/"):
                    continue
                served = ROOT / src.lstrip("/")
                assert served.is_file(), (payload["id"], src)
                assert served.stat().st_size <= 12 * 1024, src


def test_no_placeholder_content_leaks_a_real_identity():
    for path in built_files():
        text = path.read_text(encoding="utf-8")
        for pattern in (r"\b\d{3}[- ]?\d{3}[- ]?\d{3,4}\b", r"@[a-z0-9-]+\.(?:com|net|org)"):
            assert not re.search(pattern, text, re.I), (path.stem, pattern)


def test_converter_check_is_clean():
    result = subprocess.run(
        [sys.executable, str(CONVERTER), "--check"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "TEMPLATE_PACK_CURRENT" in result.stdout, result.stdout


def _allowed_khmer_file(relative: str) -> bool:
    if any(relative.startswith(prefix) for prefix in ALLOWED_KHMER_PATHS):
        return True
    if not ALLOWED_EXISTING.is_file():
        return False
    existing = {
        line.strip() for line in ALLOWED_EXISTING.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    return relative in existing


def test_no_khmer_typed_outside_allowed_files():
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    assert tracked.returncode == 0, tracked.stderr
    offenders = []
    for relative in tracked.stdout.split("\0"):
        if not relative:
            continue
        path = ROOT / relative
        if not path.is_file() or _allowed_khmer_file(relative):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if KHMER.search(text):
            offenders.append(relative)
    assert offenders == [], offenders
