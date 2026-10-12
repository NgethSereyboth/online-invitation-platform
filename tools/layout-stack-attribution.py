#!/usr/bin/env python3
"""layout-stack-attribution.py — attribute Layout and Recalculate-Style time to the
JS frame that caused it, using the stack traces the trace already carries.

Why this exists
---------------
`tools/perf-trace-compare.py` measured that index.html spends 2.65x Canva's
style+layout union time (2137.55 ms against 805.22 ms) and that it lays out 110
times to Canva's 37, but it could not say *which code* causes either. Its
`forcedLayoutProxyCount` (Layouts nested inside a script event) is a shape, not a
caller. `tools/forced-layout-attribution.mjs` answered the same question by
instrumenting the DOM for forced geometry reads — a different question, and a
costly one to keep correct.

What made the trace look uninformative was a reader bug, not a capture
limitation. The prior pass reported "the trace carries no `args.stackTrace` on any
Layout event even with the `disabled-by-default-devtools.timeline.stack` category
enabled" and labelled the cause UNVERIFIED. Measured on
`artifacts/goal3-index-run1-trace.json`:

    Layout events                                          107
    Layout events with a stack at args.beginData.stackTrace 79
    UpdateLayoutTree events with the same                   98
    events with a stack at top-level args.stackTrace         0

Blink's `SetCallStack` attaches the stack to the event's own data dictionary, so
for Layout it lands at `args.beginData.stackTrace`, not `args.stackTrace`. The
category was enabled and working the whole time.

    https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/core/inspector/inspector_trace_events.cc
    https://chromium.googlesource.com/chromium/src/+/main/base/trace_event/builtin_categories.h

Method
------
   1. Keep complete events (ph == 'X') on the main renderer thread — the tid that
      emitted the target event name. Frame intervals are not reconstructed: the
      trace gives each event its own stack, so no ancestor walk is needed.
   2. For each target event, read its stack (`args.beginData.stackTrace`, then
      `args.endData`, `args.data`, then the top level, then any depth — one
      helper, shared with `perf-trace-compare.py`).
   3. Aggregate the event's `dur` by CALLER, two ways, because they answer two
      different questions:
        innermost  — the first frame in the stack: the statement that caused it;
        outermost  — the last frame: the entry point that owns the work.
      A frame that is the V8 "anonymous" holder (empty functionName) is still
      counted, keyed by its URL, rather than dropped.
   4. Report events with NO stack separately, with their total ms, so the
      attributable fraction is explicit instead of implied.

A caller is keyed by `functionName@file:line`, with the file reduced to its
basename and its query string removed so `bundle-index-v15.js` from the served
origin and from a cache-busted URL aggregate together.

Usage
    python3 tools/layout-stack-attribution.py artifacts/goal3-index-run1-trace.json
    python3 tools/layout-stack-attribution.py --json --top=20 --event=Layout a.json b.json
    python3 tools/layout-stack-attribution.py --paths artifacts/goal3-index-run1-trace.json

`--paths` prints only step 2's answer — where inside `args` each event name keeps its
stack, and how many events carry one. That is the measurement the prior pass lacked:
run it on any of its traces and it reports 79 of 107 Layout events at
`args.beginData.stackTrace`, against a top-level count of zero.

Exit status is 0 whenever the trace(s) parsed; this reports a distribution, it
does not assert a target.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

# Chrome's internal names differ from the DevTools panel labels:
#   UpdateLayoutTree -> "Recalculate Style"; Layout -> "Layout"
TARGET_EVENTS = ("Layout", "UpdateLayoutTree")


def load(path: Path) -> list[dict]:
    with path.open() as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "traceEvents" in data:
        return data["traceEvents"]
    if isinstance(data, list):
        return data
    raise SystemExit(f"{path}: not a CDP trace (expected {{'traceEvents': [...]}})")


def stack_of(event: dict) -> list[dict] | None:
    """The stack attached to an event, wherever Blink put it.

    Kept identical in behaviour to `perf-trace-compare.py::stack_of`, deliberately:
    the two readers must not disagree about whether a trace carries stacks.
    """
    args = event.get("args") or {}
    top = args.get("stackTrace")
    if top:
        return top
    for holder in ("beginData", "endData", "data"):
        nested = (args.get(holder) or {}).get("stackTrace")
        if nested:
            return nested
    walk = [args]
    while walk:
        cur = walk.pop()
        for key, value in cur.items():
            if key == "stackTrace" and value:
                return value
            if isinstance(value, dict):
                walk.append(value)
    return None


def stack_paths(events: list[dict], names: tuple[str, ...]) -> dict:
    """Where inside `args` each event name keeps its stack, and how many have one.

    This is the measurement that corrected the prior pass's conclusion. It is a
    first-class output rather than a throwaway probe because the claim it supports
    ("the stack is at args.beginData.stackTrace, not args.stackTrace") is the reason
    every attribution below is possible.
    """
    out: dict = {}
    for name in names:
        paths: dict[str, int] = {}
        total = 0
        for e in events:
            if e.get("ph") != "X" or e.get("name") != name:
                continue
            total += 1
            hit = None
            walk = [((), e.get("args") or {})]
            while walk and not hit:
                prefix, node = walk.pop(0)
                for key, value in node.items():
                    if key == "stackTrace" and value:
                        hit = ".".join(("args",) + prefix + (key,))
                        break
                    if isinstance(value, dict):
                        walk.append((prefix + (key,), value))
            paths[hit or "(none)"] = paths.get(hit or "(none)", 0) + 1
        out[name] = {"events": total, "paths": dict(sorted(paths.items(), key=lambda kv: -kv[1]))}
    return out


def frame_key(frame: dict | None) -> str:
    if not frame:
        return "(no frame)"
    url = frame.get("url") or f"scriptId:{frame.get('scriptId')}"
    name = urlsplit(url).path.rsplit("/", 1)[-1] or url
    fn = frame.get("functionName") or "(anonymous)"
    line = frame.get("lineNumber")
    col = frame.get("columnNumber")
    where = name if line is None else f"{name}:{line}:{col}"
    return f"{fn}@{where}"


def analyse(path: Path, events_of_interest: tuple[str, ...], top: int) -> dict:
    events = load(path)

    complete = [e for e in events if e.get("ph") == "X" and isinstance(e.get("dur"), (int, float))]
    out: dict = {"file": str(path), "events": len(events), "byEvent": {}}

    for name in events_of_interest:
        rows = [e for e in complete if e.get("name") == name]
        if not rows:
            continue
        # Main renderer thread: the tid that emitted the most of this event.
        counts: dict[int, int] = {}
        for e in rows:
            counts[e.get("tid")] = counts.get(e.get("tid"), 0) + 1
        tid = max(counts, key=lambda t: counts[t])
        rows = [e for e in rows if e.get("tid") == tid]

        inner: dict[str, dict] = {}
        outer: dict[str, dict] = {}
        by_file: dict[str, dict] = {}
        no_stack = {"count": 0, "ms": 0.0}
        for e in rows:
            ms = (e.get("dur") or 0) / 1000.0
            stack = stack_of(e)
            if not stack:
                no_stack["count"] += 1
                no_stack["ms"] += ms
                continue
            first = stack[0] if stack else None
            last = stack[-1] if stack else None
            for table, frame in ((inner, first), (outer, last)):
                key = frame_key(frame)
                slot = table.setdefault(key, {"caller": key, "ms": 0.0, "count": 0, "max": 0.0})
                slot["ms"] += ms
                slot["count"] += 1
                slot["max"] = max(slot["max"], ms)
            url = (first or {}).get("url") or "(none)"
            base = urlsplit(url).path.rsplit("/", 1)[-1] or url
            slot = by_file.setdefault(base, {"file": base, "ms": 0.0, "count": 0})
            slot["ms"] += ms
            slot["count"] += 1

        def ranked(table: dict[str, dict]) -> list[dict]:
            return sorted(table.values(), key=lambda r: -r["ms"])[:top]

        out["byEvent"][name] = {
            "tid": tid,
            "events": len(rows),
            "totalMs": round(sum((e.get("dur") or 0) / 1000.0 for e in rows), 2),
            "withStack": len(rows) - no_stack["count"],
            "noStack": {"count": no_stack["count"], "ms": round(no_stack["ms"], 2)},
            "byInnermostCaller": [
                {**r, "ms": round(r["ms"], 2), "max": round(r["max"], 2)} for r in ranked(inner)
            ],
            "byOutermostCaller": [
                {**r, "ms": round(r["ms"], 2), "max": round(r["max"], 2)} for r in ranked(outer)
            ],
            "byFile": [{**r, "ms": round(r["ms"], 2)} for r in ranked(by_file)],
        }
    return out


def fmt(report: dict, top: int) -> str:
    lines = [f"LAYOUT_STACK_ATTRIBUTION {json.dumps({'file': report['file'], 'events': report['events']})}"]
    for name, data in report["byEvent"].items():
        lines.append("")
        lines.append(
            f"=== {name} — main thread tid={data['tid']}: "
            f"{data['events']} events, {data['totalMs']} ms, "
            f"{data['withStack']} with a stack, "
            f"{data['noStack']['count']} without ({data['noStack']['ms']} ms)"
        )
        coverage = (data["withStack"] / data["events"] * 100) if data["events"] else 0
        lines.append(f"    stack coverage {coverage:.1f}% of events")
        for title, key in (("by INNERMOST caller (the statement that caused it)", "byInnermostCaller"),
                           ("by OUTERMOST caller (the entry point that owns the work)", "byOutermostCaller"),
                           ("by FILE of the innermost frame", "byFile")):
            lines.append(f"  --- {title} ---")
            for row in data[key]:
                label = row.get("caller") or row.get("file")
                lines.append(
                    f"    {row['ms']:9.2f} ms  n={row['count']:<4}"
                    + (f" max={row['max']:.2f} ms  " if "max" in row else "              ")
                    + label
                )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("traces", nargs="*", help="trace JSON files written by tools/canva-probe.mjs or the trace tools")
    ap.add_argument("--event", action="append", default=[], help=f"restrict to this event name (repeatable; default {'/'.join(TARGET_EVENTS)})")
    ap.add_argument("--top", type=int, default=12, help="rows per table (default 12)")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    ap.add_argument("--paths", action="store_true",
                    help="print only where inside `args` each event keeps its stack — the "
                         "measurement that shows the stack is at args.beginData.stackTrace")
    args = ap.parse_args()

    if not args.traces:
        raise SystemExit("no traces given")
    events_of_interest = tuple(args.event) if args.event else TARGET_EVENTS

    if args.paths:
        for spec in args.traces:
            path = Path(spec)
            if not path.is_file():
                raise SystemExit(f"{path}: no such trace")
            table = stack_paths(load(path), events_of_interest)
            print(f"LAYOUT_STACK_PATHS {json.dumps({'file': str(path)})}")
            for name, data in table.items():
                top = next(iter(data["paths"]), "(none)")
                print(f"  {name:<18} {data['events']:>5} events   most common path: {top}")
                for p, count in data["paths"].items():
                    print(f"      {count:>5}  {p}")
        return 0

    reports = []
    for spec in args.traces:
        path = Path(spec)
        if not path.is_file():
            raise SystemExit(f"{path}: no such trace")
        reports.append(analyse(path, events_of_interest, args.top))

    if args.json:
        print(json.dumps({"reports": reports}, indent=1))
    else:
        for report in reports:
            print(fmt(report, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
