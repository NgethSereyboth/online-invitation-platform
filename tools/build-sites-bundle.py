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
ROUTE_BUNDLE = re.compile(r'^bundle-([A-Za-z0-9_]+)-v15\.js$')


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
            # Deferred chunk for this route, injected by route-deferred-loader-v15.js.
            for ext in (".js", ".css"):
                deferred = src.with_name(f"bundle-{route.group(1)}-deferred-v15{ext}")
                if deferred.is_file():
                    queue.append(deferred)
        if src.suffix.lower() in (".html", ".css", ".js", ".mjs"):
            text = src.read_text(encoding="utf-8", errors="replace")
            for ref in refs_in(src, text):
                if not ref.lower().endswith(ASSET_EXT):
                    # Bare module name: the loader appends a version suffix at runtime.
                    if re.fullmatch(r"[a-z][a-z0-9-]*", ref):
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
            dest.write_text(text, encoding="utf-8")
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
