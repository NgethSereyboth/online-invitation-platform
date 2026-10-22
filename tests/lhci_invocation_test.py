"""tests/lhci_invocation_test.py — never call the squatted `lhci` npm package.

FB-10 removed `@lhci/cli` from package.json to clear six advisories. After that,
the unscoped `npx lhci` used by `tools/run-gates.py` and `make perf` resolved to
an unrelated placeholder package (`lhci@4.1.2`, "placeholder anupamas0x1") that
prints ``Hello, this is AnupamAS01!`` and exits 0. Two "all 7 phases green" gate
runs therefore contained a false green LHCI phase that never started Lighthouse
(artifacts/next-work/gates/20261022-*/gates.log).

The one supported invocation is the pinned, scoped package:

    npx --yes @lhci/cli@0.15.1 autorun --config=tools/lighthouserc.js

This test is a static scan: it fails when a *live* invocation (an executable
file under tools/, the Makefile, or .github/) contains a bare `npx lhci`.
Markdown docs, root work orders and the historical transcripts under
tools/evidence/ are excluded on purpose — they record what was run at the time
and rewriting them would falsify the evidence.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# `npx lhci`, `npx -y lhci`, `npx --yes lhci`, but NOT `npx --yes @lhci/cli`.
BARE_CALL = re.compile(r"npx(?:\s+-\S+)*\s+lhci\b")

EXECUTABLE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".sh", ".ps1", ".bash", ".ts"}
# Historical transcripts / generated evidence: quoted commands, never executed.
EXCLUDED_DIRS = {"node_modules", "evidence", ".git", "artifacts"}


def _candidate_files():
    for path in sorted((REPO_ROOT / "tools").rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        if path.suffix in EXECUTABLE_SUFFIXES:
            yield path
    makefile = REPO_ROOT / "Makefile"
    if makefile.is_file():
        yield makefile
    workflows = REPO_ROOT / ".github"
    if workflows.is_dir():
        for path in sorted(workflows.rglob("*")):
            if path.is_file():
                yield path


def test_no_bare_npx_lhci_invocation():
    offenders = []
    for path in _candidate_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if BARE_CALL.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "bare `npx lhci` resolves to a squatted placeholder package that prints a "
        "greeting and exits 0; use `npx --yes @lhci/cli@0.15.1` instead:\n  "
        + "\n  ".join(offenders)
    )


def test_runner_pins_the_cli_and_requires_markers():
    """The runner must keep both halves of the FB-23 fix, not just the pin."""
    runner = (REPO_ROOT / "tools" / "run-gates.py").read_text(encoding="utf-8")
    assert "@lhci/cli@0.15.1" in runner, "tools/run-gates.py lost the pinned @lhci/cli"
    assert "MARKERS" in runner and "required=MARKERS.get(phase" in runner, (
        "tools/run-gates.py no longer fails closed on a missing signature line"
    )
