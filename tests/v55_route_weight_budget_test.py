#!/usr/bin/env python3
"""V55 route-weight budget gate — the Chrome-free half of the three-layer
performance budget.

Layer 1 (declarative)  docs/perf/lighthouse-budgets.json
                       per-route script / stylesheet / total ceilings in KB,
                       in the Lighthouse budget-file schema, so the same numbers
                       drive Lighthouse CI and this gate.
Layer 2 (build-time)   tests/v14_performance_budget_test.py
                       the pre-existing aspirational route budgets
                       (src/python/build/build_page_manifests.py: BUDGETS).
Layer 3 (gate)         tools/lighthouserc.js -> `lhci autorun` (real browser,
                       transfer sizes) and this file (byte sizes, no browser).
                       (Renamed from .lighthouserc.json on 2026-10-11; the
                       repo-root file was removed so there is exactly one
                       Lighthouse CI config.)

Why this file exists: Lighthouse's own `performance-budget` audit was removed
from Lighthouse core in v12 (https://github.com/GoogleChrome/lighthouse/issues/15203),
and Lighthouse CI can only serve one assert strategy at a time — either
`assert.budgetsFile` or `assert.assertions`, never both (LHCI configuration,
https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md).
The budget file is therefore the single source of truth, and this gate enforces
exactly the same numbers against the served assets, so a regression is caught
even where no Chrome is available.

Sizes in the budget file are kilobytes and are compared against *uncompressed*
bytes here, which is the conservative direction: any server that gzips will be
well under budget, while an unminified asset that grows will trip the gate.

Prints V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED and exits 0, or prints one line per
breach and exits 1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGET_FILE = ROOT / "docs" / "perf" / "lighthouse-budgets.json"
SERVED = ROOT / "src" / "python"
MANIFEST = ROOT / "docs" / "page-assets.json"


def find(rel: str) -> Path | None:
    """Resolve a manifest asset name to the file the server actually serves."""
    for candidate in (SERVED / rel, SERVED / Path(rel).name):
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    budgets = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pages = manifest["pages"]

    by_path = {b["path"].lstrip("/"): b for b in budgets}
    failures: list[str] = []
    checked = 0

    missing = [p for p in by_path if p not in pages]
    if missing:
        failures.append(f"budget file names pages that are not in the manifest: {missing}")

    for page, budget in sorted(by_path.items()):
        entry = pages.get(page)
        if not entry:
            continue
        checked += 1
        actual = {"script": 0, "stylesheet": 0}
        counts = {"script": 0, "stylesheet": 0}
        for kind, names in (("script", entry["scripts"]), ("stylesheet", entry["styles"])):
            for name in names:
                path = find(name)
                if path is None:
                    failures.append(f"{page}: manifest lists {name} but the server has no such file")
                    continue
                actual[kind] += path.stat().st_size
                counts[kind] += 1
        actual["total"] = actual["script"] + actual["stylesheet"]

        for size in budget.get("resourceSizes", []):
            kind = size["resourceType"]
            if kind not in actual:
                continue
            ceiling = size["budget"] * 1024
            if actual[kind] > ceiling:
                failures.append(
                    f"{page}: {kind} {actual[kind]:,} B exceeds budget {ceiling:,} B "
                    f"({size['budget']} KB) by {actual[kind] - ceiling:,} B"
                )
        for count in budget.get("resourceCounts", []):
            kind = count["resourceType"]
            if kind not in counts:
                continue
            if counts[kind] > count["budget"]:
                failures.append(
                    f"{page}: {kind} count {counts[kind]} exceeds budget {count['budget']}"
                )

    if failures:
        for line in failures:
            print(f"V55_ROUTE_WEIGHT_BUDGET_FAIL {line}")
        return 1

    print(f"V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED ({checked} pages within budget)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
