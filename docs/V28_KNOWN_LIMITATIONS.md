# V28.0 Known Limitations

- Final deterministic and browser certification is pending Codex.
- Native Windows and Linux three-run certification is pending.
- No external provider credentials were included or exercised.
- The deterministic fake provider covers representative workflows, not natural-language completeness.
- `fix.apply` exposes a bounded tool contract but diagnostic-specific auto-fix executors remain limited; unsupported fixes return an explicit skipped result.
- Background removal uses the existing browser-local workflow. It is confirmed and bounded, but its generated derivative lifecycle must be stress-tested with atomic job history by Codex.
- Prepared guest messaging never sends. The existing campaign UI/server remains the only dispatch authority.
- Publish/unpublish opens the existing product boundary and does not bypass its confirmation, permissions, review gates, or release policy.
- Conversation streaming uses NDJSON over HTTP rather than WebSocket transport.
- Offline conversations are intentionally session-only and are not merged automatically into authenticated server threads.
- No V29 vector/layer, V30 raster, V31 CRDT collaboration, or V32 production-infrastructure roadmap feature is implemented in V28.0.
