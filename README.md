# V27.3.3 Studio Automation

This cumulative release adds compatible bulk release remediation, scheduled and manual private studio backups, retention pruning, downloadable recovery archives, and a hash-verified private studio audit timeline. See `V27_3_3_COMPLETION_REPORT.md`, `V27_ARCHITECTURE.md`, and `V27_FOCUSED_VERIFICATION.md`.

# V26.3.3 Studio Operations

This cumulative release adds controlled studio resource releases, invitation release pins, rollout adoption reporting, optional server-authoritative release publishing policy, deployment health and backup access, and native Windows readiness checks. See `V26_3_3_COMPLETION_REPORT.md`.

# E-Invitation Platform — V24.6.3 Canva-Quality Invitation Workflow

This cumulative release continues from V24.0 and completes the planned V24.1–V24.6 workflow: direct manipulation and inline editing, unified content discovery, smart layout, event brand kits and reusable components, collaboration maturity, and production export/accessibility. It preserves the invitation-first Khmer, publishing, RSVP, guest, privacy, security, review, and self-hosted workflows. See `V24_6_3_COMPLETION_REPORT.md` and `V24_ARCHITECTURE.md`.

## New in V23.8.3

- Private Activity tab for comment, reply, resolve/reopen, approval, decision, and policy events.
- Unread activity badge, item-level read state, and Mark all read.
- Bounded notification retention: 500 per invitation and recipient; newest 100 returned to the editor.
- Reviewer suggestions from the invitation owner and current collaborators.
- Assigned-reviewer and manager decision permissions.
- Independent distinct-reviewer counting for publishing readiness.
- Self-approval excluded from approval-gate counts.
- Optional requirement for one to five current approvals.
- Optional requirement to resolve all open root comments before publishing.
- Server-authoritative HTTP 409 `review_gate_blocked` response with structured blocker details.
- Earlier approvals automatically stop counting when a later saved revision changes the fingerprint.
- No local published snapshot or history entry is written before the server accepts publication.
- Account and invitation lifecycle cleanup for notification and policy data.
- SQLite and PostgreSQL additive migration support.
- Review data remains private and excluded from public invitation payloads.

## Review commands

- `review.open` — Open the review drawer (`Ctrl/Cmd + Alt + Shift + M`)
- `review.openActivity` — Open private review activity
- `review.addComment` — Focus the new-comment workflow
- `review.requestApproval` — Open the approval request panel
- `review.configurePolicy` — Open manager publishing-policy controls
- `review.togglePins` — Show or hide review pins

No additional global keyboard listener is introduced.

## Focused verification

```bash
python tests/v23_8_review_operations_contract_test.py
python tests/v23_8_review_operations_backend_test.py
python tests/v23_8_review_operations_browser_test.py
python tests/v23_8_review_operations_mobile_test.py
python tests/v23_8_review_operations_performance_test.py
```

Run the complete integrated release gate with:

```bash
python release_check.py
```

Run three consecutive native gates with:

```text
RUN_V23_8_GATE_3X.bat
RUN_V23_8_GATE_3X.sh
```

Native Windows/Linux three-run certification, physical-GPU benchmarking, and external email/SMS/push delivery remain separate pending activities.
