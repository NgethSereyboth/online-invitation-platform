#!/usr/bin/env python3
"""Assemble a static-only public bundle for Sites hosting.

Starts from the 16 served pages (the same list tools/lib/repo.mjs uses) and
copies every local file they reference, transitively, from src/python/ into
an output directory. References that point to a file that does not exist are
reported: they are 404s in production and must be fixed or removed.

Usage:
    python3 tools/build-sites-bundle.py [--out artifacts/sites-public] [--max-mib 10]

The bundle contains no Python, no data, no secrets and no source maps.
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "src" / "python"

# Neutral stand-ins for the per-invitation placeholders in public.html.
PUBLIC_SHELL_DEFAULTS = {
    "__INVITATION_SLUG__": "",
    "__INVITATION_TITLE__": "Invitation — OKID",
    "__INVITATION_DESCRIPTION__": "You are invited",
    "__INVITATION_OG_IMAGE__": "/assets/favicon.svg",
    "__INVITATION_OG_TYPE__": "image/svg+xml",
    "__INVITATION_PUBLIC_URL__": "/",
}

PAGES = [
    "index.html", "dashboard.html", "public.html", "admin.html", "account.html",
    "billing.html", "verify.html", "reset.html", "privacy.html", "guests.html",
    "responses.html", "analytics.html", "materials.html", "checkin.html",
    "templates.html", "designer.html",
]

ASSET_EXT = (".html", ".js", ".mjs", ".css", ".json", ".svg", ".png", ".jpg",
             ".jpeg", ".webp", ".gif", ".ico", ".woff", ".woff2", ".ttf",
             ".otf", ".webmanifest", ".txt", ".mp3", ".wav")

HTML_REF = re.compile(r'''(?:src|href|poster|data-src)\s*=\s*["']([^"'#?]+)''', re.I)
CSS_URL = re.compile(r'''url\(\s*["']?([^"')#?]+)''', re.I)
JS_STRING = re.compile(r'''["'`]([^"'`;()]+)["'`]''')
# Loaders pack several module names into one comma-separated string.
# A route bundle is ``bundle-<route>.js``; its lazy chunk is
# ``bundle-<route>-deferred.js`` (and the historical ``-deferred-v15.js``).
ROUTE_BUNDLE = re.compile(r'^bundle-([A-Za-z0-9_]+)\.js$')

# server.py injects this into every page it serves (see its ``marker`` constant).
# backend-mode.js treats a page without it as statically hosted and skips the
# /api/health probe entirely, which puts the whole UI into "Static preview
# mode". The Sites Worker reverse-proxies /api/* to a real Python backend, so
# every bundled page must carry the marker; if that backend is down the probe
# fails on its own and the UI still degrades gracefully.
BACKEND_MARKER = '<meta name="einvite-backend" content="full">'
HEAD_TAG = re.compile(r'<head\b[^>]*>', re.I)


def with_backend_marker(html: str) -> str:
    """Declare that a full API is reachable at /api/* (idempotent)."""
    if 'name="einvite-backend"' in html:
        return html
    match = HEAD_TAG.search(html)
    if match is None:
        return html
    return html[: match.end()] + BACKEND_MARKER + html[match.end():]


def refs_in(path: Path, text: str):
    suffix = path.suffix.lower()
    found = []
    if suffix == ".html":
        found += HTML_REF.findall(text)
        found += CSS_URL.findall(text)
        found += [part for s in JS_STRING.findall(text) for part in re.split(r'[,\s]+', s) if part]
    elif suffix == ".css":
        found += CSS_URL.findall(text)
        found += [m for m in re.findall(r'@import\s+["\']([^"\']+)', text)]
    elif suffix in (".js", ".mjs"):
        found += [part for s in JS_STRING.findall(text) for part in re.split(r'[,\s]+', s) if part]
    elif suffix == ".webmanifest":
        try:
            manifest = json.loads(text)
        except ValueError:
            manifest = {}
        for icon in manifest.get("icons", []):
            if isinstance(icon, dict) and icon.get("src"):
                found.append(str(icon["src"]))
    return found


def resolve(ref: str, base: Path):
    ref = unquote(urlsplit(ref).path)
    if not ref or ref.startswith(("http:", "https:", "//", "data:", "mailto:", "blob:")):
        return None
    if ref.startswith("/"):
        target = ROOT / ref.lstrip("/")
    else:
        target = (base.parent / ref).resolve()
    try:
        target.relative_to(ROOT)
    except ValueError:
        return None  # points outside the served tree (repo-level vendor etc.)
    return target


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "artifacts" / "sites-public"))
    ap.add_argument("--max-mib", type=float, default=10.0)
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    queue = [ROOT / p for p in PAGES]
    seen: set[Path] = set()
    missing: dict[str, set[str]] = {}
    while queue:
        src = queue.pop()
        if src in seen:
            continue
        seen.add(src)
        if not src.exists():
            missing.setdefault(str(src.relative_to(ROOT)), set()).add("(page itself)")
            continue
        route = ROUTE_BUNDLE.match(src.name)
        if route:
            # Deferred chunk for this route, requested at runtime by
            # bundle-<route>.js (``${prefix}bundle-${stem}-deferred.js``) and by
            # route-deferred-loader*.js. Both the plain and the -v15 spelling
            # are queued; whichever does not exist is skipped.
            stem = route.group(1)
            for name in (f"bundle-{stem}-deferred", f"bundle-{stem}-deferred-v15"):
                for ext in (".js", ".css"):
                    deferred = src.with_name(name + ext)
                    if deferred.is_file():
                        queue.append(deferred)
        if src.suffix.lower() in (".html", ".css", ".js", ".mjs", ".webmanifest"):
            text = src.read_text(encoding="utf-8", errors="replace")
            for ref in refs_in(src, text):
                if not ref.lower().endswith(ASSET_EXT):
                    # Bare module name: a loader appends ``.js`` at runtime.
                    # Some are versioned (``core/theme-v15.js``), others are
                    # literal (``gpu-loader.js`` builds ``gpu-texture-cache.js``).
                    if re.fullmatch(r"[a-z][a-z0-9-]*", ref):
                        exact = ROOT / f"{ref}.js"
                        if exact.is_file():
                            queue.append(exact)
                        for match in ROOT.glob(f"{ref}-v*.js"):
                            queue.append(match)
                    continue
                if ref.startswith((".", "-")) and "/" not in ref:
                    continue  # a bare extension or suffix fragment, e.g. '.otf'
                target = resolve(ref, src)
                if target is None:
                    continue
                try:
                    exists = target.is_file()
                except OSError:
                    exists = False
                if not exists:
                    missing.setdefault(str(src.relative_to(ROOT)), set()).add(ref)
                    continue
                queue.append(target)
        if src.suffix.lower() in (".js", ".mjs") and src.name.endswith(".map"):
            continue
        dest = out / src.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.name == "public.html" and src.parent == ROOT:
            # server.py fills these per invitation. A static bundle has no
            # invitation, so ship neutral values instead of the raw placeholders.
            text = src.read_text(encoding="utf-8")
            for token, value in PUBLIC_SHELL_DEFAULTS.items():
                text = text.replace(token, value)
            dest.write_text(with_backend_marker(text), encoding="utf-8")
            continue
        if src.suffix.lower() == ".html":
            dest.write_text(
                with_backend_marker(src.read_text(encoding="utf-8", errors="replace")),
                encoding="utf-8",
            )
            continue
        shutil.copy2(src, dest)

    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"bundle: {count} files, {total / 1024 / 1024:.2f} MiB -> {out}")
    if missing:
        print("missing references (404 in production):")
        for owner in sorted(missing):
            for ref in sorted(missing[owner]):
                print(f"  {owner}: {ref}")
    if total > args.max_mib * 1024 * 1024:
        print(f"ERROR: bundle exceeds {args.max_mib} MiB", file=sys.stderr)
        return 2
    if count > 1000:
        print("ERROR: bundle exceeds 1000 files", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
