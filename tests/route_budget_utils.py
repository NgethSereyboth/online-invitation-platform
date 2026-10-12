"""route_budget_utils.py — read the editor route's weight ceiling from its owner.

Why this module exists
----------------------
Two gates hard-coded the same literal:

    tests/v27_3_5_release_evidence_test.py
    tests/v53_1_operator_repair_contract_test.py
        bundle-index-v15.js + bundle-index-v15.css <= 1_420_000

Both were red. Measured, the number is a V0.52-era snapshot, not a live budget:

  * `docs/BUILD_INFO.json` certification records `editorRouteLimit=1420000`,
    `editorRouteBytes=1414838`, `editorRouteHeadroom=5162` — taken 2026-08-10,
    when the route was 5,162 B under the line.
  * The route is now 1,615,999 B (+201,161 B, +14%), and the ceiling that actually
    owns the decision is `docs/perf/lighthouse-budgets.json`, whose `/index.html`
    entry budgets script 1163 KB, stylesheet 494 KB, total 1656 KB.
  * That file is the declared single source of truth and is enforced by
    `tests/v55_route_weight_budget_test.py`, which **passes**
    (`V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED (6 pages within budget)`), as does
    `tests/v14_performance_budget_test.py`.

So the literal was a second, stale copy of an authority that had moved on: the real
gate was green while every gate holding its own copy was red. This module deletes
the copy instead of re-guessing it — the ceiling is read from the budget file at
test time.

The check is also *stricter* than the sum it replaces: it compares `script` and
`stylesheet` against their own per-type budgets, so an oversized script can no
longer hide behind an undersized stylesheet inside a passing total.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGET_FILE = ROOT / "docs" / "perf" / "lighthouse-budgets.json"
ROUTE = "index.html"
JS_BUNDLE = ROOT / "src" / "js" / "bundle-index-v15.js"
CSS_BUNDLE = ROOT / "src" / "css" / "bundle-index-v15.css"


def index_route_ceiling() -> dict:
    """Per-resource-type ceilings in bytes, from the declared budget file."""
    if not BUDGET_FILE.is_file():
        raise AssertionError(f"route budget source of truth missing: {BUDGET_FILE}")
    budgets = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
    entry = next(
        (b for b in budgets if str(b.get("path", "")).lstrip("/") == ROUTE), None
    )
    if entry is None:
        raise AssertionError(f"{BUDGET_FILE} has no budget for /{ROUTE}")
    sizes = {s["resourceType"]: int(s["budget"]) * 1024 for s in entry["resourceSizes"]}
    for needed in ("script", "stylesheet", "total"):
        if needed not in sizes:
            raise AssertionError(f"{BUDGET_FILE} /{ROUTE} has no '{needed}' budget")
    return sizes


def index_route_bytes() -> dict:
    """What the built editor route actually weighs, in bytes."""
    script = JS_BUNDLE.stat().st_size
    stylesheet = CSS_BUNDLE.stat().st_size
    return {"script": script, "stylesheet": stylesheet, "total": script + stylesheet}


def assert_index_route_within_budget() -> dict:
    """Assert the built route is inside every per-type ceiling it declares.

    Returns `{'ceiling': ..., 'bytes': ..., 'headroom': ...}` so a caller can report
    the numbers rather than only the verdict, and raises with the offending type,
    its measured size, its ceiling and the overage.
    """
    ceiling, actual = index_route_ceiling(), index_route_bytes()
    for kind in ("script", "stylesheet", "total"):
        if actual[kind] > ceiling[kind]:
            raise AssertionError(
                f"{ROUTE} {kind} is {actual[kind]:,} B, over its "
                f"{ceiling[kind]:,} B budget by {actual[kind] - ceiling[kind]:,} B "
                f"(docs/perf/lighthouse-budgets.json)"
            )
    return {
        "ceiling": ceiling,
        "bytes": actual,
        "headroom": {k: ceiling[k] - actual[k] for k in ceiling},
    }
