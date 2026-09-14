# V0.52 Changelog — Independent Audit Repair

## Product fixes

- Corrected AI review-context SQL from nonexistent comment `status` to canonical `resolved=0`.
- Added sanitized pre-stream and mid-stream AI failure boundaries without leaking SQL, paths, secrets or tracebacks.
- Made AI job/reservation completion exactly-once across success, question, cancellation, disconnect and error paths.
- Fixed redesigned dashboard project-cover recursion; covers now route via the explicit card Edit action.
- Fixed false autosave-offline state caused by shadowing the browser `document` object with an invitation snapshot.
- Preserved newest pending autosave state, added cancellable idle coalescing and bounded transient retry/backoff, and separated revision/auth/validation failures.
- Added sanitized autosave diagnostics for regression tests/support.

## Release/test fixes

- Deterministically close SQLite/server resources in the V0.52 asset-identity test on Windows.
- Accept the exact current V0.52 dependency-preflight marker while preserving dependency/WOFF2 checks.
- Update UI smoke coverage to the current visible Create action plus project-cover/action-menu navigation.
- Preserve optimistic revision `0` with nullish (`??`) semantics.
- Replace redundant generated route source comments with manifest + SHA-256 source/bundle integrity checks, recovering route headroom without raising budgets.
- Register real HTTP AI, real-browser AI, dashboard-cover and autosave regressions in the cumulative release runner; contention-sensitive provider/realtime tests run serially.

## Compatibility

Public version remains `0.52`, internal milestone remains `52`, schema remains `27`, compatibility floor remains `V27.3.5`, and README is unchanged.
