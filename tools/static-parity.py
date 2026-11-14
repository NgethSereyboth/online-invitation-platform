#!/usr/bin/env python3
"""S3 static and shell parity: diff Python and Node responses path by path.

Compares status, the headers that must match, and the body bytes after folding
the per-request values (CSP nonce, request id). Range support is deliberately
absent on both sides, so a Range request is compared too.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

IGNORED_HEADERS = {
    "date",
    "server",
    "x-request-id",
    "connection",
    "keep-alive",
    "transfer-encoding",
}
COMPARED_HEADERS = [
    "content-type",
    "content-length",
    "cache-control",
    "x-robots-tag",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "x-frame-options",
    "cross-origin-opener-policy",
    "cross-origin-resource-policy",
    "content-security-policy",
    "content-security-policy-report-only",
    "report-to",
    "last-modified",
]
NONCE_RE = re.compile(r"nonce-[A-Za-z0-9_-]{10,}")
NONCE_ATTR_RE = re.compile(r'nonce="[^"]*"')
# Absolute URLs in the public shell carry each backend's own authority.
HOST_RE = re.compile(r"(?:127\.0\.0\.1|localhost):\d+")

ALIASES = {
    "/",
    "/account",
    "/admin",
    "/analytics",
    "/billing",
    "/checkin",
    "/dashboard",
    "/designer",
    "/guests",
    "/materials",
    "/privacy",
    "/public",
    "/reset",
    "/responses",
    "/templates",
    "/verify",
}


def fetch(base: str, path: str, headers: dict[str, str] | None = None):
    request = urllib.request.Request(base + path, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


def fold(text: str) -> str:
    return HOST_RE.sub("HOST", NONCE_ATTR_RE.sub('nonce="N"', text))


def normalise(headers: dict[str, str]) -> dict[str, str]:
    out = {}
    for name, value in headers.items():
        key = name.lower()
        if key in IGNORED_HEADERS:
            continue
        out[key] = HOST_RE.sub("HOST", NONCE_RE.sub("nonce-N", value.replace("\r", "").strip()))
    return out


def compare(python_base: str, node_base: str, path: str, headers: dict[str, str] | None = None):
    p_status, p_headers, p_body = fetch(python_base, path, headers)
    n_status, n_headers, n_body = fetch(node_base, path, headers)
    problems: list[str] = []
    if p_status != n_status:
        problems.append(f"status {p_status} != {n_status}")
    p_norm, n_norm = normalise(p_headers), normalise(n_headers)
    for name in COMPARED_HEADERS:
        if p_norm.get(name) != n_norm.get(name):
            problems.append(f"{name}: {p_norm.get(name)!r} != {n_norm.get(name)!r}")
    p_text, n_text = fold(p_body.decode("utf-8", "replace")), fold(n_body.decode("utf-8", "replace"))
    if p_text != n_text:
        problems.append(f"body {len(p_body)}B != {len(n_body)}B")
    return problems, (p_status, len(p_body), len(n_body))


def asset_paths(web_root: Path, limit: int) -> list[str]:
    skip_dirs = {"data", "node_modules", "__pycache__", "build"}
    found: list[str] = []
    for path in sorted(web_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(web_root)
        if set(rel.parts[:-1]) & skip_dirs:
            continue
        if path.suffix.lower() in {".html", ".pyc"}:
            continue
        if path.stat().st_size > 2_000_000:
            continue
        found.append("/" + rel.as_posix())
        if len(found) >= limit:
            break
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-base", default="http://127.0.0.1:8901")
    parser.add_argument("--node-base", default="http://127.0.0.1:8902")
    parser.add_argument("--web-root", default="src/python")
    parser.add_argument("--assets", type=int, default=40)
    args = parser.parse_args()

    paths = sorted(ALIASES) + ["/missing-asset.js", "/i/no-such-invitation"]
    paths += asset_paths(Path(args.web_root), args.assets)

    failures = 0
    for path in paths:
        problems, _ = compare(args.python_base, args.node_base, path)
        if problems:
            failures += 1
            print(f"FAIL {path}")
            for problem in problems[:6]:
                print(f"     {problem}")
    range_problems, _ = compare(
        args.python_base, args.node_base, "/core/theme.js", {"Range": "bytes=0-9"}
    )
    if range_problems:
        failures += 1
        print("FAIL Range request")
        for problem in range_problems[:6]:
            print(f"     {problem}")

    total = len(paths) + 1
    print(f"\nSTATIC PARITY {total - failures}/{total} identical, {failures} failing")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
