#!/usr/bin/env python3
"""perf-trace-compare.py — read two CDP traces and print one comparison table.

Why this exists
---------------
`tools/style-layout-trace.mjs` answers "where did Style & Layout go on *this*
page" and prints it. Goal 0 of the Canva-analysis pass asks a different question:
"how does this page's main-thread profile differ from that site's". That needs
two traces read the same way and one table, so the arithmetic lives here rather
than in a report paragraph.

Input is the JSON that `tools/canva-probe.mjs` writes (`<prefix>-trace.json`,
a list of raw CDP events). Any page traced with that tool can be a column —
Canva's public pages and this project's served pages are traced identically, so
the comparison is like-for-like.

What is measured, and the definition used for each
    style        union of `UpdateLayoutTree` intervals on the busiest thread
                 (union, not sum: recalc events nest and a sum double-counts)
    layout       union of `Layout` intervals, same rule
    script       union of `EvaluateScript` + `FunctionCall` + `v8.run` +
                 `v8.compile` + `RunMicrotasks` intervals
    tasks        the N longest complete `RunTask` events (top-level main-thread work)
    forced       `Layout` events that are *nested inside* a script event on the
                 same thread, i.e. the layout was begun from JS with no frame in
                 between. This is a proxy, and it is labelled as one. It was the
                 only signal available when this file was written, because the
                 stack was looked for at the wrong place — see `stack_of()`.

Where the stack actually lives (a correction, measured)
    A previous pass reported "the trace carries no `args.stackTrace` on any Layout
    event even with the `disabled-by-default-devtools.timeline.stack` category"
    and concluded the stack was unavailable. That was a false negative from this
    reader, not a limitation of the capture: it checked only the TOP-LEVEL
    `args.stackTrace`. Measured on artifacts/goal3-index-run1-trace.json: 79 of
    107 Layout events and 98 UpdateLayoutTree events carry the stack one level
    down, at `args.beginData.stackTrace` — the same nesting Blink uses for other
    forced-work events (`SetCallStack` attaches the stack to the event's own data
    dictionary, not to `args`). `stack_of()` therefore searches `args` at any
    depth, and `layoutEventsWithStackTrace` counts those.

    Chromium sources:
      https://chromium.googlesource.com/chromium/src/+/main/base/trace_event/builtin_categories.h
      https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/core/inspector/inspector_trace_events.cc

Usage
    python3 tools/perf-trace-compare.py artifacts/canva-trace.json artifacts/project-index-trace.json
    python3 tools/perf-trace-compare.py --label canva=artifacts/canva-trace.json --label mine=artifacts/mine-trace.json
    python3 tools/perf-trace-compare.py ... --json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Chrome's internal names differ from the DevTools panel's labels:
#   UpdateLayoutTree -> "Recalculate Style"      Layout -> "Layout"
STYLE_EVENTS = ("UpdateLayoutTree", "ParseAuthorStyleSheet", "RecalcStyle")
LAYOUT_EVENTS = ("Layout",)
SCRIPT_EVENTS = ("EvaluateScript", "FunctionCall", "v8.run", "v8.compile", "RunMicrotasks", "v8.callFunction")
TASK_EVENTS = ("RunTask",)


def stack_of(event: dict) -> list[dict] | None:
    """The stack trace attached to a trace event, wherever Blink put it.

    Blink's `SetCallStack` writes the stack into the event's own data
    dictionary, so for a Layout event it lands at `args.beginData.stackTrace`
    (measured: 79/107 on index.html) while `args.stackTrace` is empty. Searching
    only the top level produced the prior pass's "no stack traces" conclusion.
    Prefer the documented top-level location when a future Chrome emits it there.
    """
    args = event.get("args") or {}
    top = args.get("stackTrace")
    if top:
        return top
    for holder in ("beginData", "endData", "data"):
        nested = (args.get(holder) or {}).get("stackTrace")
        if nested:
            return nested
    # Any other nesting depth, so a renamed holder does not silently report 0.
    stack = [args]
    while stack:
        cur = stack.pop()
        for key, value in cur.items():
            if key == "stackTrace" and value:
                return value
            if isinstance(value, dict):
                stack.append(value)
    return None


def load(path: Path) -> list[dict]:
    with path.open() as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "traceEvents" in data:
        return data["traceEvents"]
    if isinstance(data, list):
        return data
    raise SystemExit(f"{path}: not a CDP trace (expected {{'traceEvents': [...]}})")


def complete(events: list[dict], names) -> list[dict]:
    wanted = set(names)
    return [e for e in events if e.get("ph") == "X" and e.get("name") in wanted]


def busiest_thread(events: list[dict]) -> tuple[int | None, int | None] | None:
    """(pid, tid) of the thread with the most style/layout work — the renderer's main thread."""
    counts: dict[tuple, int] = {}
    for e in complete(events, STYLE_EVENTS + LAYOUT_EVENTS):
        counts[(e.get("pid"), e.get("tid"))] = counts.get((e.get("pid"), e.get("tid")), 0) + (e.get("dur") or 0)
    if not counts:
        return None
    (pid, tid) = max(counts.items(), key=lambda kv: kv[1])[0]
    return pid, tid


def union_ms(events: list[dict], names, pid=None, tid=None) -> float:
    """Non-overlapping union of the matching intervals, in milliseconds."""
    iv = [
        (e.get("ts") or 0, (e.get("ts") or 0) + (e.get("dur") or 0))
        for e in complete(events, names)
        if (pid is None or e.get("pid") == pid) and (tid is None or e.get("tid") == tid)
    ]
    if not iv:
        return 0.0
    iv.sort()
    total = 0
    start, end = iv[0]
    for s, e in iv[1:]:
        if s <= end:
            end = max(end, e)
        else:
            total += end - start
            start, end = s, e
    total += end - start
    return total / 1000.0


def top_ms(events: list[dict], names, n, pid=None, tid=None) -> list[dict]:
    rows = [
        {
            "name": e.get("name"),
            "ms": (e.get("dur") or 0) / 1000.0,
            "startMs": (e.get("ts") or 0) / 1000.0,
            "beginData": (e.get("args") or {}).get("beginData"),
        }
        for e in complete(events, names)
        if (pid is None or e.get("pid") == pid) and (tid is None or e.get("tid") == tid)
    ]
    rows.sort(key=lambda r: r["ms"], reverse=True)
    return rows[:n]


def forced_layout_proxy(events: list[dict], tid=None) -> tuple[int, float]:
    """Layout events nested inside a script event on the same thread (see module docstring)."""
    scripts = [
        (e.get("ts") or 0, (e.get("ts") or 0) + (e.get("dur") or 0))
        for e in complete(events, SCRIPT_EVENTS)
        if tid is None or e.get("tid") == tid
    ]
    if not scripts:
        return 0, 0.0
    scripts.sort()
    count = 0
    total = 0.0
    for e in complete(events, LAYOUT_EVENTS):
        if tid is not None and e.get("tid") != tid:
            continue
        ts = e.get("ts") or 0
        for lo, hi in scripts:
            if lo <= ts <= hi:
                count += 1
                total += (e.get("dur") or 0) / 1000.0
                break
    return count, total


def analyse(path: Path) -> dict:
    events = load(path)
    thread = busiest_thread(events)
    pid, tid = thread if thread else (None, None)
    forced_n, forced_ms = forced_layout_proxy(events, tid=tid)
    # Counted where the stack actually is (`args.beginData.stackTrace`), not only at
    # the top level. Before this fix the same traces reported 0 for index.html's 79
    # stacked Layout events — the measurement the prior pass read as "unavailable".
    with_stack = len([e for e in complete(events, LAYOUT_EVENTS) if stack_of(e)])
    return {
        "file": str(path),
        "events": len(events),
        "thread": {"pid": pid, "tid": tid},
        "styleLayoutMergedMs": round(union_ms(events, STYLE_EVENTS + LAYOUT_EVENTS, pid, tid), 2),
        "styleMergedMs": round(union_ms(events, STYLE_EVENTS, pid, tid), 2),
        "styleAllThreadsMs": round(union_ms(events, STYLE_EVENTS), 2),
        "layoutMergedMs": round(union_ms(events, LAYOUT_EVENTS, pid, tid), 2),
        "layoutAllThreadsMs": round(union_ms(events, LAYOUT_EVENTS), 2),
        "scriptMergedMs": round(union_ms(events, SCRIPT_EVENTS, pid, tid), 2),
        "styleEvents": len(complete(events, STYLE_EVENTS)),
        "layoutEvents": len(complete(events, LAYOUT_EVENTS)),
        "taskCount": len(complete(events, TASK_EVENTS)),
        "longestTasks": top_ms(events, TASK_EVENTS, 10),
        "longestLayouts": top_ms(events, LAYOUT_EVENTS, 10),
        "forcedLayoutProxyCount": forced_n,
        "forcedLayoutProxyMs": round(forced_ms, 2),
        "layoutEventsWithStackTrace": with_stack,
    }


def fmt_table(rows: list[dict]) -> str:
    keys = [
        ("trace events", "events"),
        ("style+layout union ms (main thread)", "styleLayoutMergedMs"),
        ("  style recalc union ms", "styleMergedMs"),
        ("  layout union ms", "layoutMergedMs"),
        ("  style recalc union ms (all threads)", "styleAllThreadsMs"),
        ("  layout union ms (all threads)", "layoutAllThreadsMs"),
        ("Script union ms (main thread)", "scriptMergedMs"),
        ("UpdateLayoutTree events", "styleEvents"),
        ("Layout events", "layoutEvents"),
        ("RunTask events", "taskCount"),
        ("Layouts nested in script (forced proxy)", "forcedLayoutProxyCount"),
        ("Layouts with stackTrace", "layoutEventsWithStackTrace"),
    ]
    labels = [r["label"] for r in rows]
    width = max(len(k) for k, _ in keys) + 2
    out = ["TRACE_COMPARE " + json.dumps({r["label"]: r["data"]["events"] for r in rows})]
    out.append(f"{'metric':<{width}}" + "".join(f"{l:>18}" for l in labels))
    for label, key in keys:
        out.append(f"{label:<{width}}" + "".join(f"{r['data'][key]:>18}" for r in rows))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("traces", nargs="*", help="trace JSON files (label defaults to the file stem)")
    ap.add_argument("--label", action="append", default=[], help="label=PATH (repeatable, overrides positional)")
    ap.add_argument("--json", action="store_true", help="print the full analysis as JSON")
    args = ap.parse_args()

    pairs: list[tuple[str, Path]] = []
    for spec in args.label:
        if "=" not in spec:
            raise SystemExit(f"--label needs label=PATH, got {spec!r}")
        name, path = spec.split("=", 1)
        pairs.append((name, Path(path)))
    for p in args.traces:
        pairs.append((Path(p).stem.replace("-trace", ""), Path(p)))
    if not pairs:
        raise SystemExit("no traces given")

    rows = []
    for label, path in pairs:
        if not path.is_file():
            raise SystemExit(f"{path}: no such trace")
        rows.append({"label": label, "data": analyse(path)})

    if args.json:
        print(json.dumps({"rows": rows}, indent=1))
    else:
        print(fmt_table(rows))
        for r in rows:
            print(f"\n--- {r['label']}: longest 10 main-thread tasks (ms) ---")
            for t in r["data"]["longestTasks"]:
                print(f"  {t['ms']:9.2f}  {t['name']}")
            print(f"--- {r['label']}: longest 10 Layout events (ms) ---")
            for t in r["data"]["longestLayouts"]:
                bd = t["beginData"] or {}
                print(
                    f"  {t['ms']:9.2f}  dirtyObjects={bd.get('dirtyObjects')} totalObjects={bd.get('totalObjects')}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
