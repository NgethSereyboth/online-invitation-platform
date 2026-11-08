# Quality Gates

## Static analysis: `make analyze`

`make analyze` runs `radon` cyclomatic-complexity analysis and `vulture` at
90% confidence against `src/python`, then compares the results with
`tools/analysis_baseline.json`.

The baseline is debt, not a target. On 2026-11-08 it recorded:

| Metric | Baseline |
|---|---:|
| Functions/methods above CC 10 | **213** |
| Vulture findings at >=90% confidence | **11** |

The gate fails when:

- a new function/method above CC 10 appears;
- an existing above-threshold function's complexity increases;
- a new high-confidence vulture finding appears.

Resolved findings do not fail the gate. To remove debt, delete the
corresponding baseline entry and rerun `make analyze`; to record a deliberate
new baseline, run `python tools/analyze.py --write-baseline` and review the
diff. Do not regenerate the baseline merely to make a new finding disappear.

The gate is covered by `tests/tooling_analysis_test.py`, including a temporary
new-function failure, a matching-baseline pass, an increased-complexity
failure, and a new-vulture-finding failure.

`make coverage` runs the suite with `pytest-cov` and a terminal missing-lines
report; it is a diagnostic target, not a threshold gate.
