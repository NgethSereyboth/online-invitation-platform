"""Every asset a served page declares must exist under the HTTP server's ROOT.

Why this module exists
----------------------
``src/python/server.py`` sets ``ROOT = Path(__file__).resolve().parent``
(``src/python/``) and serves static files only from there. A ``<script src>`` or
``<link href>`` with no file behind it is not a build error and not an import
error -- it is a silent 404 in the browser that no test noticed.

That is exactly what happened on 2026-10-16: ``src/python/route-deferred-loader-v15.js``
was absent while ``src/python/route-bundles-v15.json`` still listed it as a startup
script for five routes. ``python3 build.py all --check`` was red
(``MIRROR_CHECK_FAILED 1 stale destination(s)``, exit 1) and ``pytest tests/`` was
completely green, because nothing in the suite read the served mirror at all.

Two independent properties, because neither one alone covers the failure above:

1. **Fidelity** -- the served mirror is byte-identical to the sources it is
   generated from. Owned by ``src/python/build/sync_frontend_assets.py``; this
   module invokes that owner's own ``--check`` instead of re-implementing it, so
   the two can never disagree.
2. **Resolution** -- every script/stylesheet/manifest/icon a served page
   declares resolves to a real file inside ``src/python/``, and so do the
   route-bundles manifest's own startup and deferred chunk names.

Navigation ``<a href>`` targets are deliberately out of scope: they are routes,
not assets, and some are dynamic (``/i/__INVITATION_SLUG__``) or non-served
documentation paths.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVE_ROOT = REPO_ROOT / "src" / "python"
ROUTE_BUNDLES = SERVE_ROOT / "route-bundles.json"
ROUTE_BUNDLE_SOURCES = REPO_ROOT / "docs" / "route-bundle-sources.json"

# <script src="..."> and <link rel="stylesheet|manifest|icon|apple-touch-icon|preload" href="...">
_SCRIPT_SRC = re.compile(r"<script\b[^>]*\bsrc\s*=\s*\"([^\"]+)\"", re.IGNORECASE)
_LINK_TAG = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_LINK_REL = re.compile(r"\brel\s*=\s*\"([^\"]+)\"", re.IGNORECASE)
_LINK_HREF = re.compile(r"\bhref\s*=\s*\"([^\"]+)\"", re.IGNORECASE)

_ASSET_RELS = {"stylesheet", "manifest", "icon", "apple-touch-icon", "preload", "modulepreload"}


def _declared_assets(html: str) -> set[str]:
    """Every script/stylesheet/manifest/icon reference declared by one page."""
    found: set[str] = set()
    found.update(_SCRIPT_SRC.findall(html))
    for tag in _LINK_TAG.findall(html):
        rel_match = _LINK_REL.search(tag)
        href_match = _LINK_HREF.search(tag)
        if not rel_match or not href_match:
            continue
        rels = {part.strip().lower() for part in rel_match.group(1).split()}
        if rels & _ASSET_RELS:
            found.add(href_match.group(1))
    return found


def _resolves(reference: str) -> bool:
    """True when ``reference`` names a real file under the server ROOT.

    Non-file schemes and fragments are not this guard's business; everything
    else resolves against ``src/python/`` whether it is written as a relative
    path (``core/theme.js``) or a root-absolute one (``/vendor/yjs/y.js``).
    """
    if reference.startswith("#"):
        return True
    if re.match(r"^[a-z][a-z0-9+.-]*:", reference, re.IGNORECASE):
        return True  # http:, https:, data:, blob:, mailto: -- not served from disk
    path = reference.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return True
    return (SERVE_ROOT / path.lstrip("/")).is_file()


@pytest.mark.parametrize("page", [p.name for p in sorted(SERVE_ROOT.glob("*.html"))])
def test_declared_page_assets_resolve_in_serve_root(page: str) -> None:
    """A served page must not reference a script or stylesheet that is not there."""
    html = (SERVE_ROOT / page).read_text(encoding="utf-8", errors="ignore")
    missing = sorted(ref for ref in _declared_assets(html) if not _resolves(ref))
    assert not missing, f"{page} declares assets with no file in src/python/: {missing}"


def test_route_bundle_manifest_assets_resolve_in_serve_root() -> None:
    """Every bundle and deferred chunk the served manifest names must exist."""
    manifest = json.loads(ROUTE_BUNDLES.read_text(encoding="utf-8"))
    missing: list[str] = []
    for page, entry in sorted(manifest["pages"].items()):
        for key in ("javascript", "stylesheet", "deferredJavascript", "deferredStylesheet"):
            name = entry.get(key)
            if name and not (SERVE_ROOT / name).is_file():
                missing.append(f"{page}:{key}={name}")
    assert not missing, f"route-bundles.json names assets not in src/python/: {missing}"


def test_early_and_direct_scripts_resolve_in_serve_root() -> None:
    """``earlyScripts`` load straight from HTML, so they must exist standalone."""
    spec = json.loads(ROUTE_BUNDLE_SOURCES.read_text(encoding="utf-8"))
    missing = sorted(
        name for name in spec.get("earlyScripts", []) if not (SERVE_ROOT / name).is_file()
    )
    assert not missing, f"earlyScripts not present in src/python/: {missing}"
    assert (SERVE_ROOT / "manifest.webmanifest").is_file()


def _mirror_module():
    """Import ``sync_frontend_assets.py`` by path.

    ``src/python/build/`` is not on ``sys.path`` and is not a package the tests
    are meant to import, so the file is loaded directly. Importing it is side
    effect free: it only defines paths and functions.
    """
    path = SERVE_ROOT / "build" / "sync_frontend_assets.py"
    spec = importlib.util.spec_from_file_location("einvite_sync_frontend_assets", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_serve_root_mirror_is_faithful_to_sources() -> None:
    """The served mirror must be byte-identical to its sources.

    Calls the owner's own ``mirror_drift()`` rather than re-implementing the
    comparison, so the gate and this test cannot disagree. This is the check
    that was red (exit 1, ``MIRROR_CHECK_FAILED``) while the whole pytest suite
    was green, and it is why ``src/python/route-deferred-loader-v15.js`` could
    go missing unnoticed.
    """
    drifted, _per_source, _up_to_date = _mirror_module().mirror_drift()
    assert not drifted, (
        "served mirror drifted from its sources; run: python3 build.py mirror\n  "
        + "\n  ".join(drifted)
    )
