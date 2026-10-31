#!/usr/bin/env python3
"""Turn a ``tools/ui-audit.py`` run directory into an agent-readable report set.

    .venv/bin/python tools/ui-audit-report.py --dir artifacts/ui-audit-2026-10-29/pass2

Writes, inside the run directory:
    REPORT.md   findings grouped by page and severity, with selectors + repro + shots
    INDEX.md    coverage matrix (page x variant) and every state/surface shot
    INDEX.html  browsable contact sheet (lazy images, no JS dependency)
    findings.csv  flat table for filtering/sorting
"""
from __future__ import annotations

import argparse
import csv
import html
import json
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
KIND_BLURB = {
    "clickable-but-invisible": "Interactive element paints nothing (opacity 0 / clipped away) but still takes pointer events.",
    "control-occluded": "Another element sits over the control, so the click lands somewhere else.",
    "control-clipped-by-ancestor": "A non-scrollable ancestor cuts the control off; part of it cannot be reached.",
    "interactive-outside-document": "Keyboard-focusable control whose box falls outside the document (off-canvas/over-clipped, not below-the-fold).",
    "tiny-target": "Target smaller than 24x24 CSS px (WCAG 2.2 AA 2.5.8).",
    "control-without-name": "No accessible name (label, aria-label, text, alt or title).",
    "nested-interactive": "Focusable control inside another focusable control.",
    "low-contrast": "Text contrast below 4.5:1 (3:1 for large text).",
    "text-clipped": "Text is cut by an overflow:hidden box with no ellipsis or line-clamp.",
    "aria-hidden-but-visible": "Visible text inside aria-hidden, so assistive tech loses it.",
    "focusable-inside-aria-hidden": "Focusable controls inside aria-hidden (tab reaches invisible controls).",
    "pointer-cursor-not-semantic": "Cursor:pointer but no role/tabindex, so it is mouse-only.",
    "overlapping-controls": "Two visible controls overlap by more than half of the smaller one.",
    "khmer-line-height": "Khmer text below the project's 1.6 line-height rule.",
    "duplicate-field-label": "The same question/label appears twice in one form.",
    "mixed-language-option": "An option label concatenates English and Khmer with no separator.",
}
KNOWN_NOISE = [
    ("pointer-cursor-not-semantic", "Advisory. Many app surfaces are custom click targets; treat as a keyboard-reachability backlog, not a regression."),
    ("overlapping-controls", "Pairwise geometry only; intentional icon-on-badge stacks can appear. Check the screenshot before filing."),
    ("aria-hidden-but-visible", "Decorative marketing panels can be deliberately hidden from AT. File only when the hidden text carries meaning or controls."),
    ("tiny-target", "Inline text links are already excluded, but 18-22 px icon buttons inside dense toolbars may be an accepted visual choice."),
    ("clickable-but-invisible", "Rows with `hover_revealed: true` appear on card hover; they remain a real touch/keyboard problem, not necessarily a desktop one."),
    ("control-clipped-by-ancestor", "Scrollable panes are filtered out, but JS-driven panes can still show content below the fold; confirm the control is unreachable."),
]


def load(path: Path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def rel(target: Path, base: Path) -> str:
    p = Path(target)
    if not p.is_absolute():
        p = p.resolve()
    try:
        return p.relative_to(base.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def decorative(f: dict) -> bool:
    """Pack-thumbnail names are hidden from AT on purpose; keep them out of triage."""
    return (f.get("page") == "templates" and f.get("kind") == "aria-hidden-but-visible"
            and "pack-name" in f.get("selector", ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="artifacts/ui-audit-2026-10-29/pass2")
    args = ap.parse_args()
    root = Path(args.dir).resolve()

    manifest = load(root / "manifest.json", {})
    findings = load(root / "findings.json", [])
    states = load(root / "states.json", {"states": [], "discovery": []})
    console = load(root / "console.json", [])
    focus = load(root / "focus.json", [])

    pages = manifest.get("pages", [])
    raw_count = len(findings)
    noise = [f for f in findings if decorative(f)]
    findings = [f for f in findings if not decorative(f)]
    by_page = defaultdict(list)
    for f in findings:
        by_page[f["page"]].append(f)

    sev = Counter(f["severity"] for f in findings)
    kinds = Counter(f["kind"] for f in findings)

    # ---------------------------------------------------------------- REPORT.md
    out: list[str] = []
    out.append("# UI audit corpus — every page, variant and reachable function\n")
    out.append(f"Generated **{manifest.get('generated', '?')}** from `{manifest.get('base', '?')}`.\n")
    out.append(
        "This folder is the hand-off for a fix pass. It contains full-page and viewport screenshots for "
        "16 routes × 4 viewer variants, screenshots of every function/surface that could be opened, a "
        "machine-readable finding list, and the console/network evidence behind each page.\n"
    )
    out.append("## What is here\n")
    out.append("| File | Use |\n|---|---|\n"
               "| `screens/<variant>/<page>.png` | full page; `<page>--viewport.png` is the 1440×900 / 390×844 first screen |\n"
               "| `states/<variant>/<page>--<state>.png` | one screenshot per opened function (dialog, menu, panel, tab, error state) |\n"
               "| `findings.json` | every probe result with selector, rect, why, screenshot |\n"
               "| `findings.csv` | the same rows, flat, for filtering |\n"
               "| `states.json` | every function attempted, with status and post-click state |\n"
               "| `console.json` | console errors, page errors and non-2xx requests per capture |\n"
               "| `focus.json` | 24-step Tab walk per page: visible box + visible focus ring |\n"
               "| `manifest.json` | run metadata and counts |\n")
    out.append("## Counts\n")
    out.append(f"- Captures: **{manifest.get('counts', {}).get('captures', '?')}** page/variant pairs\n"
               f"- Function screenshots: **{manifest.get('counts', {}).get('states', 0)}** explicit + "
               f"**{manifest.get('counts', {}).get('discoveries', 0)}** discovered surfaces\n"
               f"- Findings: **{len(findings)}** — " + ", ".join(f"{k} {v}" for k, v in sev.most_common()) + "\n"
               + (f"- Excluded as decorative (not actionable): **{len(noise)}**\n" if noise else ""))
    out.append("| Kind | Count | Meaning |\n|---|---|---|\n")
    for kind, count in kinds.most_common():
        out.append(f"| `{kind}` | {count} | {KIND_BLURB.get(kind, '')} |\n")

    out.append("\n## Triage first (highest-value, distinct signals)\n")
    shown = 0
    seen_kind = Counter()
    for f in sorted(findings, key=lambda x: (SEVERITY_ORDER.get(x["severity"], 9), x["page"], x["kind"])):
        if f["severity"] != "high" or f["kind"] in ("pointer-cursor-not-semantic", "focusable-inside-aria-hidden"):
            continue
        if seen_kind[f["kind"]] >= 3:
            continue
        seen_kind[f["kind"]] += 1
        shot = rel(Path(f["screenshot"]), root) if f.get("screenshot") else ""
        out.append(f"- **{f['page']} / {f['variant']} / {f['kind']}** — {f.get('label') or f.get('why')}  \n"
                   f"  `{f.get('selector', '')}` · {f.get('why', '')}" + (f" · [shot]({shot})" if shot else "") + "\n")
        shown += 1
        if shown >= 18:
            break

    out.append("\n## Findings by page\n")
    for page in pages:
        name = page["name"]
        rows = by_page.get(name, [])
        shots = sorted((root / "screens").glob(f"*/{name}.png"))
        out.append(f"\n### {name} — {page.get('title', '')}\n")
        if shots:
            out.append("Screens: " + " · ".join(f"[{p.parent.name}]({rel(p, root)})" for p in shots) + "\n")
        if not rows:
            out.append("\nNo structural findings on the base screen. Check the state shots below for opened surfaces.\n")
        else:
            counts = Counter(f["kind"] for f in rows)
            out.append("\n" + ", ".join(f"`{k}` ×{v}" for k, v in counts.most_common()) + "\n")
            grouped = defaultdict(list)
            for f in rows:
                grouped[(f["variant"], f["severity"], f["kind"])].append(f)
            for key in sorted(grouped, key=lambda k: (SEVERITY_ORDER.get(k[1], 9), k[0], k[2])):
                variant, severity, kind = key
                items = grouped[key]
                out.append(f"\n**{severity} · {variant} · {kind}** ({len(items)})\n")
                for f in items[:8]:
                    label = (f.get("label") or "").replace("|", "\\|")[:70]
                    out.append(f"- `{f.get('selector', '')}` — {label} · {f.get('why', '')} · "
                               f"rect {f.get('rect', {})}\n")
                if len(items) > 8:
                    out.append(f"- … {len(items) - 8} more in `findings.json`\n")
        page_states = [s for s in states.get("states", []) if s["page"] == name]
        page_disc = [d for d in states.get("discovery", []) if d["page"] == name]
        if page_states or page_disc:
            out.append("\nOpened functions: " + ", ".join(
                f"`{s['state']}`" + ("" if s["status"] == "ok" else f" ({s['status']})") for s in page_states
            ) + ("; discovered: " + ", ".join(f"`{d['trigger']['label'][:40]}`" for d in page_disc) if page_disc else "") + "\n")

    out.append("\n## Console and network\n")
    noisy = [c for c in console if any(not e.get("expected_static") for e in c.get("events", []))]
    if not noisy:
        out.append("No unexpected console/page errors or non-2xx responses were recorded.\n")
    else:
        out.append("| Page | Variant | Signal |\n|---|---|---|\n")
        for entry in noisy[:60]:
            sig = "; ".join(f"{e['type']}: {e['text'][:90]}" for e in entry.get("events", [])[:3])
            out.append(f"| {entry['page']} | {entry['variant']} | {sig.replace('|', '/')} |\n")

    out.append("\n## Keyboard focus walk\n")
    if focus:
        out.append("| Page | Steps | No visible ring | Focus off-screen |\n|---|---|---|---|\n")
        for row in focus:
            out.append(f"| {row['page']} | {len(row['steps'])} | {row['no_ring']} | {row['off_screen']} |\n")
        out.append("\n`no_ring` counts steps whose computed outline and box-shadow were both absent. "
                   "CSS that paints focus with a background change is not detected and should be checked in the screenshot `screens/focus/<page>--focus.png`.\n")
    else:
        out.append("Not run in this pass.\n")

    manual = root / "MANUAL-NOTES.md"
    if manual.exists():
        out.append("\n## Manual visual review (curated from the screenshots)\n\n")
        out.append(manual.read_text(encoding="utf-8"))

    out.append("\n## Known noise (do not file these without checking)\n")
    for kind, why in KNOWN_NOISE:
        out.append(f"- **{kind}** — {why}\n")

    out.append("\n## Reproduce\n```\n"
               "python3 tools/serve-gzip.py --port 4176 &\n"
               ".venv/bin/python tools/ui-audit.py --out artifacts/ui-audit-2026-10-29/pass2 \\\n"
               "  --mode all --variants desktop,mobile,km,dark \\\n"
               "  --login-email demo@einvite.test --login-password '<demo password>' \\\n"
               "  --invitation <invitation-id>\n"
               ".venv/bin/python tools/ui-audit-report.py --dir artifacts/ui-audit-2026-10-29/pass2\n```\n"
               "The demo password lives only in `FREEBUFF-ANSWERS-2026-10-28.md` (`## Demo credentials`).\n")
    (root / "REPORT.md").write_text("".join(out), encoding="utf-8")

    # ---------------------------------------------------------------- findings.csv
    with open(root / "findings.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["page", "variant", "state", "severity", "kind", "selector", "label", "why", "rect", "screenshot", "url"])
        for f in findings:
            writer.writerow([f.get(k, "") for k in ("page", "variant", "state", "severity", "kind", "selector", "label", "why")] +
                            [json.dumps(f.get("rect", {})), rel(Path(f.get("screenshot", "")), root) if f.get("screenshot") else "", f.get("url", "")])

    # ---------------------------------------------------------------- INDEX.md
    idx: list[str] = ["# Screenshot index\n",
                      "Each cell links to the full-page capture. `--viewport` variants live beside each file.\n"]
    variants = [v["name"] for v in manifest.get("variants", [])]
    idx.append("| Page | " + " | ".join(variants) + " | Functions |\n")
    idx.append("|---|" + "---|" * len(variants) + "---|\n")
    for page in pages:
        name = page["name"]
        cells = []
        for v in variants:
            p = root / "screens" / v / f"{name}.png"
            cells.append(f"[{'✓' if p.exists() else '—'}]({rel(p, root)})" if p.exists() else "—")
        fn = [s["state"] for s in states.get("states", []) if s["page"] == name]
        idx.append(f"| {name} | " + " | ".join(cells) + f" | {len(fn)} |\n")
    idx.append("\n## Function / surface shots\n")
    for page in pages:
        name = page["name"]
        rows = [s for s in states.get("states", []) if s["page"] == name]
        disc = [d for d in states.get("discovery", []) if d["page"] == name]
        if not rows and not disc:
            continue
        idx.append(f"\n### {name}\n")
        for s in rows:
            p = Path(s.get("screenshot", ""))
            idx.append(f"- `{s['state']}` {'' if s['status'] == 'ok' else '**' + s['status'] + '** '}"
                       + (f"[shot]({rel(p, root)})" if p.exists() else "") + "\n")
        for d in disc:
            p = Path(d.get("screenshot", ""))
            idx.append(f"- discovered `{d['trigger']['label'][:50]}` {'' if d['status'] == 'ok' else '**' + d['status'] + '** '}"
                       + (f"[shot]({rel(p, root)})" if p.exists() else "") + "\n")
    (root / "INDEX.md").write_text("".join(idx), encoding="utf-8")

    # ---------------------------------------------------------------- INDEX.html
    parts = ["<!doctype html><meta charset='utf-8'><title>UI audit contact sheet</title>",
             "<style>body{font:14px/1.5 system-ui,sans-serif;margin:24px;background:#f6f6f8;color:#1c1c22}"
             "h1{margin:0 0 4px}h2{margin:32px 0 8px;border-bottom:2px solid #d8d8e0;padding-bottom:6px}"
             "h3{margin:18px 0 6px;font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#666}"
             ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}"
             "figure{margin:0;background:#fff;border:1px solid #ddd;border-radius:10px;overflow:hidden}"
             "figure img{display:block;width:100%;height:190px;object-fit:cover;object-position:top;background:#eee}"
             "figcaption{padding:6px 8px;font-size:12px}"
             "a{color:#7a2540;text-decoration:none}a:hover{text-decoration:underline}"
             ".meta{color:#666;font-size:12px}</style>"]
    parts.append(f"<h1>UI audit — contact sheet</h1><p class='meta'>{html.escape(manifest.get('generated',''))} · "
                 f"{manifest.get('counts',{}).get('captures','?')} captures · "
                 f"{manifest.get('counts',{}).get('findings','?')} findings</p>")
    for page in pages:
        name = page["name"]
        parts.append(f"<h2 id='{name}'>{html.escape(name)} <span class='meta'>{html.escape(page.get('title',''))}</span></h2>")
        parts.append("<h3>base screens</h3><div class='grid'>")
        for v in variants:
            p = root / "screens" / v / f"{name}.png"
            if p.exists():
                parts.append(f"<figure><a href='{rel(p, root)}'><img loading='lazy' src='{rel(p, root)}'></a>"
                             f"<figcaption>{v} · full page</figcaption></figure>")
        parts.append("</div>")
        rows = [s for s in states.get("states", []) if s["page"] == name and s["status"] == "ok"]
        disc = [d for d in states.get("discovery", []) if d["page"] == name and d["status"] == "ok"]
        shots = [(s["state"], s.get("screenshot", "")) for s in rows] + [(d["trigger"]["label"][:40], d.get("screenshot", "")) for d in disc]
        if shots:
            parts.append("<h3>opened surfaces</h3><div class='grid'>")
            for label, shot in shots:
                p = Path(shot) if shot else None
                if p and p.exists():
                    parts.append(f"<figure><a href='{rel(p, root)}'><img loading='lazy' src='{rel(p, root)}'></a>"
                                 f"<figcaption>{html.escape(label)}</figcaption></figure>")
            parts.append("</div>")
    (root / "INDEX.html").write_text("".join(parts), encoding="utf-8")

    print(f"wrote {root}/REPORT.md ({len(findings)} findings), INDEX.md, INDEX.html, findings.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
