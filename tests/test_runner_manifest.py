"""FB-08 — the zero-test runner manifest is complete and gates are wired.

261 of the repo's test-pattern files contain no ``def test_``; 226 of them run
zero tests under pytest, silently, and two of them (v55/v14) are real budget
gates pytest never executes. This test makes the inventory explicit:

  * every zero-``def test_`` file must appear in ``tests/runner-manifest.json``
    (or be in ``COLLECT_IGNORE`` in ``tests/conftest.py``);
  * every manifest entry must exist on disk;
  * every entry marked kind ``gate`` must be wired into ``tools/run-gates.py``
    (by filename) with the disposition the 2026-10-22 owner answer requires
    (v55 blocking via the budgets phase; v14 aspirational/non-blocking);
  * a new zero-test file without a manifest entry fails here with the file
    named.

This does NOT convert runners to pytest tests; it classifies them (see the
work-order FB-08 scope)."""
from __future__ import annotations
import json, re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
MANIFEST = TESTS / "runner-manifest.json"


def zero_test_files() -> list[str]:
    files = set()
    for pattern in ("*_test.py", "test_*.py"):
        for p in TESTS.glob(pattern):
            if not re.search(r"def test_", p.read_text(encoding="utf-8", errors="replace")):
                files.add(p.name)
    return sorted(files)


def collect_ignore() -> set[str]:
    """Parse the COLLECT_IGNORE list out of tests/conftest.py so the test
    tracks the real list instead of a copy."""
    text = (TESTS / "conftest.py").read_text(encoding="utf-8")
    match = re.search(r"COLLECT_IGNORE\s*=\s*\[(.*?)\]", text, re.S)
    assert match, "COLLECT_IGNORE not found in tests/conftest.py"
    return set(re.findall(r'"([^"]+)"|\'([^\']+)\'', match.group(1)) and
               {a or b for a, b in re.findall(r'"([^"]*)"|\'([^\']*)\'', match.group(1))} - {""})


def test_runner_manifest_complete():
    assert MANIFEST.exists(), "tests/runner-manifest.json missing — FB-08 inventory was deleted"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = manifest["files"]
    zero = zero_test_files()
    ignore = collect_ignore()

    unlisted = [f for f in zero if f not in entries and f not in ignore]
    assert not unlisted, (
        "new zero-test file(s) without a manifest or COLLECT_IGNORE entry "
        "(FB-08): " + ", ".join(unlisted)
    )

    missing_on_disk = [f for f in entries if not (TESTS / f).is_file()]
    assert not missing_on_disk, (
        "manifest lists files that no longer exist (stale FB-08 inventory): "
        + ", ".join(missing_on_disk)
    )

    run_gates = (ROOT / "tools" / "run-gates.py").read_text(encoding="utf-8")

    v55 = entries.get("v55_route_weight_budget_test.py")
    assert v55 and v55.get("kind") == "gate", "v55 must be classified as a gate"
    assert "budgets" in run_gates and "v55_route_weight_budget_test.py" in run_gates, (
        "tools/run-gates.py must run the v55 gate via a budgets phase (FB-08 item 3)"
    )

    v14 = entries.get("v14_performance_budget_test.py")
    assert v14 and v14.get("kind") == "gate", "v14 must be classified as a gate"
    assert v14.get("invocation", "").find("NON-BLOCKING") != -1, (
        "v14's manifest entry must state the non-blocking disposition "
        "(owner answer 2026-10-22, OD-6 / FB-11)"
    )
    ci = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "v14_performance_budget_test.py" in ci, "CI tests.yml must run v14"
    v14_step = ci.find("name: v14 performance budget")
    assert v14_step != -1, "v14's CI step must be labeled with its disposition"
    # The step block between the v14 step's name and the next step name must
    # carry continue-on-error: true — that is the quarantine itself.
    next_step = ci.find("name: Upload logs", v14_step)
    v14_block = ci[v14_step:next_step]
    assert "continue-on-error: true" in v14_block and "NON-BLOCKING" in v14_block, (
        "CI must keep v14 quarantined: its own step carries "
        "continue-on-error: true and the NON-BLOCKING label (FB-11)"
    )


def test_manifest_entry_structure():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, entry in manifest["files"].items():
        assert entry.get("kind") in {
            "manual-runner", "module-script", "gate",
        }, f"{name}: unknown kind {entry.get('kind')!r}"
        assert entry.get("invocation"), f"{name}: missing invocation command"
