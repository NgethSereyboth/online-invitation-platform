# Round 1 — fix plan

| # | Finding | Action | Files | Status |
|---|---|---|---|---|
| 1 | BUG-R1-1 raw JSON for signed-out editor URLs | Content-negotiate the management page: HTML navigations get a 302 to the dashboard with `next`; API clients keep 401. | `src/python/server.py` | Done — `fix-round-1` |
| 2 | BUG-R1-2 soft 404 for missing slugs | Return 404 with the existing unavailable shell when no published invitation exists; keep the client’s API 404. | `src/python/server.py` (`serve_public`) | Open — needs cache/policy check |
| 3 | BUG-R1-3 CSP data-URI fetch | Trace the generated SVG placeholder fetch in the cover/export path and pass the object URL/blob directly; do not widen `connect-src`. | likely `src/js/public-page.js` or `src/js/share.js`; confirm with the console stack | Open |
| 4 | BUG-R1-4 stale inline fixture | Inline the bundle that defines `EInviteProfessionalEditor` before the v17 boot wait. | `tests/inline_editor_runtime_test.py` | Stuck after 3 probes — logged |
| 5 | Verification | Re-run full pytest, `build.py all`, bundles, mirror and compile; deploy; prove the live redirect and bundle hash. | — | In progress |

No assertion was deleted or weakened, no test was skipped, and no `@ts-ignore`/`eslint-disable`
was added. The 401 contract test still passes for API clients.
