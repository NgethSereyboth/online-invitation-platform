# Attack Story: `materials.import_zip`

| Field | Value |
|---|---|
| **Tool ID** | `materials.import_zip` |
| **Group** | `materials` |
| **Risk tier** | `medium` |
| **Permission tier** | `edit` |
| **Executor** | `server` |
| **Binding** | `POST /api/invitations/{invitationId}/materials/import-zip` (internal-api) |
| **Reversible** | `True` (default) |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, after `materials.import_folder`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["materials.import_zip"]` |
| **Upload gate** | `ai_agent/capabilities.py:UPLOAD_TOOL_IDS = {"materials.create_folder", "materials.import_folder", "materials.import_zip"}` — requires `upload_enabled=True` and storage-quota check. |

### 1. What it touches

- **Data**: `stored_objects` (write — one row per extracted asset), `assets` (write — per-asset metadata: name, folder, tags, checksum, size, mime), `studio_resources` (write — extracted assets become available in the studio library), `materials_folders` (write — folder structure from the ZIP is reconstructed).
- **Services**: `POST /api/invitations/{invitationId}/materials/import-zip` extracts the ZIP server-side. The extraction uses Python's `zipfile` module with a path-traversal guard (per `platform_v32/service.py` — `safe_key` rejects `..` segments).
- **Files**: extracted asset files are written under the workspace's object-storage area (`{DATA}/objects-v32/{workspace_id}/...`). Object keys are derived from `safe_key(materials, asset_name)` to prevent path traversal.
- **Side effects**: the extraction runs as a background job (`media-ingest` handler registered in `platform_v32/service.py`). Each extracted asset is malware-scanned via `src/python/security_scanner_v54.py` (ClamAV / Defender) before being marked `processing_state='ready'`.

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `materials.import_zip` with an attacker-controlled `attachmentId` pointing to a previously-uploaded malicious ZIP, the attacker could:

- **Zip-slip path traversal**: a maliciously-crafted ZIP entry named `../../../etc/passwd` could, if the path-traversal guard is bypassed, write a file outside the workspace's storage area. The current `safe_key` guard rejects `..` segments, but a future regression or a Unicode-normalization bug could re-open the hole.
- **Zip-bomb denial-of-service**: a 10 MB ZIP that decompresses to 100 GB of zeros, exhausting disk space and crashing the platform.
- **Malware storage**: a ZIP containing a `.exe`, `.dll`, or `.js` file with malicious payloads. These assets are stored in the workspace's library and could be served to other hosts if the workspace is shared. The malware scanner (`security_scanner_v54.py`) is the primary defense.
- **Asset-name XSS**: an asset named `<script>alert(1)</script>.png` could, if the asset name is rendered un-escaped in the materials UI, execute JavaScript in the host's browser session.
- **Asset quota exhaustion**: a ZIP with 10 000 small files (each under the per-file size limit but cumulatively exceeding the workspace quota) could exhaust the workspace's storage allocation.
- **MIME-spoofing**: an asset declared as `image/png` in the ZIP but with a `.html` extension and HTML content could be served as HTML by the static-file handler if the MIME sniffing is permissive.

Blast radius: **workspace-wide for storage**, **potentially platform-wide if the malicious asset propagates through template sharing or marketplace installation**. Data affected: **filesystem integrity + storage abuse + XSS + supply-chain**.

### 3. Containment

- **Schema validation**: `attachmentId` is a stable-id (120 chars). `folderName` is `string(120)`.
- **Permission tier**: `edit` — owner / manager / designer / content only.
- **Confirmation boundary**: `confirmation=True` (medium-risk → `exactTargetsAccepted=True`).
- **Upload gate**: `availability()` checks `snapshot["uploadEnabled"]` and `snapshot["storageRemainingBytes"] > 0` for `UPLOAD_TOOL_IDS`. If either is false, the tool is filtered out.
- **Authorization token**: 30-second single-use, bound to the exact plan index.
- **HTTP-binding match**: `http_request_matches_tool` verifies `POST /api/invitations/{invitationId}/materials/import-zip`.
- **Path-traversal guard**: `platform_v32/storage.py::safe_key` rejects object keys containing `..` or absolute paths.
- **Malware scanning**: every extracted asset is scanned by `src/python/security_scanner_v54.py` before being marked `ready`. Scan failures raise `MalwareDetected` → HTTP 422.
- **Background job**: `media-ingest` handler runs in the bounded job queue with retry limits and cancellation.
- **Audit event**: `ai.plan_confirmed` / `ai.tool_authorized` with `metadata={"attachmentId": ..., "folderName": ..., "assetCount": ...}`.

### 4. Reversible

- **Yes**: per `ToolDefinition.reversible = True` (default).
- **How**: delete the imported folder and all its assets via the materials UI (`DELETE /api/invitations/{invitationId}/materials/folders/{folderId}` cascade-deletes child assets). Each asset's stored-object ref-count is decremented; the underlying stored object is garbage-collected when ref-count reaches zero.
- **Time to undo**: seconds for the database rows; minutes for the object-storage garbage collection.
- **Side effects of undo**: any invitation that already references the imported asset (via `asset.insert` or `materials.insert_into_page`) retains its reference, but the asset will display as "missing" once garbage-collected.

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: `invitation:{id}:materials:import`, `invitation:{id}:materials:delete`, `invitation:{id}:materials:{assetId}:move`. The `import` scope is broader than `move` because it can write multiple assets at once.
- **JIT elevation**: 5-minute TTL grant with mandatory `reason` for any import larger than 50 MB or 100 files.
- **Zip-bomb guard**: refuse any ZIP whose `uncompressed_size / compressed_size` ratio exceeds 100:1, or whose declared uncompressed size exceeds 1 GB. Per-entry size limits already exist.
- **File-type allowlist**: refuse any extracted asset whose MIME type is not in `SAFE_UPLOAD_MIMES` (per `platform_v32/service.py:SAFE_UPLOAD_MIMES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'audio/mpeg', 'audio/mp4', 'video/mp4', 'video/webm'}`). This blocks `.exe`, `.dll`, `.js`, `.html`, `.svg` (with embedded script), and other dangerous types.
- **SVG sanitization** (Phase 1b): if SVG support is added, strip `<script>`, `onload`, and external references before storing.
- **Asset-name HTML-escape**: render asset names in the UI through `esc()` (per `src/js/analytics.js` pattern). Add a contract test that verifies every UI render path escapes asset names.
- **Anomaly detection**: dashboard detects when a single workspace imports more than 500 MB of materials in a 1-hour window.

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v0_52_asset_identity_test.py` — asset identity (checksum, ref-count).
- `tests/signed_upload_backend_test.py` — signed-upload backend.
- `tests/security_regression_test.py` — security regression suite (may cover path traversal).

Gap: no test explicitly covers the zip-bomb / zip-slip attack. Add a regression test in Phase 1b that imports a malicious ZIP and verifies rejection.

### 7. AISVS cross-reference

- `C9.2.4` — confirmation (medium-risk → `exactTargetsAccepted`).
- `C9.3.3` — exact-target confirmation (`attachmentId`, `folderName`).
- `C9.7.5` — workspace budget / storage quota policy.
- `C10.5.1` — uploaded content treated as untrusted data.
- `C10.6.3` — no executable markup in asset names (HTML-escape on render).
- `C10.5.2` — bounded response schema (the import job returns a bounded `importJob` object).
