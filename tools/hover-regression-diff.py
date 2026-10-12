#!/usr/bin/env python3
"""hover-regression-diff.py — prove a source change did not alter any hover state.

Why this exists
---------------
The `!important` demotion in this pass removes priority from ten `:hover`
declarations. "Nothing changed visually" is the whole safety argument, so it has
to be measured, not asserted. Screenshot diffing is the usual answer, but a
screenshot only shows what is painted in the viewport: a hover rule that expands
into ten longhands and loses one of them can round to the same pixels while the
computed value quietly changed.

This tool compares two runs of tools/hover-audit.mjs instead. `hover-audit.mjs`
writes one row per (trigger selector, element) pair carrying a `selfDiff` and
`subjectDiffs` map of `property: "before -> after"` for every property that
changed while `:hover` was forced. Two runs produce byte-identical rows when the
hover state is identical, and this tool reports exactly which property, on which
element, on which page, diverged.

Usage
-----
    python3 tools/hover-regression-diff.py --before <dir> --after <dir>

Both directories hold `hover-*.json` files as written by `hover-audit.mjs`
(artifacts/ when at the repo root, artifacts/hover-before-demotion/ for the
baseline this pass captured).

Exit status: 0 when every comparable row is identical, 1 when any row differs,
2 when there is nothing to compare (a missing directory, or no page in common).
A page present in only one directory is reported, not silently skipped: a page
that fails to measure is a hole in the evidence and must be visible.

Caveats this tool is honest about
---------------------------------
* Rows are matched by their position in the run plus (trigger, tag, cls), which
  is stable for a fixed page and viewport. If the two runs tested a different
  number of elements the page is reported as `shape-mismatch` rather than
  compared pairwise, because offset matching would then compare unlike rows.
* The audit measures the 16 shipped routes at the default viewport with the
  default cap. It does not exercise `@media(hover: none)` or dark theme.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PAGES = [
    "index", "dashboard", "public", "admin", "account", "billing", "verify",
    "reset", "privacy", "guests", "responses", "analytics", "materials",
    "checkin", "templates", "designer",
]


def rows_for(payload: dict) -> dict[int, dict]:
    """Key every tested element by `i`, its index in the page's tested-element list.

    `i` is assigned once per tested element before the changed/unchanged split, so
    it is stable across runs and independent of which bucket an element lands in.
    Keying on (trigger, tag, cls) instead would mis-pair rows whenever several
    elements share a class and one of them changes bucket, which manufactures
    hundreds of phantom diffs.
    """
    out: dict[int, dict] = {}
    for bucket in ("changed", "unchanged"):
        for row in payload.get(bucket, []):
            out[row["i"]] = row
    return out


def state_of(row: dict) -> dict:
    return {
        "selfDiff": row.get("selfDiff") or {},
        "subjectDiffs": row.get("subjectDiffs") or [],
        "isChange": bool(row.get("isChange")),
    }


def shape_of(row: dict) -> tuple:
    """What the row *is*: if this differs at the same `i`, the two runs tested
    different elements and the pair is not comparable.

    `cls` is deliberately NOT part of the identity. A page's own scripts add and
    remove classes after load (`fp-profile-button`, `active`, ..), so an element
    that is the same DOM node can report a different className in two runs on the
    same code. Measured: dashboard.html element 9 was `BUTTON.active` in one run
    and `BUTTON.fp-profile-button` in the other with no source change, which would
    otherwise be reported as a comparability failure rather than page noise. Class
    drift is counted separately (`clsDrift`) so it stays visible.
    """
    return (row.get("trigger"), row.get("tag"), tuple(row.get("subjects") or []))


def compare_page(before_path: Path, after_path: Path) -> dict:
    before = json.loads(before_path.read_text())
    after = json.loads(after_path.read_text())
    b_rows, a_rows = rows_for(before), rows_for(after)
    result = {
        "page": after_path.name[len("hover-"):-len(".json")],
        "beforeElements": before["summary"].get("elementsTested"),
        "afterElements": after["summary"].get("elementsTested"),
        "beforeChange": before["summary"].get("elementsWithVisibleChange"),
        "afterChange": after["summary"].get("elementsWithVisibleChange"),
        "compared": 0,
        "identical": 0,
        "differing": 0,
        "diffs": [],
        "shapeMismatch": b_rows.keys() != a_rows.keys(),
    }
    if result["shapeMismatch"]:
        only_before = [k for k in b_rows if k not in a_rows]
        only_after = [k for k in a_rows if k not in b_rows]
        result["onlyBefore"] = len(only_before)
        result["onlyAfter"] = len(only_after)
        return result
    for key in sorted(b_rows):
        b_row, a_row = b_rows[key], a_rows[key]
        if shape_of(b_row) != shape_of(a_row):
            result["shapeMismatch"] = True
            result["shapeDiffAt"] = result.get("shapeDiffAt", []) + [{
                "i": key, "before": shape_of(b_row), "after": shape_of(a_row)}]
            continue
        if b_row.get("cls") != a_row.get("cls"):
            result["clsDrift"] = result.get("clsDrift", 0) + 1
        result["compared"] += 1
        b_state, a_state = state_of(b_row), state_of(a_row)
        if b_state == a_state:
            result["identical"] += 1
            continue
        result["differing"] += 1
        props = sorted(set(b_state["selfDiff"]) | set(a_state["selfDiff"]))
        row_diff = {
            "i": key,
            "trigger": b_row.get("trigger"),
            "tag": b_row.get("tag"),
            "cls": b_row.get("cls"),
            "properties": props,
            "before": b_state["selfDiff"],
            "after": a_state["selfDiff"],
            "isChangeBefore": b_state["isChange"],
            "isChangeAfter": a_state["isChange"],
            "subjectsBefore": b_state["subjectDiffs"],
            "subjectsAfter": a_state["subjectDiffs"],
        }
        result["diffs"].append(row_diff)
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="hover-regression-diff.py",
        description="Compare two hover-audit artifact sets row by row.",
    )
    ap.add_argument("--before", default="artifacts/hover-before-demotion",
                    help="directory with the baseline hover-*.json files")
    ap.add_argument("--after", default="artifacts",
                    help="directory with the post-change hover-*.json files")
    ap.add_argument("--json", action="store_true", help="print the full JSON report")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    before_dir, after_dir = Path(args.before), Path(args.after)
    if not before_dir.is_dir() or not after_dir.is_dir():
        sys.stderr.write(
            f"hover-regression-diff.py: need two directories with hover-*.json\n"
            f"  before={before_dir} exists={before_dir.is_dir()}\n"
            f"  after ={after_dir} exists={after_dir.is_dir()}\n"
        )
        return 2

    pages, missing = [], []
    for page in PAGES:
        b, a = before_dir / f"hover-{page}.json", after_dir / f"hover-{page}.json"
        if b.is_file() and a.is_file():
            pages.append(compare_page(b, a))
        else:
            missing.append({"page": page, "before": b.is_file(), "after": a.is_file()})
    if not pages:
        sys.stderr.write("hover-regression-diff.py: no page present in both directories\n")
        return 2

    totals = {
        "pagesCompared": len(pages),
        "pagesMissing": len(missing),
        "elementsCompared": sum(p["compared"] for p in pages),
        "elementsIdentical": sum(p["identical"] for p in pages),
        "elementsDiffering": sum(p["differing"] for p in pages),
        "pagesShapeMismatch": sum(1 for p in pages if p["shapeMismatch"]),
        "clsDrift": sum(p.get("clsDrift", 0) for p in pages),
    }
    report = {"totals": totals, "pages": pages, "missing": missing}
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        print(f"HOVER_REGRESSION_TOTALS {json.dumps(totals)}")
        for p in pages:
            flag = "SHAPE-MISMATCH" if p["shapeMismatch"] else "ok"
            print(f"  {p['page']:<11} before={p['beforeElements']:<4} after={p['afterElements']:<4} "
                  f"changes {p['beforeChange']}->{p['afterChange']:<4} "
                  f"rows {p['compared']} identical {p['identical']} differing {p['differing']}  {flag}")
            if p["shapeMismatch"]:
                print(f"      only-before={p.get('onlyBefore')} only-after={p.get('onlyAfter')}")
            for d in p["diffs"][:20]:
                print(f"      DIFF i={d['i']} {d['trigger']} ({d['tag']}.{d['cls']}) "
                      f"props={d['properties']} isChange {d['isChangeBefore']}->{d['isChangeAfter']}")
                print(f"           self before={json.dumps(d['before'])}")
                print(f"           self after ={json.dumps(d['after'])}")
                if d["subjectsBefore"] != d["subjectsAfter"]:
                    print(f"           subj before={json.dumps(d['subjectsBefore'])}")
                    print(f"           subj after ={json.dumps(d['subjectsAfter'])}")
            if p.get("shapeDiffAt"):
                print(f"      SHAPE-DIFF-AT {json.dumps(p['shapeDiffAt'][:5])}")
        for m in missing:
            print(f"  MISSING {m['page']}: before={m['before']} after={m['after']}")
    if totals["pagesShapeMismatch"] or totals["elementsDiffering"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
