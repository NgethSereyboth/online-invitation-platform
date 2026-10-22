#!/usr/bin/env python3
"""fb19-merge-dead.py — merge the static scan and the live-DOM probe into the
final provably-dead `!important` list (FB-19 Phase 1).

A rule is PROVABLY DEAD only when **both** hold:
  1. static: every compound class/id token in its selector is absent from all
     shipped HTML/JS sources (fb19-dead-important.py), and
  2. probe: its selector matched no element in any page/viewport/theme/lang
     combo the fb19-probe-dom.py matrix visited (or the probe file is absent —
     then the rule is reported as "static-only", NOT counted dead).

Output: provably-dead.json with per-rule entries {file, atChain, selector,
tokens, occurrences} plus per-file token totals for batch planning. The rule
must still be re-confirmed after editing by the byte-diff of the served CSS
(r2 matrix run + digest compare) before any commit.

Usage:
  python3 tools/fb19-merge-dead.py \
      --static artifacts/next-work/fb-19/dead-rules-static.json \
      --probe artifacts/next-work/fb-19/probe/dom-presence.json \
      --out artifacts/next-work/fb-19/provably-dead.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", required=True)
    ap.add_argument("--probe")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    static = json.loads(Path(args.static).read_text(encoding="utf-8"))
    live = set()
    probe_missing = True
    if args.probe and Path(args.probe).is_file():
        probe_missing = False
        probe = json.loads(Path(args.probe).read_text(encoding="utf-8"))
        for row in probe.get("selectors", []):
            if row.get("selector") and row.get("liveAny"):
                live.add(row["selector"].strip())

    merged, rejected = [], []
    for e in static.get("candidates", []):
        # The probe evaluates each candidate as a WHOLE selector list
        # (querySelectorAll over the comma text): a row is live when ANY
        # alternative matched. A rule is provably dead only when the probe row
        # for the full selector list is dead — testing individual comma parts
        # against full-row keys once killed live alternatives of multi-
        # selector rules (e.g. `button, .cta, …` — the plain `button` part
        # matches every button, while the class alternatives are absent).
        if e["tokensAbsentFromSources"] is not True:
            rejected.append({"selector": e["selector"], "reason": "static-absent lost"})
            continue
        full_selector = e["selector"].strip()
        has_live = full_selector in live
        entry = dict(e)
        entry["probeCovered"] = not probe_missing
        entry["liveInProbe"] = has_live
        if has_live:
            rejected.append({"selector": e["selector"], "file": e["file"],
                             "reason": "selector matched a live DOM page"})
            continue
        if probe_missing:
            rejected.append({"selector": e["selector"], "file": e["file"],
                             "reason": "probe data missing — not counted dead"})
            continue
        merged.append(entry)

    tokens = sum(e["importantCount"] for e in merged)
    per_file = defaultdict(int)
    per_file_rules = defaultdict(int)
    for e in merged:
        per_file[e["file"]] += e["importantCount"]
        per_file_rules[e["file"]] += 1
    out = {
        "generatedFor": "FB-19 Phase-1 provably-dead set (static + live probe)",
        "inventoryTotalImportant": static["inventoryTotalImportant"],
        "targetTokensAt25pct": static["targetTokensAt25pct"],
        "targetTokensAt40pct": static["targetTokensAt40pct"],
        "provablyDeadRules": len(merged),
        "provablyDeadTokens": tokens,
        "percentOfInventory": round(100 * tokens / max(1, static["inventoryTotalImportant"]), 2),
        "rejected": rejected,
        "perFileTokens": dict(sorted(per_file.items(), key=lambda kv: -kv[1])),
        "perFileRules": dict(per_file_rules),
        "rules": merged,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("provablyDeadRules", "provablyDeadTokens",
                                          "percentOfInventory", "targetTokensAt25pct")}))
    print("per file:", json.dumps(out["perFileTokens"], indent=1))
    print("rejected:", len(rejected))


if __name__ == "__main__":
    main()
