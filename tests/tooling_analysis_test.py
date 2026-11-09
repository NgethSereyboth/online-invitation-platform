"""Regression tests for the Sprint 2 analysis gate.

The gate is deliberately baseline-diff based: the repository already has
substantial complexity and vulture debt, so a raw threshold check would be red
on day one. These tests prove that an existing baseline passes, a new
above-threshold function fails, an increased complexity fails, and a new
high-confidence vulture finding fails.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "analyze.py"


def _load_tool():
    assert TOOL.exists(), f"missing analysis tool: {TOOL}"
    spec = importlib.util.spec_from_file_location("sprint2_analyze", TOOL)
    assert spec and spec.loader, f"cannot load {TOOL}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _complex_source() -> str:
    branches = "\n".join(f"    if value > {i}: total += {i}" for i in range(12))
    return "def complex_function(value):\n    total = 0\n" + branches + "\n    return total\n"


def test_new_above_threshold_function_is_rejected(tmp_path):
    (tmp_path / "mod.py").write_text(_complex_source(), encoding="utf-8")
    tool = _load_tool()
    current = tool.collect_complexity(tmp_path)
    assert current, "radon did not report the deliberately complex function"

    baseline = {"complexity": {}, "vulture": []}
    violations = tool.compare_complexity(current, baseline)
    assert any("complex_function" in item for item in violations), violations
    assert tool.run_gate(tmp_path, baseline=baseline, skip_vulture=True) == 1


def test_matching_baseline_passes(tmp_path):
    (tmp_path / "mod.py").write_text(_complex_source(), encoding="utf-8")
    tool = _load_tool()
    current = tool.collect_complexity(tmp_path)
    baseline = {"complexity": dict(current), "vulture": []}

    assert tool.compare_complexity(current, baseline) == []
    assert tool.run_gate(tmp_path, baseline=baseline, skip_vulture=True) == 0


def test_increased_complexity_is_rejected(tmp_path):
    (tmp_path / "mod.py").write_text(_complex_source(), encoding="utf-8")
    tool = _load_tool()
    current = tool.collect_complexity(tmp_path)
    key = next(iter(current))
    baseline = {"complexity": {key: current[key] - 1}, "vulture": []}

    violations = tool.compare_complexity(current, baseline)
    assert any("grew" in item for item in violations), violations


def test_new_vulture_finding_is_rejected():
    tool = _load_tool()
    known = "src/python/server.py:18: unused import 'marketplace_summary' (90% confidence)"
    new = "src/python/server.py:19: unused variable 'shadow' (90% confidence)"
    baseline = {"complexity": {}, "vulture": [known, known]}

    assert tool.compare_vulture([known], baseline) == []
    violations = tool.compare_vulture([known, new], baseline)
    assert len(violations) == 1, violations
    assert "shadow" in violations[0]


def test_repository_baseline_matches_current_tree():
    baseline = json.loads((ROOT / "tools" / "analysis_baseline.json").read_text(encoding="utf-8"))
    tool = _load_tool()

    assert tool.run_gate(ROOT / "src" / "python", baseline=baseline) == 0


def test_analysis_gate_is_wired_into_local_and_ci_runners():
    """A passing local target is not enough; both gate runners must call it."""
    runner = (ROOT / "tools" / "run-gates.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )

    assert "'analyze'" in runner, "run-gates.py must expose an analyze phase"
    assert "ANALYSIS_OK" in runner, "run-gates.py must fail closed on the analysis marker"
    assert "make analyze" in workflow, "CI tests.yml must run make analyze"
