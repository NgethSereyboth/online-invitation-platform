#!/usr/bin/env python3
"""TP-2.1: the template-pack artwork is served, typed and cached.

The converter's tests prove the files on disk are safe; this test proves the
server actually exposes them to the editor: 200 with the right content type for
every unique ornament a built document references, a public one-day
``Cache-Control`` (TP-2.1), a byte-identical body, and a 404 with ``no-store``
for a name that is not in the pack.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from v14_test_utils import app_server

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "template-pack"
OUT = ROOT / "assets" / "template-pack"


def load_built(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return json.loads(text[len("export default "):].rstrip().rstrip(";"))


def ornament_urls() -> list[str]:
    urls: set[str] = set()
    for path in sorted((OUT / "built").glob("*.js")):
        for page in load_built(path)["document"]["designPages"]:
            for obj in page["objects"].values():
                src = obj.get("src") or ""
                if src.startswith("/assets/template-pack/ornaments/"):
                    urls.add(src)
    return sorted(urls)


def fetch(base: str, path: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(base + path)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()


def test_ornament_urls_are_non_trivial():
    urls = ornament_urls()
    assert len(urls) >= 27, len(urls)


def test_every_template_pack_asset_is_served_and_cached():
    urls = ornament_urls()
    catalog = json.loads((OUT / "catalog.js").read_text(encoding="utf-8")[len("export default "):].rstrip().rstrip(";"))
    thumbs = [f"/assets/template-pack/thumbs/{entry['id']}.webp" for entry in catalog["templates"]]
    built = [f"/assets/template-pack/built/{entry['id']}.js" for entry in catalog["templates"]]
    with app_server() as (_process, base, _data):
        for path in ["/assets/template-pack/catalog.js", *urls, *thumbs, *built]:
            status, headers, body = fetch(base, path)
            assert status == 200, (path, status)
            assert headers.get("cache-control") == "public, max-age=86400", (path, headers.get("cache-control"))
            assert len(body) > 100, (path, len(body))
            assert body == (ROOT / path.lstrip("/")).read_bytes(), path
        for path in urls:
            status, headers, _body = fetch(base, path)
            assert status == 200
            assert headers.get("content-type") == "image/svg+xml", (path, headers.get("content-type"))
        for path in thumbs:
            status, headers, _body = fetch(base, path)
            assert headers.get("content-type") == "image/webp", (path, headers.get("content-type"))
        status, headers, _body = fetch(base, "/assets/template-pack/ornaments/not-a-real-ornament.svg")
        assert status == 404, status
        assert headers.get("cache-control") == "no-store", headers.get("cache-control")


def test_cache_header_is_scoped_to_the_pack():
    """The new header is scoped to /assets/template-pack/ only."""
    with app_server() as (_process, base, _data):
        status, headers, _body = fetch(base, "/assets/fonts/noto-serif-latin-400.woff2")
        assert status == 200
        assert "cache-control" not in headers, headers.get("cache-control")


def test_asset_record_is_current():
    """docs/ASSETS.md must list every shipped ornament variant with its hash."""
    import hashlib

    record = (ROOT / "docs" / "ASSETS.md").read_text(encoding="utf-8")
    for path in sorted((OUT / "ornaments").glob("*.svg")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert path.name in record, path.name
        assert digest in record, (path.name, digest)
