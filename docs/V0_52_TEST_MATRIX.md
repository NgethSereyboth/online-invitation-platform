# V0.52 Test Matrix

| Area | Current repair evidence | Release boundary |
|---|---|---|
| Registered deterministic matrix | **90/90 passed**, including final release-evidence/hash verification | Independent fresh-extraction rerun recommended |
| Registered Chromium matrix | 114 unique entries registered, including 3 new real-server regressions | Served HTTP Chromium is blocked here by `ERR_BLOCKED_BY_ADMINISTRATOR`; unrestricted rerun required |
| Total registered matrix | 204 unique entries | Independent full one-command rerun required for certification |
| Real HTTP AI | Clean SQLite, auth, invitation/thread, offline-provider NDJSON, persisted messages/job and unresolved-comment context passed | Real-browser AI path still requires unrestricted navigation |
| Autosave | Source-level root cause repaired; deterministic/revision contracts pass | New real-browser two-edit/status/reload regression registered |
| Dashboard cover | Recursive target repaired; current smoke/browser regressions updated | New real-server browser regression registered |
| Asset identity/publication | Canonical/scoped legacy migration and cross-scope rejection passed | Preserve in final gate |
| Canonical build integrity | Editor/route/page builders regenerated and check-only verification passed before freeze | Repeat from final fresh extraction |
| Editor route | 1,413,344 canonical bundle bytes; 1,417,331 complete startup bytes | Fixed 1,420,000 limit unchanged |
| Public route | 233,585 bytes | Fixed 260,000 limit unchanged |
| Schema | 27; idempotent legacy migration contracts preserved | No schema-number change |
| External/native/security/scale/recovery | Not executed without required infrastructure/credentials | Pending independent certification |

No release certification is claimed by this matrix.
