# Canva Bridge — Import / Export Design (Phase 5.1 + 5.2)

> **Why a bridge, not a competitor.** *Canva wins on raw design; eInvite wins
> on event management. A bridge is cheaper than out-designing them.*
> — ROADMAP §8.

This document specifies how an eInvite host can pull a Canva design into
eInvite (so they can attach guests, RSVPs, delivery channels, analytics) and
how they can push an eInvite invitation back into Canva (for last-mile
tweaks, brand-kit consistency, or print-ready export).

Cross-references:
* `docs/ROADMAP.md` §8 — Phase 5 acceptance: "Canva import/export works for
  at least the common template shapes."
* `docs/hosted/STORAGE-TIERS.md` — tier limits apply to imported assets.
* `platform_v32/storage.py::ObjectStorage` — where imported assets land.
* `src/python/server.py` — `/api/canva/*` routes scaffolded in V54.8.

---

## 1. Two-phase rollout

| Phase | Capability | Tier | Status |
|---|---|---|---|
| **5.1** | Import: Canva → eInvite | Standard + Pro | Designed (this doc) |
| **5.2** | Export: eInvite → Canva | Standard + Pro | Designed (this doc) |

Free tier cannot use the bridge — Canva's API rate limits and the asset-
rehosting cost make it uneconomical. Standard + Pro users get unlimited
import/export calls (subject to the tier's storage quota).

---

## 2. Import flow — Canva → eInvite

### 2.1 User-facing entry points

1. **Paste Canva design URL** — `https://www.canva.com/design/DAE123456/edit`
   or `https://www.canva.com/design/DAE123456/view`. The host pastes the
   URL into the template picker. eInvite extracts the design ID
   (`DAE123456`), fetches the design via Canva Connect API, converts it to
   an eInvite document, and creates a new invitation.
2. **Upload Canva-exported file** — the host exports their Canva design as
   a PNG or PDF and uploads it directly. eInvite treats it as a single-page
   invitation where the Canva export is the page's background image. This is
   the lower-fidelity path (no editable text layers) but works offline and
   needs no Canva Connect API credentials.

### 2.2 Backend import pipeline

```
host → POST /api/canva/import {canvaUrl} or multipart file
       │
       ├─ URL path:
       │    1. Parse design ID + variant from URL
       │    2. OAuth2: ensure host has authorized eInvite's Canva app
       │       (EINVITE_CANVA_CLIENT_ID + EINVITE_CANVA_CLIENT_SECRET)
       │    3. GET https://api.canva.com/rest/v1/designs/{designId}
       │       → returns design metadata + page thumbnails
       │    4. GET https://api.canva.com/rest/v1/exports
       │       POST body: {design_id, type='png', pages=[...]}
       │       → poll until export job completes
       │       → download each page PNG
       │    5. For each page: re-upload PNG to eInvite ObjectStorage via
       │       the existing multipart-upload flow (asset bytes flow
       │       through security_scanner_v54.scan_bytes → HTTP 422 on
       │       MalwareDetected, same as any other upload)
       │    6. Construct eInvite document JSON: one page per Canva page,
       │       page.background = {objectKey: '<uploaded-png-key>'},
       │       page.elements = [] (the Canva PNG is the page; no editable
       │       text in the import path — see §5 Limitations)
       │    7. INSERT INTO invitations(id, slug, draft_json, owner_id, ...)
       │    8. Return {invitationId, slug, warnings: [...]}
       │
       └─ Upload path:
            1. Receive multipart file (PNG or PDF)
            2. scan_bytes → ObjectStorage.put_local/put
            3. If PDF: rasterize page 1 to PNG via existing V22 GPU pipeline
               fallback (or pypdfium2 if GPU unavailable)
            4. Construct single-page eInvite document with the image as
               page background
            5. INSERT INTO invitations(...)
            6. Return {invitationId, slug}
```

### 2.3 Asset mapping

| Canva concept | eInvite concept |
|---|---|
| `design.id` (e.g. `DAE123456`) | `invitations.canva_design_id` (new column, Phase 5.1 — nullable; stored for re-import / refresh on edit) |
| `design.pages[]` | `document.pages[]` (eInvite document JSON) |
| `page.thumbnail.url` | `assets` row with `object_key = ObjectStorage.safe_key(workspace_id, asset_id, version, name)` |
| `page.background` (image fill) | `page.background.objectKey` |
| `page.text` (Canva text element) | `page.elements[]` of `kind: 'text'` with content, font, size, position |
| `page.shape` (rectangle, circle, etc.) | `page.elements[]` of `kind: 'shape'` with geometry + fill |
| `page.image` (uploaded photo) | `page.elements[]` of `kind: 'image'` with `objectKey` referencing the re-hosted asset |

### 2.4 OAuth2 with Canva Connect API

* Authorization URL: `https://www.canva.com/api/oauth/authorize?client_id={EINVITE_CANVA_CLIENT_ID}&redirect_uri={EINVITE_PUBLIC_BASE_URL}/api/canva/oauth/callback&scope=design:content:read&response_type=code&state={csrf_state}`
* Token exchange: `POST https://www.canva.com/api/oauth/token` with
  `grant_type=authorization_code`, `client_id`, `client_secret`, `code`,
  `redirect_uri`. Returns `{access_token, refresh_token, expires_in}`.
* Refresh: `POST https://www.canva.com/api/oauth/token` with
  `grant_type=refresh_token`. Tokens are stored in a new
  `canva_oauth_tokens` table (id, user_id, access_token_encrypted,
  refresh_token_encrypted, expires_at). Encryption uses the existing
  `EINVITE_SECRET_KEY` via Fernet from the `cryptography` package (already
  a transitive dependency for the Argon2id stack).

### 2.5 Configuration

New environment variables (documented in `deploy/.env.example`):

```
EINVITE_CANVA_CLIENT_ID=
EINVITE_CANVA_CLIENT_SECRET=
EINVITE_CANVA_OAUTH_REDIRECT_URI=https://your-host/api/canva/oauth/callback
EINVITE_CANVA_API_BASE=https://api.canva.com/rest/v1
```

When `EINVITE_CANVA_CLIENT_ID` is unset, the URL import path returns HTTP 503
with `{"error":"Canva Connect API is not configured","code":"canva_not_configured"}`.
The upload-file path is always available (no Canva API dependency).

---

## 3. Export flow — eInvite → Canva

### 3.1 User-facing entry point

Host clicks "Open in Canva" on the dashboard. eInvite exports the current
invitation document as a Canva-compatible JSON and either:

* (a) **Direct-import path:** POSTs the JSON to Canva Connect API's
  `POST /rest/v1/imports` endpoint, which creates a new Canva design owned
  by the host. Returns a Canva design URL — host is redirected there.
* (b) **Download path:** if the host has not authorized Canva, downloads the
  JSON as a `.canva.json` file. Host can drag-drop it into Canva's
  "Import design" page.

### 3.2 Backend export pipeline

```
host → POST /api/canva/export {invitationId}
       │
       1. Load invitations.draft_json
       2. Walk each page → convert to Canva page schema:
          • page.width, page.height (mm or px — Canva uses px @ 96 DPI)
          • page.background.color OR page.background.objectKey →
            upload the asset to Canva via POST /rest/v1/asset-uploads,
            receive a Canva asset URI, set as page background
          • page.elements[] → Canva elements[]:
              - kind: 'text' → {type: 'text', text: content,
                font_family, font_size, font_weight, color, position,
                rotation, width, height}
              - kind: 'image' → upload underlying asset to Canva,
                {type: 'image', asset_id, position, rotation, width, height}
              - kind: 'shape' → {type: 'shape', shape_type, fill, stroke,
                position, rotation, width, height}
       3. Wrap in Canva design envelope:
          {design: {type: 'doc', pages: [...], title: <invitation name>}}
       4a. Direct-import: POST /rest/v1/imports with the envelope
           → returns {design: {id, url}}
       4b. Download: respond with Content-Type: application/json and
           Content-Disposition: attachment; filename="{slug}.canva.json"
```

### 3.3 Asset re-upload to Canva

For each eInvite asset referenced by the document:

1. Read the asset from `ObjectStorage` via `ObjectStorage.read(object_key)`.
2. Compute SHA-256 (already in `stored_objects.sha256`).
3. POST to Canva's `/rest/v1/asset-uploads` with the bytes as multipart.
4. Receive `{asset_id, status: 'success' | 'failed', error?}`.
5. Cache the `object_key → Canva asset_id` mapping in a new
   `canva_asset_cache` table so re-exports don't re-upload the same
   asset (Canva asset IDs are stable per Canva user).

---

## 4. Tier gating

| Operation | Free | Standard | Pro |
|---|---|---|---|
| Import via upload (PNG/PDF) | ❌ | ✅ | ✅ |
| Import via Canva URL (requires OAuth) | ❌ | ✅ | ✅ |
| Export to Canva JSON (download) | ❌ | ✅ | ✅ |
| Export to Canva design (direct import) | ❌ | ✅ | ✅ |
| Asset re-upload to Canva (per export) | — | unlimited (subject to tier storage quota) | unlimited |

Imported assets count against the user's tier storage quota. A 50-page
Canva design with 50 MB of page thumbnails will consume 50 MB of the
user's 25 GB (Standard) or 250 GB (Pro) quota.

---

## 5. Limitations — what does NOT map cleanly

| Canva feature | eInvite behavior | Mitigation |
|---|---|---|
| **Animations** (page transitions, element animations) | Dropped on import. eInvite exports are static PNG/PDF; animations are not part of the eInvite document model. | Document this on the import dialog: "Animations will not be imported." |
| **Brand kit** (locked fonts, color palettes) | Brand kit fonts are converted to the closest eInvite font (see `assets/fonts/registry.json`); brand-kit colors are preserved as page-level color values. | Document: "Brand kit is not preserved as a managed resource; colors are inlined." |
| **Canva apps / integrations** (embed widgets) | Dropped. Each embedded widget is replaced with a placeholder rectangle + a comment annotation pointing at the Canva design URL. | Comment annotation in `invitation_comments` table; host can review and re-add manually. |
| **Smart mockups** (3D object previews) | Dropped. | Document. |
| **Canva text effects** (shadow, outline, curve) | Best-effort conversion: shadow → CSS box-shadow on text element; outline → `-webkit-text-stroke`; curve → flattened to straight text with a warning. | Document; host can re-apply curve in eInvite's V17 professional-layers transform stack. |
| **Layered groups** (Canva's group-of-groups) | Flattened. eInvite's `page.elements[]` is a flat array. Z-index is preserved via the array order. | Document. |
| **eInvite collaboration cursors** | Not exported — Canva has its own collaboration model. | N/A. |
| **eInvite delivery / RSVP state** | Not exported — these are runtime concerns, not design-time. | N/A. |
| **eInvite AI agent plans** | Not exported. | N/A. |

---

## 6. Roadmap

| Phase | Capability | Acceptance |
|---|---|---|
| 5.1 (this design) | Import via upload + Import via Canva URL | Standard-tier host can import a 10-page Canva design and the resulting invitation has all pages accessible. |
| 5.2 (this design) | Export to Canva JSON + Export to Canva design | Standard-tier host can re-open an eInvite invitation in Canva and edit text. |
| 5.3 (future) | Live Canva link (refresh on edit) | Host edits in Canva, clicks "refresh in eInvite", eInvite re-imports. Bidirectional sync NOT a goal — Canva and eInvite have different document models, and round-tripping will lose fidelity each time. |

---

## 7. Acceptance criteria (per ROADMAP §8)

* [ ] Canva import/export works for at least the common template shapes
      (single-page wedding invitation, multi-page save-the-date + details).
* [ ] Import does not require a Canva account if the host uploads a PNG/PDF.
* [ ] Export produces a Canva design the host can immediately edit
      (text layers preserved, image assets re-hosted on Canva).
* [ ] Asset bytes flow through `security_scanner_v54.scan_bytes` before
      landing in `ObjectStorage` (same as every other upload path).
* [ ] Tier gating is enforced (Free tier cannot import/export).

## 8. Change history

| Version | Date | Change |
|---|---|---|
| V54.8 | 2026-08-14 | Initial design: import (upload + Canva URL via OAuth) + export (download JSON + direct Canva import) + asset mapping + limitations table. |
