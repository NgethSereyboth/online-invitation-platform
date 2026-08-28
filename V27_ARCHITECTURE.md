# V27 Studio Automation Architecture

V27 is an additive operational layer over the V25 governance and V26 release systems.

## Runtime modules

- `studio-automation-v27.js`
- `studio-automation-v27.css`

The module is loaded after `studio-operations-v26.js` through `performance-loader-v22.js`. Its stylesheet is injected only when the module initializes, so neither file joins the initial editor route.

## Command ownership

The authoritative V23 command registry remains the only global shortcut owner. V27 registers:

- `studio.automation`
- `studio.bulkRemediation`
- `studio.backups`
- `studio.auditTrail`

Default launcher shortcut: `Ctrl/Cmd + Alt + Shift + A`.

## Server models

### `studio_backup_policies`

One policy per studio owner, containing enablement, interval, retention, media inclusion, last run, and next run.

### `backup_runs`

The existing backup table is additively extended with owner, initiator, archive filename, size, and error information.

### `studio_bulk_jobs`

Stores the selected scope and structured result of each organization-wide release-pin operation.

### `audit_events`

V27 reuses the existing immutable hash-chained table. A shared `write_audit_event` helper now supports both request-generated and scheduler-generated events.

## Private API surface

- `GET /api/studio/adoption`
- `POST /api/studio/releases/:id/bulk-pin`
- `GET /api/studio/bulk-jobs`
- `GET /api/studio/backup-policy`
- `PUT /api/studio/backup-policy`
- `POST /api/studio/backups/run`
- `GET /api/studio/backups`
- `GET /api/studio/backups/:id/download`
- `GET /api/studio/audit`

All mutation and download routes require authenticated same-origin access. Organization-wide operations are bound to the authenticated studio owner.
