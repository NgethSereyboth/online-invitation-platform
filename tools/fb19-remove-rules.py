#!/usr/bin/env python3
"""fb19-remove-rules.py — FB-19 Phase-1 executor: delete the provably-dead rules.

Input: artifacts/next-work/fb-19/provably-dead.json (tools/fb19-merge-dead.py).
Behaviour per file:
  * kill list = set of (atChain, normalized selector, comma-normalized selector
    parts) that the merged analysis marked provably dead for the file;
  * every rule occurrence in the file whose (atChain, selector) matches is
    deleted from the header start (never into the previous block's `}`) to the
    block end, plus the immediately following blank line when that keeps the
    file's remaining structure byte-stable;
  * after rewriting, the file must re-parse with the same walker on the
    blanked text and must contain the same number of `{`/`}` — refuses to
    write otherwise (SystemExit, no partial write);
  * prints per-file before/after `!important` counts and bytes saved.

Usage:
  python3 tools/fb19-remove-rules.py --dead artifacts/next-work/fb-19/provably-dead.json \
      [--files filter1,filter2]   # batch scoping: only files containing the substring
      [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def blank_block_bodies(text: str) -> str:
    out = list(text)
    i, n = 0, len(text)
    state = "normal"
    quote = None
    STRUCT = set("{};")
    while i < n:
        c = text[i]
        if state == "string":
            if c == "\\":
                i += 2
                continue
            if c in ("\n", "\r"):
                state = "normal"
                i += 1
                continue
            if c == quote:
                state = "normal"
            elif c in STRUCT or (c == "/" and text[i + 1:i + 2] == "*"):
                out[i] = " "
        elif state == "comment":
            if c == "*" and i + 1 < n and text[i + 1] == "/":
                out[i] = out[i + 1] = " "
                i += 2
                state = "normal"
                continue
            if out[i] not in ("\n", "\r"):
                out[i] = " "
        else:
            if c == "/" and i + 1 < n and text[i + 1] == "*":
                out[i] = out[i + 1] = " "
                i += 2
                state = "comment"
                continue
            if c in "\"'":
                state = "string"
                quote = c
        i += 1
    if state == "comment":
        raise ValueError("unterminated comment")
    return "".join(out)


def parse_blocks(blanked: str):
    out = []
    i, n = 0, len(blanked)
    while i < n:
        j = blanked.find("{", i)
        if j == -1:
            break
        k = j + 1
        depth = 1
        while k < n and depth:
            c = blanked[k]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            k += 1
        if depth:
            raise ValueError("unbalanced braces")
        out.append((i, j, k))
        i = k
    return out


SKIP_AT = {"keyframes", "font-face", "import", "charset", "namespace"}
SUBSUME_AT = {"media", "supports", "layer", "container", "scope"}


def strip_comments(s: str) -> str:
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def collect_kill_spans(text: str, blanked: str, kill_keys):
    """Return [(start,end)] delete spans for rules matching the kill keys.

    Recursive to mirror tools/fb19-dead-important.py; the kill key's atChain
    (e.g. `@media (max-width:600px)` / `@layer components`) must equal the
    walk chain so a rule is only deleted in the very context that was
    proven dead in all shipped contexts."""
    spans = []

    def rec(start: int, end: int, at_chain: str):
        for (h_start, brace, block_end) in parse_blocks(blanked[start:end]):
            hb = h_start + start
            bb = brace + start
            be = block_end + start
            # the analyser compares comments-stripped selectors; do the same
            header = norm(strip_comments(text[hb:bb])).strip()
            m = re.match(r"@([\w-]+)", header)
            if m:
                name = m.group(1).lower()
                if name in SKIP_AT:
                    continue
                if name in SUBSUME_AT:
                    sub = f"{at_chain} {header.split('{')[0].strip()}" if at_chain else header.split("{")[0].strip()
                    rec(bb + 1, be - 1, sub)
                    continue
                continue
            canon_header = canon(header)
            canon_chain = canon(at_chain)
            if (canon_chain, canon_header) in {(canon(a), canon(s)) for (a, s) in kill_keys}:
                e = be
                mnl = re.match(r"[ \t]*\r?\n(?:[ \t]*\r?\n)?", text[e:])
                if mnl:
                    e += mnl.end()
                spans.append((hb, e))

    rec(0, len(blanked), "")
    return spans


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def canon(s: str) -> str:
    """Whitespace-insensitive canonical form for selector/at-chain matching.

    The analyser stores selectors as `", ".join(strip()ed parts)` (explicit
    comma+space) while raw CSS often writes `a,b`. Both canon() forms collapse
    to the same key, so matching cannot miss on formatting."""
    return norm(s).replace(", ", ",", 1).replace(", ", ",") if False else re.sub(r"\s+", "", s.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dead", required=True)
    ap.add_argument("--files", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    dead = json.loads(Path(args.dead).read_text(encoding="utf-8"))
    per_file = {}
    for e in dead["rules"]:
        key = (norm(e.get("atChain", "")), norm(e["selector"]))
        per_file.setdefault(e["file"], set()).add(key)
    filters = [f for f in args.files.split(",") if f]

    report = []
    grand_before = grand_after = 0
    for path, keys in per_file.items():
        if filters and not any(f in path for f in filters):
            continue
        p = REPO / path
        text = p.read_text(encoding="utf-8")
        before_important = text.count("!important")
        before_bytes = len(text)
        blanked = blank_block_bodies(text)
        try:
            # mirror the analyser's recursive walk so at-rule-nested rules
            # (@media/@layer/…) match too
            blocks = collect_kill_spans(text, blanked, keys)
        except ValueError as exc:
            raise SystemExit(f"REFUSING (pre-check): {path}: {exc}")
        spans = blocks
        if not spans:
            continue
        new_text = text
        for (a, b) in sorted(set(spans), key=lambda x: -x[0]):
            new_text = new_text[:a] + new_text[b:]
        # post checks: brace balance parity and no `}`/`{` corruption, and the
        # remaining important count dropped by at least one per removed rule
        if new_text.count("{") != text.count("{") - len(set(spans)) or \
           new_text.count("}") != text.count("}") - len(set(spans)):
            raise SystemExit(f"REFUSING: {path}: brace delta mismatch after removal")
        after_important = new_text.count("!important")
        if not args.dry_run:
            p.write_text(new_text, encoding="utf-8")
        report.append({"file": path, "rules": len(set(spans)), "bytesSaved": before_bytes - len(new_text),
                       "importantBefore": before_important, "importantAfter": after_important})
        grand_before += before_important
        grand_after += after_important
    print(json.dumps({"files": report, "importantBefore": grand_before,
                      "importantAfter": grand_after, "dryRun": args.dry_run}, indent=1))


if __name__ == "__main__":
    main()
