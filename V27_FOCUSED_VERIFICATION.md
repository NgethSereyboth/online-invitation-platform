# V27.3.3 Focused Verification

The following checks passed on the cumulative V27 working tree:

```text
V27_STUDIO_AUTOMATION_CONTRACT_TEST_PASSED
V27_STUDIO_AUTOMATION_MIGRATION_TEST_PASSED
V27_STUDIO_AUTOMATION_BACKEND_TEST_PASSED
V27_STUDIO_BACKUP_SCHEDULER_TEST_PASSED
V27_STUDIO_AUTOMATION_BROWSER_TEST_PASSED
V27_STUDIO_AUTOMATION_MOBILE_TEST_PASSED
V27_STUDIO_AUTOMATION_PERFORMANCE_TEST_PASSED
```

The V27 backend test verifies:

- Compatible and incompatible bulk release remediation
- Bounded bulk-job history
- Backup-policy persistence
- Manual archive creation
- Retention pruning
- Private backup download
- Archive contents
- Hash-chained studio audit retrieval

The scheduler test verifies a due policy produces a scheduled archive, advances `last_run_at` and `next_run_at`, writes the ZIP, and appends a `studio.backup_completed` audit event.

Cumulative build, security, collaboration, and V26/V25/V24/V23 load-bearing checks also passed individually. The accumulated all-generation monolithic test runner was not used as the sole acceptance claim.

Latest focused performance sample: 173.2 ms for the 500-invitation, 200-audit-event, 50-backup projection.
