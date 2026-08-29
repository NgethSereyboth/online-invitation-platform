# V28.0 Implementation Status

## Implemented

- Project-scoped persistent conversations and session-only offline mode.
- Streaming NDJSON assistant and job events.
- User, assistant, question, plan, progress, preview, result, error, and cancellation messages.
- Stable `@page`, `@layer`, and `@asset` context references.
- Plan preview with affected pages/objects, risks, warnings, Apply, Apply step, and Cancel.
- One-click Undo AI job for document transactions.
- Provider-neutral server adapter with deterministic fake provider.
- Strict registered-tool schemas and forbidden direct-execution fields.
- Bounded authorized context, optimistic revision/fingerprint checks, permissions, confirmations, cancellation, idempotency, retention, usage, and audit records.
- Lazy-loaded accessible desktop/mobile agent interface.
- V29–V32 architecture and implementation prompts without implementing those future stages.

## Validation status

The user explicitly delegated final testing to Codex. Full deterministic, browser, native Windows/Linux, external-provider, physical-GPU, and fresh-extraction release certification were not run during this implementation pass. No V28 release-pass marker is claimed.
