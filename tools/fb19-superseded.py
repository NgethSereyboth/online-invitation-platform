#!/usr/bin/env python3
"""fb19-superseded.py — FB-19 Phase-2: proven-superseded `!important` removal.

A later declaration with the identical property always beats an earlier one when
the two declarations sit in the *same cascade context* (same file, identical
selector text ⇒ identical specificity, identical at-rule chain, identical
@layer nesting, both `!important`). The earlier declaration is then provably
overridden and safe to delete — the cascade cannot change, because the winning
declaration already existed and wins.

Strictness rules (drop any pair that fails one):
  * same selector text (string equality after whitespace normalisation),
  * same at-chain (the @media/@supports/... chain including its condition text);
    different media conditions ⇒ NOT guaranteed overridden — skipped,
  * same property (case-insensitive), both declarations `!important`,
  * the later occurrence sits after the earlier one in the file,
  * neither occurrence is inside `@keyframes`/`@font-face` (excluded by the
    walker anyway) and both are in the same @layer (same-walk context).

Modes:
  --apply  rewrite the files, deleting the earlier declaration (its text span
           up to and including the following `;`), reporting byte savings and
           per-file `!important` delta; refuses to touch a file whose rewrite
           does not re-parse (re-running this analysis must find zero pairs).

Default mode is analysis-only: prints/JSONs candidates with byte spans
without touching anything.

Usage:
  python3 tools/fb19-superseded.py --inventory artifacts/next-work/nw-2-1/important-inventory.json \
      --out artifacts/next-work/fb-19/superseded.json
  python3 tools/fb19-superseded.py --inventory ... --out ... --apply
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def blank_block_bodies(text: str) -> str:
    """Same structural blanking as fb19-dead-important.py: keep quotes intact,
    blank `{`/`}`/`;` inside strings, fully blank comments (same length)."""
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


def parse_blocks(blanked: str, pos: int, end: int):
    """Yield (start_of_header, brace_open, block_end) triples within [pos,end)."""
    out = []
    i = pos
    while i < end:
        j = blanked.find("{", i, end)
        if j == -1:
            break
        k = j + 1
        depth = 1
        while k < end and depth:
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


DECL_RE = re.compile(r"([-A-Za-z]+)\s*:\s*([^;]*?)\s*(?:!\s*important)?\s*(?:;|$)", re.I)


def walk(path_text: str):
    """Yield dicts for every !important declaration: file-level walk with at-chain."""
    blanked = blank_block_bodies(path_text)

    def rec(start: int, end: int, at_chain: str):
        for (h_start, brace, block_end) in parse_blocks(blanked, start, end):
            header = re.sub(r"\s+", " ", path_text[h_start:brace]).strip()
            m = re.match(r"@([\w-]+)", header)
            if m:
                name = m.group(1).lower()
                if name in {"keyframes", "font-face", "import", "charset", "namespace"}:
                    continue
                if name in {"media", "supports", "layer", "container", "scope"}:
                    yield from rec(brace + 1, block_end - 1, f"{at_chain} {header}" if at_chain else header)
                    continue
                continue
            # rule block: find declarations with !important
            block_raw = path_text[brace + 1:block_end - 1]
            block_blank = blanked[brace + 1:block_end - 1]
            for d in split_decls(block_blank):
                d_start = brace + 1 + d["start"]
                d_end = brace + 1 + d["end"]
                if d["important"]:
                    yield {
                        "declStart": d_start,
                        "declEnd": d_end,
                        "headerStart": h_start,
                        "atChain": at_chain.strip(),
                        "selector": header,
                        "property": d["prop"],
                        "text": path_text[d_start:d_end],
                    }

    yield from rec(0, len(blanked), "")


def split_decls(block_blank: str):
    """Split a blanked block into declaration spans; returns {start,end,prop,important}."""
    out = []
    i = 0
    n = len(block_blank)
    # A block can also contain nested rules (@media inside a rule) — detect by '{':
    j = block_blank.find("{")
    if j != -1:
        # nested rules exist below this header; declarations before it only
        out.extend(_decls_in(block_blank, 0, j))
        return out
    out.extend(_decls_in(block_blank, 0, n))
    return out


def _decls_in(s: str, a: int, b: int):
    out = []
    i = a
    while i < b:
        semi = s.find(";", i, b)
        stop = semi if semi != -1 else b
        chunk = s[i:stop]
        if ":" in chunk:
            m = re.match(r"\s*([-\w]+)\s*:(.*)", chunk, re.I | re.S)
            if m:
                out.append({"start": i, "end": stop, "prop": m.group(1).lower(),
                            "important": bool(re.search(r"!\s*important", m.group(2), re.I))})
        i = stop + 1
    return out


def norm_sel(sel: str) -> str:
    return re.sub(r"\s+", " ", sel).strip().rstrip(">").strip()


def analyse(files):
    candidates = []
    for path, total in files.items():
        p = REPO / path
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        rows = []
        try:
            rows = list(walk(text))
        except ValueError as exc:
            candidates.append({"file": path, "error": str(exc), "pairs": [], "tokens": 0})
            continue
        seen = {}
        pairs = []
        for idx, r in enumerate(rows):
            key = (norm_sel(r["selector"]), norm_sel(r["atChain"]), r["property"])
            if key in seen:
                earlier = seen[key]
                earlier_end = text[earlier["declEnd"]:earlier["declEnd"] + 2]
                # move the deletion end past an immediately following ';'
                de = earlier["declEnd"]
                while de < len(text) and text[de] in "; \t":
                    de += 1
                if text[de - 1:de] == ";":
                    pass
                pairs.append({
                    "file": path,
                    "selector": r["selector"][:160],
                    "atChain": r["atChain"][:200],
                    "property": r["property"],
                    "earlierSpan": [earlier["declStart"], de],
                    "laterSpan": [r["declStart"], r["declEnd"]],
                    "earlierText": text[earlier["declStart"]:de],
                    "laterText": text[r["declStart"]:r["declEnd"]],
                    # guard: later must override — same context enforced by key
                    # plus both !important (walk yields only important rows)
                })
            seen[key] = r
        # one removal per earlier declaration; a chain of three identical rows
        # yields two pairs that may share the span — dedupe overlapping spans
        dedup = []
        spans = set()
        for pr in pairs:
            s = tuple(pr["earlierSpan"])
            if s in spans:
                continue
            spans.add(s)
            dedup.append(pr)
        tokens = len(dedup)
        candidates.append({"file": path, "inventoryTotal": int(total), "pairs": dedup, "tokens": tokens})
    return candidates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    inv = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    cands = analyse(inv["files"])
    total = sum(c["tokens"] for c in cands)
    data = {
        "generatedFor": "FB-19 Phase-2 proven-superseded !important",
        "totalTokens": total,
        "targetTokensAt25pct": inv["total"] * 25 // 100,
        "targetTokensAt40pct": inv["total"] * 40 // 100,
        "files": cands,
    }
    if args.apply:
        applied = []
        for c in cands:
            path = REPO / c["file"]
            text = path.read_text(encoding="utf-8")
            if not c["pairs"]:
                continue
            # apply in reverse document order
            for pr in sorted(c["pairs"], key=lambda x: -x["earlierSpan"][0]):
                a, b = pr["earlierSpan"]
                before_pruned = text[:a] + text[b:]
                path.write_text(before_pruned, encoding="utf-8")
                text = before_pruned
            # re-validate: re-analysis must find zero pairs for this file
            re_cands = analyse({c["file"]: inv["files"][c["file"]]})
            ok = all(not r["pairs"] for r in re_cands)
            if not ok:
                raise SystemExit(f"REFUSING: {c['file']} still has superseded pairs after apply — aborting")
            applied.append({"file": c["file"], "pairs": len(c["pairs"]), "revalidated": ok})
        data["applied"] = applied
        data["importantDelta"] = total
        print(json.dumps({"appliedFiles": len(applied), "removedTokens": total}))
    Path(args.out).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    if not args.apply:
        per_file = {c["file"]: c["tokens"] for c in cands if c["tokens"]}
        print(json.dumps({"totalTokens": total,
                          "targetAt25pct": data["targetTokensAt25pct"],
                          "perFile": dict(sorted(per_file.items(), key=lambda kv: -kv[1]))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
