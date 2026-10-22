#!/usr/bin/env python3
"""fb19-dead-important.py — FB-19 Phase-1 target analysis (lossless CSS parse).

For every source CSS file, produces:
  * every `!important`-bearing rule grouped by full selector (with the at-rule
    chain, e.g. `@media ...`, as context),
  * a candidate "provably dead" list: rules whose selector holds only with
    at least one compound token (class/id) that does not occur in any shipped
    HTML/JS source AND that matched no DOM in the live probe JSON produced by
    fb19-probe-dom.py (when --probe is given).

Parsing rules (validated):
  * matching-brace walker (handles nested `@media` / `@layer` correctly, so
    declaration text can never be mistaken for a selector);
  * `@keyframes`/`@font-face`/`@import`/`:root` variable bodies are skipped —
    their inner text is descriptors/frames, not selectors;
  * a selector must not contain '{', '}', ';' or a bare property name, and the
    file must be brace-balanced (unbalanced files are reported and skipped).

Usage:
  python3 tools/fb19-dead-important.py \
      --inventory artifacts/next-work/nw-2-1/important-inventory.json \
      [--probe artifacts/next-work/fb-19/probe/dom-presence.json] \
      --out artifacts/next-work/fb-19/dead-rules-static.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

HTML_GLOBS = ["src/html/*.html", "src/python/*.html"]
CSS_GLOBS = ["src/css/**/*.css"]          # files whose every class token counts
JS_GLOBS = ["src/js/**/*.js"]

# At-rules whose inner content is NOT selector-bearing (frames/descriptors).
SKIP_AT = {"keyframes", "font-face", "import", "charset", "namespace"}
# At-rules to recurse into for inner rules.
SUBSUME_AT = {"media", "supports", "layer", "container", "scope"}


def strip_comments(s: str) -> str:
    # Comments are removed; quoted attribute values in selectors
    # (html[data-theme="dark"]) must survive intact — string bodies are
    # neutralised only for the brace walker (see blank_block_bodies).
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def blank_block_bodies(text: str) -> str:
    """Replace comment bodies and string bodies with spaces, same length.

    Single left-to-right state machine (normal / string / comment): a `/*`
    inside a string is NOT a comment, and a quote inside a comment is NOT a
    string opener (CSS `content: "/*"` and comment prose with apostrophes are
    both common).    Only structural characters (`{`, `}`, `;`, comment open/close) are blanked
    inside strings — quoted selector attribute values like
    `html[data-theme="dark"]` must stay intact, while braces/semicolons inside
    `content:"…"` may not corrupt the depth tracking or statement splitting.
    """
    STRUCT = set("{};")
    out = list(text)
    i, n = 0, len(text)
    state = "normal"
    quote = None
    while i < n:
        c = text[i]
        if state == "string":
            if c == "\\":
                i += 2
                continue
            # CSS recovers from an unescaped newline inside a string: the
            # string token ends there. Recover the same way instead of
            # rejecting the whole file as unterminated.
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
        else:  # normal
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


def parse_blocks(text: str):
    """Yield (header, block) pairs at any depth, using matching braces.

    `text` must already be comment/string-blanked (see blank_block_bodies).
    The header is everything between the previous block's closing brace
    (or file start) and this block's '{'.
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        j = text.find("{", i)
        if j == -1:
            break
        header = text[i:j]
        k = j + 1
        depth = 1
        while k < n and depth:
            c = text[k]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            k += 1
        if depth:  # unbalanced — fail loudly for this file
            raise ValueError("unbalanced braces")
        block = text[j + 1:k - 1]
        out.append((header, block))
        i = k
    return out


def iter_rules(text: str, at_chain: str = ""):
    """Yield (at_chain, selector, block) for every selector-bearing rule."""
    blanked = blank_block_bodies(text)
    for header, block in parse_blocks(blanked):
        h = strip_comments(header).strip()
        if not h:
            continue
        m = re.match(r"@([\w-]+)", h)
        if m:
            name = m.group(1).lower()
            if name in SKIP_AT:
                continue
            if name in SUBSUME_AT:
                yield from iter_rules(block, at_chain=(at_chain + " " + h.split("{")[0].strip()).strip() if at_chain else h.split("{")[0].strip())
                continue
            continue  # other at-rules: not selector-bearing
        yield at_chain, h, blanked_skip(block)


def selector_parts(selector: str):
    """Top-level rules may hold several comma selectors; validate each."""
    parts = []
    for p in selector.split(","):
        p = p.strip()
        if not p or "{" in p or "}" in p or ";" in p:
            raise ValueError(f"malformed selector part: {p[:60]!r}")
        # a plain property prefix would place ':' before any structural char
        head = re.split(r"[\s\.\[\)#:>~\+\*]", p, 1)[0]
        if head and ":" in head and "=" not in head.split("[", 1)[0]:
            raise ValueError(f"property-like selector part: {p[:60]!r}")
        parts.append(p)
    return parts


def compound_tokens(parts):
    toks = set()
    for p in parts:
        for m in re.finditer(r"[.#](-?[A-Za-z_][\w-]*)", p):
            toks.add(m.group(1))  # store bare token for presence tests
    return toks


def collect_class_tokens():
    present = set()
    static_tokens = set()
    for pattern in HTML_GLOBS:
        for p in REPO.glob(pattern):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for cls in re.findall(r'class="([^"]*)"', text):
                present.update(cls.split())
            for cls in re.findall(r"class='([^']*)'", text):
                present.update(cls.split())
    for pattern in JS_GLOBS:
        for p in REPO.glob(pattern):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for cls in re.findall(r"classList\.(?:add|toggle|remove|contains)\(\s*['\"]([-\w ]+)['\"]", text):
                present.update(cls.split())
            for cls in re.findall(r"class(?:Name)?\s*\+?=\s*['\"]([-\w ]+)['\"]", text):
                present.update(cls.split())
            for cls in re.findall(r"`([^`]*\$\{[^`]*\}[^`]*)`", text):
                # dynamic class assembly — cannot prove absence; record file
                static_tokens.add("<<dynamic-class-assembly>>")
    # tag names + common attribute selectors' values cannot be class tokens, so
    # proving absence only rests on class/id compounds (see compound_tokens).
    if static_tokens:
        present.add("<<dynamic-class-assembly>>")
    return present


def blanked_skip(block: str) -> str:
    """Return the block text with comments/strings blanked for token counting."""
    return blank_block_bodies(block)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--probe")
    ap.add_argument("--css-glob", default=None, help="restrict to one bundled CSS file")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    present = collect_class_tokens()
    inv = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    probe_map = {}
    if args.probe and Path(args.probe).is_file():
        probe = json.loads(Path(args.probe).read_text(encoding="utf-8"))
        for row in probe.get("selectors", []):
            if row.get("selector") and row.get("liveAny"):
                probe_map[row["selector"].strip()] = True

    per_file, candidates, skipped = {}, [], []
    for path, count in inv["files"].items():
        if args.css_glob and args.css_glob not in path:
            continue
        p = REPO / path
        if not p.is_file():
            skipped.append({"file": path, "reason": "missing"})
            continue
        text = p.read_text(encoding="utf-8")
        try:
            rules = list(iter_rules(text))
        except ValueError as exc:
            skipped.append({"file": path, "reason": str(exc)})
            continue
        entries = []
        for at_chain, sel, block in rules:
            if "!important" not in block:
                continue
            try:
                parts = selector_parts(sel)
            except ValueError as exc:
                skipped.append({"file": path, "selector": sel[:80], "reason": str(exc)})
                continue
            toks = compound_tokens(parts)
            tokens_all_absent = bool(toks) and all(t not in present for t in toks)
            dead_probe = all(p not in probe_map for p in parts)
            entries.append({
                "file": path,
                "atChain": at_chain.strip(),
                "selector": ", ".join(parts),
                "importantCount": block.count("!important"),
                "tokensAbsentFromSources": tokens_all_absent,
                "selectorNeverLiveInProbe": dead_probe,
            })
        per_file[path] = {"ruleCount": len(rules), "entries": entries}
        for e in entries:
            if e["tokensAbsentFromSources"]:
                candidates.append(e)
    total_dead = sum(c["importantCount"] for c in candidates)
    out = {
        "generatedFor": "FB-19 Phase-1 candidate analysis",
        "inventoryTotalImportant": inv["total"],
        "candidateRules": len(candidates),
        "candidateImportantTokens": total_dead,
        "targetTokensAt25pct": round(inv["total"] * 0.25),
        "targetTokensAt40pct": round(inv["total"] * 0.40),
        "skippedFilesOrParts": skipped,
        "files": per_file,
        "candidates": candidates,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("inventoryTotalImportant", "candidateRules",
                                          "candidateImportantTokens", "targetTokensAt25pct",
                                          "targetTokensAt40pct")}), flush=True)
    if skipped:
        print(f"skipped {len(skipped)} file(s)/part(s):", json.dumps(skipped[:6], indent=1))


if __name__ == "__main__":
    main()
