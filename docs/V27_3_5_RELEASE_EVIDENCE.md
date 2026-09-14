# V27.3.5 Release Evidence

## Baseline and preservation

- Baseline archive: `e-invitation-platform-studio-automation-v27.3.4-repaired.zip`
- Baseline SHA-256: `ee37a64bc02c56b84e467c36d4370a46d5854c51e18198718cc556990709f052`
- Extraction rejected unsafe absolute, drive-qualified, traversal, or escaping ZIP paths.
- Schema remains 14.
- README SHA-256 remains `f3c158d37f1ab2367a4bd0565c230535369596431709cbbd3cb234c324633330`.
- Existing Studio Automation, governance/templates, review/approval, publishing snapshots, optional RSVP, Khmer/lunar-date/fonts, typography, rich text, photo, animation, public invitation, collaboration, backups, audit, server/storage abstraction, and offline capabilities remain present.

## Route and lazy-loading evidence

- Canonical route bytes: `1393850`.
- Fixed limit: `1420000`.
- Headroom: `26150`.
- `ai-assistant-pro.js` and `ai-assistant-pro.css` are not eagerly embedded in `editor-suite.js`, `editor-suite.css`, or the canonical route source list.
- The route includes the small `ai-editor-action-service-v27.js`, `ai-assistant-loader-v27.js`, and `ai-assistant-loader-v27.css`; the full drawer implementation loads on first open.

## Per-file manifest rule

`V27_3_5_RELEASE_FILE_HASHES.sha256` uses this deterministic rule:

1. Walk every shipped regular file below the project root.
2. Exclude only `V27_3_5_RELEASE_FILE_HASHES.sha256` itself.
3. Sort paths by their POSIX-style relative path.
4. Hash raw file bytes with SHA-256.
5. Write `<64 lowercase hex><two spaces><relative POSIX path>` per line.

Generated signing secrets, databases, caches, PID files, debug logs, temporary test data, and incomplete release logs are excluded from the archive before manifest generation.

## Test evidence

- 76/76 deterministic contracts passed in isolated segmented execution.
- 97/104 browser contracts passed; all 104 were attempted.
- Seven server-navigation suites were blocked by managed Chromium loopback policy before assertions.
- No browser application assertion failed after a page loaded.
- The required full-review, final-release, and Windows 3× success markers remain absent.

## Fresh-extraction acceptance

The final ZIP acceptance procedure verifies:

- ZIP SHA-256 sidecar;
- safe member paths;
- exact single project-root directory;
- absence of forbidden caches/secrets/databases/logs/PID files;
- README hash and schema/build identity;
- canonical route check-only stages;
- complete manifest coverage and every file hash;
- the honest pending certification state.
