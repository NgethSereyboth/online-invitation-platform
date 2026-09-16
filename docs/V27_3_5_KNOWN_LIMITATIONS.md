# V27.3.5 Known Limitations

## Certification boundary

- This archive is an **uncertified release candidate**. The implementation and focused evidence are complete, but the required uninterrupted review/release markers were not produced.
- Seven browser suites that require Chromium to navigate to a local `127.0.0.1` server were blocked by managed browser policy with `ERR_BLOCKED_BY_ADMINISTRATOR` before application assertions.
- Native Windows three-run certification has not run; `EINVITATION_V27_3_5_WINDOWS_3X_RELEASE_CHECK_PASSED` is absent.
- A complete native Linux three-run certification has not run. No Linux pass is claimed.
- Native physical-GPU, large-media, Windows Khmer printer/PDF-driver, and unrestricted-loopback certification remain pending.

## Preserved production limitations

- Scheduled backups run only while the application server is running.
- Generated recovery archives are stored in the local `data/backups/` directory. Direct S3/R2/cloud backup destinations are not included.
- Archive construction remains in memory before the final ZIP is written; infrastructure-level database/object-storage backups remain necessary for large deployments.
- Object storage remains local rather than a production S3/R2-compatible implementation.
- Bulk remediation is bounded to 500 owned invitations and does not rewrite governed resource references inside documents.
- Backup retention is bounded to 30 completed archives per studio.
- The Audit Trail API returns a bounded result and verifies record hashes, but it is not an externally signed ledger and a filtered response is not a complete global-chain proof.
- Offline AI capability is a deterministic **Template helper — offline**, not generative AI. Connected AI requires an authenticated server-confirmed provider.
- Release A provides typed editor transactions and previews for the existing assistant. It does not implement the V28 multi-turn AI Creative Agent, arbitrary tools, or the later V29–V32 Photoshop/Canva roadmap.

## Performance boundary

- Canonical editor route: **1,393,850 bytes**.
- Fixed ceiling: **1,420,000 bytes**.
- Remaining headroom: **26,150 bytes**.
- The full assistant implementation remains lazy-loaded and is not added to the initial canonical route.
