# AI Tool Attack Stories — Index

> **Scope**: 80 registered AI tools (per `ai_agent/tools.py:_defs()`), grouped by tool-group prefix.
> **12 high-blast-radius tools** have full attack stories (linked below). The remaining **68 tools** have a one-line blast-radius + containment entry in the per-group tables.
> **Template**: `_TEMPLATE.md` — use this to expand any one-line entry into a full attack story.

## How to read this index

| Column | Meaning |
|---|---|
| **Tool ID** | The stable id as registered in `ai_agent/tools.py:TOOLS`. |
| **Risk** | `low` / `medium` / `high` — per `ToolDefinition.risk`. |
| **Permission** | `read` / `edit` / `manage` / `admin` — per `ToolDefinition.permission`. |
| **Confirmation** | `Y` if `ToolDefinition.confirmation=True`, else `—`. |
| **Reversible** | `Y` if `ToolDefinition.reversible=True`, else `N`. |
| **Blast radius** | `invitation` / `workspace` / `account` / `external` / `system` — the maximum scope of harm if the tool is invoked by a malicious actor. |
| **Containment file** | The attack story file (`*.md`) that documents the worst case + containment + reversibility. For one-line entries, `_TEMPLATE.md` (expandable) or the closest related story. |

## High-blast-radius tools — 12 full attack stories

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `publish.prepare` | high | manage | Y | N | external (publication) | [`publish.prepare.md`](publish.prepare.md) |
| `message.prepare_send` | high | manage | Y | N | external (guest PII + sender reputation) | [`message.prepare_send.md`](message.prepare_send.md) |
| `invitation.archive` | high | manage | Y | Y | invitation (visibility + workflow DoS) | [`invitation.archive.md`](invitation.archive.md) |
| `invitation.update_operations` | high | manage | Y | Y | workspace (custom domain + DNS posture) | [`invitation.update_operations.md`](invitation.update_operations.md) |
| `plugin.configure` | high | manage | Y | N | workspace (supply-chain + sandbox escape) | [`plugin.configure.md`](plugin.configure.md) |
| `marketplace.install_template` | medium | manage | Y | Y | workspace (supply-chain + XSS) | [`marketplace.install_template.md`](marketplace.install_template.md) |
| `merge.prepare_job` | high | manage | Y | N | workspace + external (bulk PII + billing) | [`merge.prepare_job.md`](merge.prepare_job.md) |
| `publishing.configure_environment` | high | manage | Y | N | workspace (production promotion + TLS) | [`publishing.configure_environment.md`](publishing.configure_environment.md) |
| `guest.delete` | high | manage | Y | N | invitation (PII destruction + audit evidence) | [`guest.delete.md`](guest.delete.md) |
| `materials.import_zip` | medium | edit | Y | Y | workspace (zip-slip + zip-bomb + XSS) | [`materials.import_zip.md`](materials.import_zip.md) |
| `event.prepare_automation` | high | manage | Y | N | workspace + external (chain-reaction + SSRF) | [`event.prepare_automation.md`](event.prepare_automation.md) |
| `enterprise.prepare_protocol` | medium | manage | Y | Y | workspace (classification downgrade) | [`enterprise.prepare_protocol.md`](enterprise.prepare_protocol.md) |

---

## Per-group index — 80 tools

### `read.*` group — bounded read tools (3 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `read.project_summary` | low | read | — | Y | invitation (PII disclosure if scope bypass) | `_TEMPLATE.md` |
| `read.page_summary` | low | read | — | Y | invitation (PII disclosure if scope bypass) | `_TEMPLATE.md` |
| `read.selection_summary` | low | read | — | Y | invitation (PII disclosure if scope bypass) | `_TEMPLATE.md` |

### `selection.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `selection.select_layers` | low | edit | — | Y | invitation (no external harm; affects only editor state) | `_TEMPLATE.md` |

### `object.*` group (6 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `object.create_text` | low | edit | — | Y | invitation (document mutation) | `_TEMPLATE.md` |
| `object.create_image` | medium | edit | — | Y | invitation (asset reference injection) | `_TEMPLATE.md` |
| `object.create_shape` | low | edit | — | Y | invitation (document mutation) | `_TEMPLATE.md` |
| `object.update` | low | edit | — | Y | invitation (document mutation) | `_TEMPLATE.md` |
| `object.duplicate` | low | edit | — | Y | invitation (document growth / quota) | `_TEMPLATE.md` |
| `object.delete` | high | edit | Y | Y | invitation (destructive deletion of project content) | `_TEMPLATE.md` (similar to `guest.delete.md`) |

### `rich_text.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `rich_text.replace` | low | edit | — | Y | invitation (text content) | `_TEMPLATE.md` |

### `transform.*` group (9 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `transform.move` | low | edit | — | Y | invitation (geometry) | `_TEMPLATE.md` |
| `transform.resize` | low | edit | — | Y | invitation (geometry) | `_TEMPLATE.md` |
| `transform.rotate` | low | edit | — | Y | invitation (geometry) | `_TEMPLATE.md` |
| `transform.align` | low | edit | — | Y | invitation (geometry) | `_TEMPLATE.md` |
| `transform.distribute` | low | edit | — | Y | invitation (geometry) | `_TEMPLATE.md` |
| `transform.tidy` | medium | edit | — | Y | invitation (geometry; multi-object) | `_TEMPLATE.md` |
| `transform.group` | low | edit | — | Y | invitation (grouping) | `_TEMPLATE.md` |
| `transform.ungroup` | low | edit | — | Y | invitation (grouping) | `_TEMPLATE.md` |
| `transform.arrange` | low | edit | — | Y | invitation (layer order) | `_TEMPLATE.md` |

### `style.*` group (4 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `style.apply_text_style` | low | edit | — | Y | invitation (style) | `_TEMPLATE.md` |
| `style.apply_palette` | medium | edit | — | Y | invitation (palette; multi-page) | `_TEMPLATE.md` |
| `style.apply_brand_kit` | medium | edit | — | Y | invitation (brand; cross-page) | `_TEMPLATE.md` |
| `style.apply_photo` | low | edit | — | Y | invitation (photo preset) | `_TEMPLATE.md` |

### `photo.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `photo.remove_background` | medium | edit | Y | Y | invitation (creates derivative asset; supply-chain risk via background-removal model) | `_TEMPLATE.md` |

### `image.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `image.configure_frame` | low | edit | — | Y | invitation (frame / mask / focal position) | `_TEMPLATE.md` |

### `gallery.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `gallery.arrange` | medium | edit | — | Y | invitation (multi-object grid) | `_TEMPLATE.md` |

### `page.*` group (5 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `page.create` | medium | edit | — | Y | invitation (page growth) | `_TEMPLATE.md` |
| `page.duplicate` | medium | edit | — | Y | invitation (page growth + asset duplication) | `_TEMPLATE.md` |
| `page.rename` | low | edit | — | Y | invitation (metadata) | `_TEMPLATE.md` |
| `page.reorder` | medium | edit | — | Y | invitation (page order) | `_TEMPLATE.md` |
| `page.configure_style` | medium | edit | — | Y | invitation (background + animation) | `_TEMPLATE.md` |

### `invitation.*` group (4 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `invitation.configure_opening` | medium | edit | — | Y | invitation (opening scene) | `_TEMPLATE.md` |
| `invitation.archive` | high | manage | Y | Y | invitation (visibility + workflow DoS) | [`invitation.archive.md`](invitation.archive.md) |
| `invitation.update_operations` | high | manage | Y | Y | workspace (custom domain + DNS) | [`invitation.update_operations.md`](invitation.update_operations.md) |
| `invitation.configure_rsvp` | medium | manage | Y | Y | invitation (RSVP enable/disable) | `_TEMPLATE.md` |

### `event.*` group (6 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `event.update_fields` | medium | edit | — | Y | invitation (event details, bilingual) | `_TEMPLATE.md` |
| `event.configure_details` | medium | edit | — | Y | invitation (language, date, venue, map URL) | `_TEMPLATE.md` |
| `event.update_schedule` | medium | edit | — | Y | invitation (schedule replacement) | `_TEMPLATE.md` |
| `event.create_task` | low | edit | — | Y | workspace (event task creation) | `_TEMPLATE.md` |
| `event.run_intelligence` | low | read | — | Y | workspace (read-only analysis) | `_TEMPLATE.md` |
| `event.prepare_automation` | high | manage | Y | N | workspace + external (chain-reaction + SSRF) | [`event.prepare_automation.md`](event.prepare_automation.md) |

### `guest.*` group (5 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `guest.create` | medium | manage | Y | Y | invitation (guest PII write) | `_TEMPLATE.md` |
| `guest.update` | medium | manage | Y | Y | invitation (guest PII modification) | `_TEMPLATE.md` |
| `guest.delete` | high | manage | Y | N | invitation (PII destruction + audit) | [`guest.delete.md`](guest.delete.md) |
| `guest.check_in` | medium | manage | Y | Y | invitation (check-in state) | `_TEMPLATE.md` |
| `guest.read_delivery_status` | low | manage | — | Y | invitation (delivery PII read) | `_TEMPLATE.md` |

### `rsvp.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `rsvp.update` | medium | manage | Y | Y | invitation (RSVP state — could be used to silently decline invited guests) | `_TEMPLATE.md` |

### `analytics.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `analytics.read_summary` | low | read | — | Y | invitation (read-only analytics) | `_TEMPLATE.md` |

### `account.*` group (1 tool)

> **Note**: There is currently no `account.billing` or `account.admin` tool registered — the only `account.*` tool is `account.read_usage`. Billing operations flow through the billing webhook (`src/python/server.py::verify_billing_webhook`) and admin operations through the admin UI. The absence of agent-facing billing / admin tools is itself an AISVS-relevant finding (see `docs/ai/AISVS-C9-C10-MAPPING.md` C9.2.7).

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `account.read_usage` | low | read | — | Y | account (read-only usage) | `_TEMPLATE.md` |

### `materials.*` group (10 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `materials.list_folders` | low | read | — | Y | invitation (read-only) | `_TEMPLATE.md` |
| `materials.create_folder` | low | edit | — | Y | invitation (folder metadata) | `_TEMPLATE.md` |
| `materials.import_folder` | medium | edit | Y | Y | workspace (folder upload + path traversal risk) | [`materials.import_zip.md`](materials.import_zip.md) (analogous) |
| `materials.import_zip` | medium | edit | Y | Y | workspace (zip-slip + zip-bomb + XSS) | [`materials.import_zip.md`](materials.import_zip.md) |
| `materials.move` | low | edit | — | Y | invitation (asset folder) | `_TEMPLATE.md` |
| `materials.rename` | low | edit | — | Y | invitation (asset name; XSS if unescaped) | `_TEMPLATE.md` |
| `materials.update_metadata` | medium | edit | Y | Y | invitation (asset metadata) | `_TEMPLATE.md` |
| `materials.classify` | low | edit | — | Y | invitation (asset tags) | `_TEMPLATE.md` |
| `materials.find_duplicates` | low | read | — | Y | invitation (read-only duplicate scan) | `_TEMPLATE.md` |
| `materials.insert_into_page` | medium | edit | — | Y | invitation (asset insertion) | `_TEMPLATE.md` |

### `design.*` group (2 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `design.analyze_reference` | low | edit | — | Y | invitation (read-only analysis) | `_TEMPLATE.md` |
| `design.apply_blueprint` | medium | edit | — | Y | invitation (style/palette/typography application; multi-page) | `_TEMPLATE.md` |

### `asset.*` group (2 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `asset.search` | low | read | — | Y | workspace (read-only asset search) | `_TEMPLATE.md` |
| `asset.insert` | medium | edit | — | Y | invitation (asset insertion) | `_TEMPLATE.md` |

### `check.*` group (4 tools)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `check.design` | low | read | — | Y | invitation (read-only diagnostics) | `_TEMPLATE.md` |
| `check.accessibility` | low | read | — | Y | invitation (read-only diagnostics) | `_TEMPLATE.md` |
| `check.layout` | low | read | — | Y | invitation (read-only diagnostics) | `_TEMPLATE.md` |
| `check.print` | low | read | — | Y | invitation (read-only diagnostics) | `_TEMPLATE.md` |

### `fix.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `fix.apply` | medium | edit | — | Y | invitation (applies bounded repair; could be abused to overwrite content if fix schema is loose) | `_TEMPLATE.md` |

### `preview.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `preview.prepare` | low | read | — | Y | invitation (side-effect-free preview) | `_TEMPLATE.md` |

### `export.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `export.prepare` | medium | edit | Y | Y | invitation (export could disclose project content; backup format exports the full document) | `_TEMPLATE.md` |

### `publish.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `publish.prepare` | high | manage | Y | N | external (publication) | [`publish.prepare.md`](publish.prepare.md) |

### `message.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `message.prepare_send` | high | manage | Y | N | external (guest PII + sender reputation) | [`message.prepare_send.md`](message.prepare_send.md) |

### `editor.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `editor.apply_workspace` | low | edit | — | Y | invitation (workspace mode; no content change) | `_TEMPLATE.md` |

### `marketplace.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `marketplace.install_template` | medium | manage | Y | Y | workspace (supply-chain + XSS) | [`marketplace.install_template.md`](marketplace.install_template.md) |

### `enterprise.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `enterprise.prepare_protocol` | medium | manage | Y | Y | workspace (classification downgrade) | [`enterprise.prepare_protocol.md`](enterprise.prepare_protocol.md) |

### `animation.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `animation.update_timeline` | medium | edit | — | Y | invitation (animation timeline; multi-track could trigger heavy rendering) | `_TEMPLATE.md` |

### `publishing.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `publishing.configure_environment` | high | manage | Y | N | workspace (production promotion + TLS) | [`publishing.configure_environment.md`](publishing.configure_environment.md) |

### `merge.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `merge.prepare_job` | high | manage | Y | N | workspace + external (bulk PII + billing) | [`merge.prepare_job.md`](merge.prepare_job.md) |

### `plugin.*` group (1 tool)

| Tool ID | Risk | Permission | Conf. | Rev. | Blast radius | Containment file |
|---|---|---|---|---|---|---|
| `plugin.configure` | high | manage | Y | N | workspace (supply-chain + sandbox escape) | [`plugin.configure.md`](plugin.configure.md) |

---

## Counts

| Category | Count |
|---|---:|
| Full attack stories (high-blast-radius) | 12 |
| One-line entries (template-expandable) | 68 |
| **Total tools covered** | **80** |

## How to expand a one-line entry into a full attack story

1. Copy `_TEMPLATE.md` to `{tool_id}.md` (e.g. `object.delete.md`).
2. Fill in the metadata table from `ai_agent/tools.py:_defs()` and `ai_agent/capabilities.py:TOOL_BINDINGS`.
3. Reference the closest related high-blast-radius story for the threat-model structure (e.g. `object.delete` mirrors `guest.delete.md`; `materials.import_folder` mirrors `materials.import_zip.md`).
4. Update this README to link to the new story.

## Highest-priority one-line entries to expand next (Phase 1b)

These 8 tools are not in the top-12 but are the next-highest priority for full attack-story expansion:

1. `object.delete` — destructive deletion of project content (high risk, but invitation-scoped).
2. `materials.import_folder` — same blast surface as `materials.import_zip` (path traversal + zip bomb equivalent for nested folder structures).
3. `rsvp.update` — silent RSVP state manipulation could be used to disinvite specific guests.
4. `invitation.configure_rsvp` — disabling RSVP mid-event blocks new responses.
5. `export.prepare` — backup-format export discloses the full document.
6. `photo.remove_background` — derivative asset creation + local-model invocation.
7. `invitation.configure_opening` — opening-scene manipulation could affect brand integrity.
8. `fix.apply` — applies bounded repair but could overwrite content if fix schema is loose.
