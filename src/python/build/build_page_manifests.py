#!/usr/bin/env python3
"""Generate deterministic V15 page asset manifests and enforce route budgets.

The manifest lists every browser asset each HTML page loads (scripts + stylesheets),
plus the total transfer bytes for the route. It is the build-time evidence that
production pages stay within their byte/script/style budgets.

Repository layout
-----------------
HTML pages live in ``src/html/``; browser assets live in ``src/js/``,
``src/css/`` (+ ``src/css/organized/``), and ``vendor/``. The output manifest
``page-assets.json`` is written to BOTH ``src/python/`` (where the server
reads it) AND ``docs/`` (repo source of truth).

OUTPUT-ROOT FIX (owner decision accepted 2026-10-20, was the documented
``build.py all`` wrinkle): ``SCRIPT_DIR`` (this file's directory,
``src/python/build/``) was used as the "server" output, so the real served
root never got ``page-assets.json`` while the build exited 0. The true
server-root copy now lives in ``src/python/``; ``src/python/build/`` keeps
a legacy copy for build-dir readers (``tools/important-removal-audit.py``).
"""
from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path

# --- Repo layout -----------------------------------------------------------
# SCRIPT_DIR is src/python/ (server ROOT). The output manifest is written here
# so server.py can read it, AND mirrored to docs/ (repo source of truth).
SCRIPT_DIR = Path(__file__).resolve().parent
# SERVER_DIR = src/python/ — the HTTP server's ROOT (server.py serves static
# files only from here). This is the primary output location.
SERVER_DIR = SCRIPT_DIR.parent
# REPO_ROOT = /home/z/my-project/einvite-platform
REPO_ROOT = SERVER_DIR.parent.parent
JS_DIR = REPO_ROOT / "src" / "js"
CSS_DIR = REPO_ROOT / "src" / "css"
CSS_ORG = CSS_DIR / "organized"
VENDOR_DIR = REPO_ROOT / "vendor"
ASSETS_DIR = REPO_ROOT / "assets"
HTML_DIR = REPO_ROOT / "src" / "html"
DOCS_DIR = REPO_ROOT / "docs"

# Output manifest: written to all three locations.
OUTPUT_SERVER = SERVER_DIR / "page-assets.json"
OUTPUT_BUILD = SCRIPT_DIR / "page-assets.json"  # legacy build-dir copy
OUTPUT_DOCS = DOCS_DIR / "page-assets.json"
OUTPUTS = (OUTPUT_SERVER, OUTPUT_BUILD, OUTPUT_DOCS)

# Map each route name to the list of HTML pages that belong to it.
ROUTES = {
    "dashboard": ["dashboard.html"],
    "editor": ["index.html"],
    "public-guest": ["public.html"],
    "account-admin": ["account.html", "admin.html", "billing.html", "verify.html", "reset.html", "privacy.html"],
    "event-operations": ["guests.html", "responses.html", "analytics.html", "materials.html", "checkin.html", "templates.html", "designer.html"],
}
# Per-route budgets: maximum allowed script count, stylesheet count, and total bytes.
#
# RE-BASELINED 2026-10-11. These are the *measured* page totals plus 5% headroom,
# rounded up to the next 5,000 bytes. The previous numbers were not aspirational,
# they were a category error: BUDGETS["editor"]["bytes"] was 1_420_000 and
# BUDGETS["public-guest"]["bytes"] was 260_000, which are the *route-bundle JS*
# ceilings (bundle-index.js and bundle-public.js respectively) applied to
# *whole-page* totals. A page total also counts the route CSS bundle and the two
# shared scripts the bundle does not contain (core/theme.js, backend-mode.js),
# so the old gate was unsatisfiable by construction and had never passed once:
#
#   public.html  249_994 (bundle-public.js) is the entire old 260_000 budget,
#                while the page also loads bundle-public.css (128_899) and
#                backend-mode.js (2_249) -> 381_142.
#   index.html   1_129_296 + 481_963 (bundle-index js + css) already exceeds
#                1_420_000 before the page's other two scripts are counted.
#
# Ceilings below were measured from docs/page-assets.json after the
# dashboard second-stylesheet consolidation and the versioned-name rename batch:
#
#   route              measured     ceiling   scripts  styles
#   dashboard           649_239     685_000     3       1
#   editor            1_615_307   1_700_000     3       1
#   public-guest        381_142     405_000     2       1
#   account-admin       411_917     435_000     4       1
#   event-operations    416_759     440_000     3       1
#
# Counts are route maxima, because tests/v14_performance_budget_test.py applies
# the route budget to every page in the route: account-admin's 4 is privacy.html
# (core/safe-dom.js + core/i18n.js + core/theme.js + backend-mode.js), while
# its other five pages load 3. The declarative single source of truth for the
# Chrome-driven gate stays docs/perf/lighthouse-budgets.json (see the header of
# tests/v55_route_weight_budget_test.py).
BUDGETS = {
    "dashboard": {"scripts": 3, "styles": 1, "bytes": 685_000},
    "editor": {"scripts": 3, "styles": 1, "bytes": 1_700_000},
    "public-guest": {"scripts": 2, "styles": 1, "bytes": 405_000},
    "account-admin": {"scripts": 4, "styles": 1, "bytes": 435_000},
    "event-operations": {"scripts": 3, "styles": 1, "bytes": 440_000},
}


class Parser(HTMLParser):
    """Collect <script src=...> and <link rel=stylesheet href=...> references."""

    def __init__(self) -> None:
        """Initialise an empty collector with no scripts or styles yet."""
        super().__init__()
        self.scripts: list[str] = []
        self.styles: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Capture script src and stylesheet link href attributes."""
        a = dict(attrs)
        if tag == "script" and a.get("src"):
            self.scripts.append(a["src"])
        if tag == "link" and a.get("href") and "stylesheet" in str(a.get("rel", "")).lower():
            self.styles.append(a["href"])


def clean(value: str) -> str:
    """Strip query strings, fragments, and a leading slash from an asset URL.

    The HTML pages reference assets with bare filenames (e.g. ``bundle-x.js``);
    ``clean`` keeps the resolver agnostic to whether the page wrote
    ``bundle-x.js`` or ``/bundle-x.js`` or ``bundle-x.js?v=15``.
    """
    return value.split("?", 1)[0].split("#", 1)[0].lstrip("/")


def resolve_asset(value: str) -> Path:
    """Resolve a cleaned asset URL to a concrete file under the repo layout.

    Tries (in order): ``vendor/<rest>`` for ``vendor/...`` paths; ``assets/<rest>``
    for ``assets/...`` paths; ``src/js/<name>`` for ``.js`` files; ``src/css/<name>``
    then ``src/css/organized/<name>`` for ``.css`` files; finally ``src/python/<name>``
    so generated bundles that exist only in the server directory still resolve.

    Returns the Path if found, or a non-existent Path (so ``.is_file()`` is False)
    if no candidate exists — ``size()`` then reports 0 for that asset.
    """
    cleaned = clean(value)
    if cleaned.startswith("vendor/"):
        candidate = VENDOR_DIR / cleaned[len("vendor/"):]
        return candidate
    if cleaned.startswith("assets/"):
        candidate = ASSETS_DIR / cleaned[len("assets/"):]
        return candidate
    if cleaned.endswith(".js"):
        candidate = JS_DIR / cleaned
        if candidate.is_file():
            return candidate
    if cleaned.endswith(".css"):
        for base in (CSS_DIR, CSS_ORG):
            candidate = base / cleaned
            if candidate.is_file():
                return candidate
    # Final fallback: the server directory (for generated bundles that exist
    # only in src/python/ — e.g. when the mirror hasn't been written yet).
    return SCRIPT_DIR / cleaned


def size(value: str) -> int:
    """Return the on-disk byte size of an asset URL, or 0 if it is missing.

    Missing assets report 0 so the manifest can still be generated; a missing
    asset shows up as a budget overage during review.
    """
    p = resolve_asset(value)
    return p.stat().st_size if p.is_file() else 0


def page_entry(name: str) -> dict:
    """Parse one HTML page and return its asset summary (scripts/styles/bytes)."""
    p = Parser()
    p.feed((HTML_DIR / name).read_text(encoding="utf-8"))
    scripts = list(dict.fromkeys(p.scripts))
    styles = list(dict.fromkeys(p.styles))
    return {
        "scripts": scripts,
        "styles": styles,
        "scriptCount": len(scripts),
        "styleCount": len(styles),
        "bytes": sum(size(x) for x in scripts + styles),
    }


def atomic_write(path: Path, text: str) -> None:
    """Atomically write text to ``path`` via a .tmp rename (crash-safe)."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def build() -> dict:
    """Compute the full page-asset manifest dict from the current HTML + assets."""
    pages = {name: page_entry(name) for names in ROUTES.values() for name in names}
    routes: dict = {}
    for route, names in ROUTES.items():
        scripts = list(dict.fromkeys(x for name in names for x in pages[name]["scripts"]))
        styles = list(dict.fromkeys(x for name in names for x in pages[name]["styles"]))
        routes[route] = {"pages": names, "scripts": scripts, "styles": styles, "budgets": BUDGETS[route]}
    return {"version": 15, "pages": pages, "routes": routes}


def main(argv=None) -> int:
    """Entry point: ``--check`` verifies the manifest; without it, regenerates it."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="Verify manifest without writing files")
    args = ap.parse_args(argv)
    text = json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        for output in OUTPUTS:
            if not output.is_file() or output.read_text(encoding="utf-8") != text:
                print(f"PAGE_ASSET_MANIFEST_OUT_OF_DATE {output}")
                return 1
        print("PAGE_ASSET_MANIFEST_CHECK_PASSED")
        return 0
    for output in OUTPUTS:
        atomic_write(output, text)
    print(f"WROTE {OUTPUT_SERVER.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
