#!/usr/bin/env python3
"""og-contract-audit.py — does `serve_public` actually fill every placeholder the
public page template declares?

The gap this closes
-------------------
There are two lists that have to agree and nothing compared them:

  1. the ``__INVITATION_*__`` placeholders written into ``src/html/public.html``
     (mirrored to ``src/python/public.html``, which is the copy the server reads
     at request time — see ``src/python/server.py``'s ``ROOT``), and
  2. the ``.replace("__INVITATION_X__", …)`` calls in
     ``Handler.serve_public``.

If a placeholder is added to the template and no ``.replace`` is added for it,
the *literal token* ``__INVITATION_TITLE__`` is served to the link-preview
crawler: no error, no log line, just a card whose title reads like a variable
name. That is exactly the failure mode a "does Telegram show the right preview"
question needs to rule out, so it is worth a static check rather than a
hand-read.

What it reports
---------------
* every placeholder in the template, and whether ``serve_public`` substitutes it
  (``SUBSTITUTED``) or leaks it verbatim (``UNSUBSTITUTED``),
* any ``.replace("__INVITATION_…__")`` in ``server.py`` with no template
  counterpart (``ORPHAN`` — dead code, or a rename that was only half done),
* the ``og:*`` / ``twitter:*`` / ``<title>`` / ``<meta name=description>`` tags
  the template declares, each marked ``per-request`` (its content is a
  placeholder) or ``static`` (a literal),
* whether the served mirror copy of the template is byte-identical to the source
  copy.

Read-only: it opens three files, writes nothing, starts nothing.

Usage
    python3 tools/og-contract-audit.py            # human report, exit 1 on a leak
    python3 tools/og-contract-audit.py --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_TEMPLATE = ROOT / "src" / "html" / "public.html"
MIRROR_TEMPLATE = ROOT / "src" / "python" / "public.html"
SERVER = ROOT / "src" / "python" / "server.py"

PLACEHOLDER = re.compile(r"__INVITATION_[A-Z_]+__")
# An HTML comment is prose, not markup. The template's only comment mentioning a
# placeholder is the one at the `__INVITATION_LANG__` note, which explains why the
# server deliberately does NOT substitute a language placeholder; the first run of
# this tool counted it as a leaked token. Comments are stripped before scanning so
# that explanation cannot be mistaken for a defect.
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# `.replace("__INVITATION_X__", …)` and `.replace('__INVITATION_X__', …)`.
REPLACED = re.compile(r"""\.replace\(\s*["'](__INVITATION_[A-Z_]+__)["']""")
# An og:/twitter: meta tag, a <title>, or the description meta — with its content.
META = re.compile(
    r"""<meta\s+(?:property|name)\s*=\s*["'](?P<key>og:[^"']+|twitter:[^"']+)["']"""
    r"""\s+content\s*=\s*["'](?P<value>[^"']*)["']"""
    r"""|<title>(?P<title>[^<]*)</title>"""
    r"""|<meta\s+name\s*=\s*["']description["']\s+content\s*=\s*["'](?P<desc>[^"']*)["']""",
    re.IGNORECASE,
)


def serve_public_body(text: str) -> str:
    """The text of ``Handler.serve_public`` only.

    Scoped deliberately: ``__INVITATION_*__`` and ``.replace`` appear elsewhere in
    server.py's 10 000 lines, and a whole-file grep would let an unrelated hit
    stand in for the public page's own contract.
    """
    start = text.find("def serve_public(self, slug):")
    if start < 0:
        raise SystemExit("og-contract-audit: Handler.serve_public not found in server.py")
    end = text.find("\n    def _p2c_resolve_invitation", start)
    if end < 0:
        end = len(text)
    return text[start:end]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    raw_template = SOURCE_TEMPLATE.read_text(encoding="utf-8")
    template = COMMENT.sub("", raw_template)
    body = serve_public_body(SERVER.read_text(encoding="utf-8"))

    in_template = sorted(set(PLACEHOLDER.findall(template)))
    substituted = sorted(set(REPLACED.findall(body)))

    unsubstituted = [p for p in in_template if p not in substituted]
    orphans = [p for p in substituted if p not in in_template]

    tags = []
    for match in META.finditer(template):
        key = match.group("key") or (
            "title" if match.group("title") is not None else "description"
        )
        raw = match.group("value")
        if raw is None:
            raw = match.group("title")
        if raw is None:
            raw = match.group("desc")
        value = raw or ""
        found = PLACEHOLDER.search(value)
        tags.append(
            {
                "key": key,
                "kind": "per-request" if found else "static",
                "placeholder": found.group(0) if found else "",
                "literal": "" if found else value,
            }
        )

    if MIRROR_TEMPLATE.exists():
        source_digest = sha(SOURCE_TEMPLATE)
        mirror_digest = sha(MIRROR_TEMPLATE)
        mirror = {
            "path": str(MIRROR_TEMPLATE.relative_to(ROOT)),
            "source_sha256_16": source_digest,
            "mirror_sha256_16": mirror_digest,
            "identical": source_digest == mirror_digest,
        }
    else:
        mirror = {
            "path": str(MIRROR_TEMPLATE.relative_to(ROOT)),
            "source_sha256_16": sha(SOURCE_TEMPLATE),
            "mirror_sha256_16": None,
            "identical": False,
        }

    report = {
        "template": str(SOURCE_TEMPLATE.relative_to(ROOT)),
        "serve_public": "src/python/server.py::Handler.serve_public",
        "template_placeholders": in_template,
        "substituted_by_serve_public": substituted,
        "unsubstituted": unsubstituted,
        "orphan_substitutions": orphans,
        "head_tags": tags,
        "mirror": mirror,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(
            "OG_CONTRACT_AUDIT template=%s placeholders=%d substituted=%d "
            "unsubstituted=%d orphans=%d"
            % (
                report["template"],
                len(in_template),
                len(substituted),
                len(unsubstituted),
                len(orphans),
            )
        )
        print()
        print("placeholder                          status         substituted by")
        for name in in_template:
            if name in substituted:
                print(f"{name:<36} SUBSTITUTED    serve_public")
            else:
                print(f"{name:<36} UNSUBSTITUTED  (leaks verbatim into the response)")
        for name in orphans:
            print(f"{name:<36} ORPHAN         .replace has no template token")
        print()
        print("head tag                             kind           value")
        for tag in tags:
            detail = tag["placeholder"] or tag["literal"] or "(empty)"
            print(f"{tag['key']:<36} {tag['kind']:<14} {detail}")
        print()
        print(
            "mirror %s %s (source %s / mirror %s)"
            % (
                report["mirror"]["path"],
                "identical" if mirror["identical"] else "DIFFERS",
                mirror["source_sha256_16"],
                mirror["mirror_sha256_16"] or "(absent)",
            )
        )

    return 1 if (unsubstituted or orphans or not mirror["identical"]) else 0


if __name__ == "__main__":
    sys.exit(main())
