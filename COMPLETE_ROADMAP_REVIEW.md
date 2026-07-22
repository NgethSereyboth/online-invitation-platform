# E-invitation-website — Complete Roadmap Review Build

This build consolidates the full product roadmap requested before production-provider deployment. It is intended for hands-on product review, not for claiming that external provider integrations have already been validated against real production accounts.

## Review the product locally

```powershell
python -u server.py --port 8080
```

Open:

```text
http://127.0.0.1:8080
```

For deterministic automated checks:

```powershell
python run_review_checks.py
```

Optional browser/visual checks (requires Playwright Chromium to be allowed to access the local loopback server):

```powershell
python tests/ui_smoke_test.py
python tests/visual_regression.py --update
python tests/visual_regression.py
```

## Creation Studio completed

- Persistent Select, Text, Frame, Rectangle, Ellipse, Line, Hand and Zoom tools.
- Canva/Photoshop-style keyboard workflow and Alt-drag duplication.
- Direct double-click rich-text editing on the canvas.
- Contextual top toolbar and advanced inspector.
- Visual schedule, venue and published-section-order builders.
- Searchable layers with selection, rename, visibility and locking.
- Multi-selection, marquee, grouping, alignment, distribution, smart layouts, guides and object snapping.
- Copy/paste across pages and reusable element groups/pages/templates.
- Searchable font browser with categories, favorites and recents.
- Expanded invitation element library and ready-made creative compositions.
- Masks, frames, crop focus, filters, blend modes, gradients, shadows and advanced typography.
- Motion timeline, animation delay, stagger and page/section transitions.
- Light, Dark and System app appearance modes.
- Modern dialogs/toasts replacing browser prompt/confirm UX.

## Invitation-specific workflows completed

- Wedding, birthday and business invitation starter systems.
- Khmer and English content with guest language switching.
- Khmer lunar dates.
- Schedule, multiple venues, maps, countdown, galleries, video and music.
- YouTube music support after guest interaction.
- RSVP, custom questions, guest wishes and guest management.
- Personalized guest links, QR codes and arrival check-in.
- Immutable publishing snapshots, version history and unpublishing.
- Password-protected invitations.
- Analytics and invitation readiness/design checks.

## Media and AI workflows completed

- Account-wide material library with folders, tags, favorites, search and usage tracking.
- Duplicate-file storage reuse for normal server uploads.
- Raw binary uploads for local deployments.
- Signed browser-direct R2/S3 upload flow with server verification and registration.
- Shared browser upload client that automatically uses direct storage when configured and falls back to the local server upload path when it is not configured.
- Automatic background cut for simpler backgrounds.
- Background-cut results saved as material assets when server-connected rather than embedded as large invitation JSON data URLs.
- Advanced non-destructive photo editor.
- Invitation-specific AI Studio with local deterministic fallback and configurable external-provider adapter.

## Collaboration completed

- Viewer, content, designer and manager collaboration roles.
- Server-side invitation permissions.
- Server-Sent Events (SSE) remote-change awareness with polling fallback.
- Remote-change review prompt rather than pretending to provide conflict-free simultaneous editing.

## Production foundations completed

- Zero-dependency SQLite local runtime.
- PostgreSQL runtime adapter selected through `EINVITE_DATABASE_URL`.
- SQLite-to-PostgreSQL migration tooling.
- Local media storage and S3-compatible/R2 object storage adapter.
- Signed direct-upload endpoints and shared upload client.
- HttpOnly SameSite session cookies for browser authentication.
- Compatibility bearer API tokens for API/testing workflows.
- Same-origin validation for cookie-authenticated state changes.
- CSP and additional browser security headers.
- Redis distributed rate-limit adapter with in-process fallback.
- SMTP email verification and password-reset integration.
- Provider-neutral hosted checkout adapter and HMAC-signed billing webhook handling.
- Admin monitoring/health metrics and structured JSON logging option.
- Backup and migration tooling.

## Automated validation included

Deterministic suites cover:

- static HTML/script/asset integrity;
- main account/invitation/publishing/RSVP/material workflow;
- plan-limit enforcement;
- advanced final feature validation;
- cookie authentication and production-security foundations;
- AI and billing provider adapter contracts;
- collaboration SSE and direct-upload fallback behavior;
- signed object-storage upload signing, completion verification and material registration through a deterministic fake object store.

## External validation still required before real production launch

The code paths and adapters are present, but the following require real selected infrastructure and credentials:

- Managed PostgreSQL operational validation, connection limits, failover and backups.
- Real Cloudflare R2/Amazon S3 credentials, bucket CORS and CDN/custom-domain validation.
- Real Redis deployment for multi-instance rate limiting.
- Real SMTP delivery reputation and provider configuration.
- Real external AI provider output quality, latency, cost controls and safety policy.
- Real payment-provider sandbox/production checkout, taxes, invoices and settlement.
- Production HTTPS/domain/reverse proxy and monitoring/alerting integration.
- Full browser visual regression on a machine/environment where Playwright Chromium is permitted to access the local application.

The review build deliberately reports those boundaries rather than faking successful hosted-service integration.
