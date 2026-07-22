# Platform Maturity Phase — 2026-07-21

This phase extends the invitation builder beyond the visual editor into a more complete invitation-platform workflow.

## Template ecosystem

- Added persistent template metadata, favorites, descriptions, tags, thumbnails and current-version tracking.
- Added immutable template version history and restore-as-new-current-version behavior.
- Added a dedicated Template Studio.
- Added reusable account-level page templates, content blocks and element groups.
- Added a shared template marketplace with owner-controlled publish/remove behavior.
- Added richer live template thumbnails and preview mode in the dashboard.

## Invitation privacy and publishing

- Added editable public slugs.
- Added password-protected invitations.
- Added hashed 24-hour invitation access tokens.
- Public RSVP and guest-wish write endpoints now enforce password access for protected invitations.
- Added unpublish without deleting publication history.
- Published guest pages now receive dynamic title and description metadata; protected invitations use generic metadata.

## Guest interaction and owner operations

- Added configurable custom RSVP questions.
- Required RSVP questions and select/number answers are validated server-side against the published snapshot.
- Added private guest wishes.
- Added a dedicated Responses & Wishes management screen.
- RSVP status and guest count can be corrected by the invitation owner.
- RSVP records can be deleted and exported with custom answers.
- Guest wishes can be reviewed and deleted.
- Added guest-facing Add to Calendar (.ics) and Share Invitation actions.

## Account and data portability

- Added account settings page.
- Added authenticated password changes while preserving the current session and invalidating other sessions.
- Added full JSON account-data export covering invitations, publications, RSVPs, guests, wishes, template data and material metadata.

## Analytics

- Added persistent view events.
- Added 30-day view history.
- Added RSVP status totals, total attending guest count, guest-list totals and check-in totals.
- Added a dedicated analytics screen from the invitation dashboard.

## Server and deployment maturity

- SQLite now uses WAL mode and a busy timeout.
- Runtime data can be relocated with `EINVITE_DATA_DIR`.
- Bind host and port can be configured with CLI flags or environment variables.
- Added stronger HTTP security headers.
- Added Docker support.
- Added `backup.py` using SQLite's online backup API.
- Added `PRODUCTION_DEPLOYMENT.md`.
- Added a self-contained end-to-end smoke test in `tests/smoke_test.py`.

## Automated verification completed

The smoke test verifies:

1. Account registration.
2. Template creation and publishing to the marketplace.
3. Invitation creation and password protection.
4. Immutable publication.
5. Invitation unlock-token behavior.
6. Required custom RSVP validation.
7. RSVP persistence and owner-side updates.
8. Private guest-wish persistence and deletion.
9. Account-data export.
10. Password change and subsequent login.
11. Unpublish behavior and closure of public write endpoints.

The test completed successfully with `SMOKE_TEST_PASSED`.

## Remaining external integrations

PostgreSQL, object storage, transactional email, payments and AI features remain provider-dependent production integrations. No third-party credentials are embedded in the repository.
