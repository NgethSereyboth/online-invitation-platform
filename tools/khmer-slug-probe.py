#!/usr/bin/env python3
"""khmer-slug-probe.py — what does the shipped slug function do to a Khmer title?

The question this answers
-------------------------
The platform's public link is ``/i/<slug>`` and the slug is produced by
``clean_slug`` in ``src/python/server.py``:

    def clean_slug(value):
        value = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
        return value[:60] or "our-invitation"

That character class keeps ``a-z``, ``0-9`` and ``-`` and replaces *everything
else* with a hyphen. Khmer is written in U+1780–U+17FF. So the question "can a
Khmer wedding title become a readable link today" is answerable by running the
real function over real Khmer input, rather than by reasoning about the regex.

This tool calls the shipped ``clean_slug`` — it does not re-implement it, so it
cannot drift from the behaviour it reports.

Where the Khmer input comes from
--------------------------------
**Nothing here is invented.** Every Khmer string is read out of the repository's
own translation table, ``docs/i18n/TRANSLATIONS.csv``, which is real Khmer
already in the tree. The probe de-duplicates and reports how many distinct values
it exercised. An ASCII control (``"Sok Dara"``) is included so the report shows
the function working as designed on the input it was written for.

Usage
    python3 tools/khmer-slug-probe.py             # human report
    python3 tools/khmer-slug-probe.py --json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# server.py imports the repo-root packages (``ai_agent``, ``platform_v32``,
# ``future_platform_v52``) as siblings, which is why render.yaml deliberately
# leaves rootDir unset and serve.py adds the repo root to sys.path. Both entries
# are needed — and ``src/python`` must end up FIRST, the same order
# tests/v15_http_integration_test.py uses. Reversed, ``import server`` finds the
# repo-root forwarder instead, whose runpy re-entry sets ``__name__ == "__main__"``
# and *starts the HTTP server*: the first version of this probe hung there and was
# killed at 120 s rather than reporting a slug.
ROOT_PATH = str(ROOT)
PY_PATH = str(ROOT / "src" / "python")
for entry in (ROOT_PATH, PY_PATH):
    if entry not in sys.path:
        sys.path.insert(0, entry)

TRANSLATIONS = ROOT / "docs" / "i18n" / "TRANSLATIONS.csv"
KHMER = re.compile(r"[\u1780-\u17ff]")
FALLBACK = "our-invitation"


def khmer_corpus(limit: int) -> list[str]:
    if not TRANSLATIONS.exists():
        raise SystemExit(f"khmer-slug-probe: missing corpus {TRANSLATIONS}")
    seen: list[str] = []
    with TRANSLATIONS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for value in row.values():
                if value and KHMER.search(value) and value not in seen:
                    seen.append(value)
    return seen[:limit]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=8, help="distinct Khmer strings to show")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    import server  # the shipped implementation, imported rather than copied

    # Guard the identity of what was imported: the forwarder at the repo root
    # shares the module name and would answer with the same function while also
    # having started a server on the way.
    if Path(server.__file__).resolve() != (ROOT / "src" / "python" / "server.py"):
        raise SystemExit(f"khmer-slug-probe: imported the wrong module: {server.__file__}")

    clean_slug = server.clean_slug
    corpus = khmer_corpus(args.limit)

    rows = []
    for value in corpus:
        rows.append(
            {
                "input": value,
                "input_chars": len(value),
                "output": clean_slug(value),
                "collapsed": clean_slug(value) == FALLBACK,
            }
        )
    control = {"input": "Sok Dara", "input_chars": 8, "output": clean_slug("Sok Dara"), "collapsed": False}

    collapsed = sum(1 for r in rows if r["collapsed"])
    result = {
        "implementation": "src/python/server.py::clean_slug (imported from the shipped module)",
        "corpus": str(TRANSLATIONS.relative_to(ROOT)),
        "distinct_khmer_strings_tested": len(rows),
        "collapsed_to_fallback": collapsed,
        "fallback": FALLBACK,
        "rows": rows,
        "ascii_control": control,
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(
            f"KHMER_SLUG_PROBE corpus={result['corpus']} "
            f"tested={len(rows)} collapsed={collapsed}/{len(rows)} "
            f"fallback={FALLBACK!r}"
        )
        print()
        print("input (truncated to 16 chars)  ->  slug")
        for row in rows:
            shown = row["input"][:16]
            mark = "  <-- collapsed to the fallback" if row["collapsed"] else ""
            print(f"{shown:<30} ->  {row['output']!r}{mark}")
        print(f"{control['input']:<30} ->  {control['output']!r}   (ASCII control)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
