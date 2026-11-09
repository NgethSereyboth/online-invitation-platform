#!/usr/bin/env python3
"""Baseline-diff analysis gate for the Python backend.

The repository has a large, known complexity and vulture baseline. Running a
raw threshold check would fail on day one and hide new debt in the noise. This
gate records the known findings in ``tools/analysis_baseline.json`` and fails
only when a new above-threshold function appears, an existing function grows,
or a new high-confidence vulture finding is introduced.

Usage::

    python tools/analyze.py                 # check the current tree
    python tools/analyze.py --write-baseline
    python tools/analyze.py --skip-vulture  # useful in unit tests
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "src" / "python"
DEFAULT_BASELINE = ROOT / "tools" / "analysis_baseline.json"
COMPLEXITY_THRESHOLD = 10
VULTURE_MIN_CONFIDENCE = 90
VULTURE_LINE = re.compile(
    r"^(?P<path>.+?):\d+: (?P<message>.*) \(\d+% confidence\)$"
)


def _relative(path_text: str) -> str:
    """Normalize a tool path to a repo-relative path when possible."""
    path = Path(path_text)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _complexity_key(path: str, block: dict) -> str:
    return "|".join(
        (
            _relative(path),
            str(block.get("type") or ""),
            str(block.get("classname") or ""),
            str(block.get("name") or ""),
        )
    )


def collect_complexity(root: Path) -> dict[str, int]:
    """Return ``{key: complexity}`` for blocks above the threshold."""
    result = subprocess.run(
        [sys.executable, "-m", "radon", "cc", str(root), "-s", "-j"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "radon failed")
    data = json.loads(result.stdout or "{}")
    current: dict[str, int] = {}
    for path, blocks in data.items():
        for block in blocks:
            complexity = int(block.get("complexity") or 0)
            if complexity <= COMPLEXITY_THRESHOLD:
                continue
            key = _complexity_key(path, block)
            current[key] = max(current.get(key, 0), complexity)
    return current


def compare_complexity(
    current: dict[str, int], baseline: dict
) -> list[str]:
    """Return human-readable violations against the recorded baseline."""
    known = baseline.get("complexity", {}) if isinstance(baseline, dict) else {}
    violations: list[str] = []
    for key in sorted(current):
        value = int(current[key])
        previous = known.get(key)
        if previous is None:
            violations.append(
                f"{key}: new complexity {value} exceeds {COMPLEXITY_THRESHOLD}"
            )
        elif value > int(previous):
            violations.append(f"{key}: complexity grew from {previous} to {value}")
    return violations


def _normalize_vulture_line(line: str) -> str:
    match = VULTURE_LINE.match(line.strip())
    if not match:
        return line.strip()
    return f"{_relative(match.group('path'))}: {match.group('message')}"


def collect_vulture(root: Path) -> list[str]:
    """Return normalized high-confidence vulture findings."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vulture",
            str(root),
            "--min-confidence",
            str(VULTURE_MIN_CONFIDENCE),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    # vulture exits 3 when it finds anything; that is the expected state.
    if result.returncode not in (0, 3):
        raise RuntimeError(result.stderr.strip() or "vulture failed")
    return [
        _normalize_vulture_line(line)
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def compare_vulture(current: list[str], baseline: dict) -> list[str]:
    """Return new high-confidence findings not present in the baseline."""
    known = baseline.get("vulture", []) if isinstance(baseline, dict) else []
    known_set = {_normalize_vulture_line(line) for line in known}
    current_set = {_normalize_vulture_line(line) for line in current}
    return sorted(current_set - known_set)


def run_gate(
    root: Path,
    baseline: dict,
    *,
    skip_vulture: bool = False,
) -> int:
    """Run the gate and print a compact summary; return a process exit code."""
    current_complexity = collect_complexity(root)
    complexity_violations = compare_complexity(current_complexity, baseline)
    known_complexity = len(baseline.get("complexity", {}))
    print(
        f"Complexity: {len(current_complexity)} above CC {COMPLEXITY_THRESHOLD} "
        f"(baseline {known_complexity})"
    )

    vulture_violations: list[str] = []
    if not skip_vulture:
        current_vulture = collect_vulture(root)
        vulture_violations = compare_vulture(current_vulture, baseline)
        print(
            f"Vulture: {len(current_vulture)} findings at "
            f">={VULTURE_MIN_CONFIDENCE}% confidence"
        )

    violations = complexity_violations + vulture_violations
    for item in violations:
        print(f"NEW: {item}")
    if violations:
        print(f"ANALYSIS_FAILED: {len(violations)} new finding(s)")
        return 1
    print("ANALYSIS_OK")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help=f"Python source root (default: {DEFAULT_ROOT})",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help=f"baseline JSON (default: {DEFAULT_BASELINE})",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="record the current findings instead of checking",
    )
    parser.add_argument(
        "--skip-vulture",
        action="store_true",
        help="run only the complexity comparison (used by unit tests)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.write_baseline:
            current_complexity = collect_complexity(args.root)
            current_vulture = (
                [] if args.skip_vulture else collect_vulture(args.root)
            )
            payload = {
                "complexity_threshold": COMPLEXITY_THRESHOLD,
                "vulture_min_confidence": VULTURE_MIN_CONFIDENCE,
                "complexity": current_complexity,
                "vulture": current_vulture,
            }
            args.baseline.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(
                f"Wrote {len(current_complexity)} complexity and "
                f"{len(current_vulture)} vulture baseline entries to {args.baseline}"
            )
            return 0

        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        return run_gate(args.root, baseline, skip_vulture=args.skip_vulture)
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ANALYSIS_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
