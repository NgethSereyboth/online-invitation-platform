# V28.0 Test Matrix — Codex Execution Required

This implementation pass intentionally did not run the full project test suites at the user's request. The following matrix defines the required final acceptance work.

| Area | Required evidence | Current status |
|---|---|---|
| Typed tool schemas | known/unknown tools, forbidden fields/values, bounded arguments | Test source provided; not run |
| Conversation persistence | create/list/read/archive, reload/resume, retention purge | Test source provided; not run |
| Provider adapters | fake provider, malformed response, timeout, rate limit, secrets | Test source provided; not run |
| Permissions/context | owner/collaborator roles, unauthorized IDs, redaction, prompt injection | Test source provided; not run |
| Transactions | exact before/after, atomic batch rollback, one-step Undo/Redo | V27 foundation + V28 registry test source; not run |
| Rich text | links, marks, locale, Khmer, list semantics | V28 registry/focused scenario required; not run |
| Revision safety | stale revision, selection change, missing targets/assets | Server/client contracts implemented; not run |
| Layout preview | diagnostics at 320/360/390/430/820/1024/1180/1440 | Shared preview pipeline used; not run |
| Confirmation | publish/delete/message/background/export boundaries | Implemented; not run |
| Cancellation | streaming and execution cancellation | Implemented; not run |
| Mobile accessibility | dialog role, modal, focus trap, Escape, inert, targets, overflow | Browser test source provided; not run |
| Route performance | lazy assets excluded; route ≤1,420,000 bytes | Build sanity measured 1,403,447 bytes; full test not run |
| CSP/security | strict same-origin loading and no direct execution authority | Implemented; full security suite not run |
| Inherited product | full V27.3.5 deterministic/browser gate | Delegated to Codex |
| Native platforms | Windows/Linux full release runs | Delegated to Codex |
| External provider | real configured provider integration | Credentials absent; delegated |
| Fresh ZIP | manifest, safe extraction, regeneration, complete gate | Delegated to Codex |
