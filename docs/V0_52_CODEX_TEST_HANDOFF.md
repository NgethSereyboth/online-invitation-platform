# V0.52 Independent Testing Handoff

Use the final cumulative V0.52 repair ZIP as the only test baseline.

## Priority validation

1. Verify the ZIP sidecar SHA-256 and internal `V0_52_RELEASE_FILE_HASHES.sha256` manifest.
2. Run `python run_review_checks.py --continue-on-failure` from a fresh extraction with no skips.
3. Run the normal non-continue gate afterward.
4. Verify the new real-server regressions: `v0_52_ai_real_server_test.py`, `v0_52_ai_live_browser_test.py`, `v0_52_dashboard_cover_navigation_test.py`, and `v0_52_autosave_status_test.py`.
5. Confirm editor startup remains at or below 1,420,000 bytes and public remains at or below 260,000 bytes.
6. Recheck canonical asset-ID migration and wrong-invitation/wrong-workspace/missing-asset publication blockers.
7. Recheck AI panel initialization, stacking, Escape/close/focus restoration and actual server conversation streaming.
8. Recheck two rapid server-backed edits remain persisted and the header truthfully stays `Server connected` after the acknowledged save.
9. Recheck dashboard project-cover navigation and Project actions → Edit.
10. Recheck strict CSP/Trusted Types, permissions, provider-secret boundaries, plugin manifests, schema-27 idempotency, Khmer/public rendering and RSVP modes.

## Expected release identity

- Product version: `0.52`
- Internal milestone: `52`
- Schema: `27`
- Compatibility floor: `V27.3.5`
- Certification: pending until the independent unrestricted gate passes.
