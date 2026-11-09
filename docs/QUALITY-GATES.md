# Quality Gates

## Static analysis: `make analyze`

`make analyze` runs `radon` cyclomatic-complexity analysis and `vulture` at
90% confidence against `src/python`, then compares the results with
`tools/analysis_baseline.json`.

The baseline is debt, not a target. On 2026-11-09 it recorded:

| Metric | Baseline |
|---|---:|
| Functions/methods above CC 10 | **209** |
| Vulture findings at >=90% confidence | **1** |

The Sprint 3 refactor reduced the recorded count from 213 to 209 and the
vulture count from 11 to 1 by extracting bounded helpers and removing three
independently unused imports. `server.JITElevationManager` remains because an
existing security test monkey-patches it.

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

The gate runs in both local and CI paths: `tools/run-gates.py --phase analyze`
checks for the fail-closed `ANALYSIS_OK` marker, and the Tests workflow runs
`make analyze` after the build check. A new finding therefore fails the full
local matrix and CI, not only a manually invoked target.

`make coverage` runs the suite with `pytest-cov` and a terminal missing-lines
report; it is a diagnostic target, not a threshold gate.
