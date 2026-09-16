# V52 Selected Roadmap Architecture

Status: **implementation complete; independent Codex testing and release certification pending**.

## Cumulative boundaries

- `future_platform_v52/` owns the additive database schema and typed server services for V34, V35, V36, V42, V44, V45, V47, V48, and V52.
- `future-studio-loader-v52.js` and `future-studio-v52.css` provide one lazy, accessible platform shell. Each selected capability remains a bounded module.
- `document-schema-v32.js` and `document_schema_v32.py` remain the shared migration/normalization boundary and now normalize schema 27.
- `advanced-editor-loader-v32.js` remains the tiny canonical-route bootstrap. Vector, raster, collaboration, production operations, and V52 modules load only when opened.
- `future-public-renderer-v52.js` renders supported declarative plugin blocks and public official references without executable content.
- Existing `EInviteEditorBridge`, command registry, transaction/history service, structured renderer, publication snapshots, permissions, storage, jobs, and workspace ownership remain authoritative.

## Security boundaries

Provider keys remain server-side. Plugin manifests cannot contain executable code. Domain activation requires verified state. Bulk and export work use durable bounded jobs. Event automation actions are registered and confirmation-aware. Invitation text, imported rows, template packages, SVG/media, plugin metadata, and external provider results remain untrusted data.

## Data model

Schema 27 adds durable references for editor profiles, AI policies/workflows/budgets, marketplace lineage, enterprise protocols/approvals, animation projects/exports, domains/environments, merge jobs/variants, plugin installations/grants, and event operations. Large media bytes remain in the material/object-storage abstraction.
