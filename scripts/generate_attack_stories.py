#!/usr/bin/env python3
"""Generate complete AI tool attack stories from reviewed threat narratives.

Tool metadata comes from the live AI registry. The per-tool threat and exposure
statements below are reviewed content; adding a new tool requires adding its
scenario instead of silently getting a generic story. Run with --check to verify
that the checked-in Markdown still matches this source.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ai_agent.capabilities import TOOL_BINDINGS  # noqa: E402
from ai_agent.jit_elevation import AUTO_APPROVED_TOOLS, JIT_ELIGIBLE_TOOLS  # noqa: E402
from ai_agent.tools import TOOLS  # noqa: E402

# (direct impact, plausible malicious or injected-agent outcome). Keep scenarios
# grounded in each tool's declared effect and bounded arguments.
THREATS: dict[str, tuple[str, str]] = {
    "read.project_summary": ("the bounded current invitation summary and its selected design fields", "use an unauthorized read to expose guest-facing event details, draft content, or scheduling information to a caller or provider that should not receive it"),
    "read.page_summary": ("the named page's bounded text, object, and layout summary", "choose a page containing private notes or sensitive event details and cause them to be included in model context or returned to a user without page-level authorization"),
    "read.selection_summary": ("the captured selected-object IDs and their bounded content", "select a text object containing a private address, access code, or personal detail and exfiltrate that content through a later prompt or provider"),
    "selection.select_layers": ("editor selection state for the supplied object IDs", "select an unintended set of layers to mislead a host about which objects a later edit or confirmation will affect"),
    "object.create_text": ("the active invitation page's scene graph and a new bounded text object", "insert misleading RSVP instructions, defamatory text, or a phishing URL-like string that changes what guests see when the invitation is published"),
    "object.create_image": ("the page scene graph and a reference to an already-authorized asset ID", "insert an inappropriate, deceptive, or privacy-sensitive image into the invitation, or attempt to reference an asset outside the authorized project"),
    "object.create_shape": ("the page scene graph, shape geometry, and a bounded hex fill color", "obscure a disclaimer, RSVP control, or event detail with a large or high-contrast shape before the host notices the design change"),
    "object.update": ("the selected objects' allow-listed patchable properties on one page", "replace text, geometry, visibility, or style with deceptive content or move critical invitation information off-canvas"),
    "object.duplicate": ("the selected page objects and invitation document size", "duplicate costly or sensitive objects repeatedly to bloat the document, exhaust storage limits, or create confusing near-identical content"),
    "object.delete": ("the selected page-local objects and their document references", "remove the invitation title, RSVP directions, accessibility content, or a host's authored design; repeated authorized plans could compound the loss"),
    "rich_text.replace": ("structured text runs for the supplied object IDs and the requested bounded replacement text", "silently replace invitation wording, Khmer translations, dates, or accessibility text while preserving formatting that makes the altered text look authentic"),
    "transform.move": ("the page geometry of up to the schema-bounded set of object IDs", "move a venue, date, RSVP link, or disclosure outside the visible canvas so guests miss essential event information"),
    "transform.resize": ("width and height of the selected page objects", "shrink essential text or enlarge a decorative layer over the event details, making the invitation misleading or unusable"),
    "transform.rotate": ("rotation values for the selected page objects", "rotate key wording or controls until they are unreadable or overlap other invitation content"),
    "transform.align": ("relative alignment of the supplied object IDs on a page", "rearrange a group so the visual hierarchy hides a date change, consent language, or important host-provided details"),
    "transform.distribute": ("spacing of selected objects along the requested page axis", "spread a related set of labels and controls apart, causing text to appear associated with the wrong date, venue, or response option"),
    "transform.tidy": ("a bounded grid layout and geometry for the selected objects", "reflow a carefully composed invitation into overlapping or misleading groupings that a host may accept as a routine cleanup"),
    "transform.group": ("scene-graph grouping and parent relationships for selected objects", "group unrelated content so later movement or deletion affects labels, decorations, and event details together"),
    "transform.ungroup": ("group membership and hierarchy for selected objects", "break a carefully constrained layout apart so related elements can be independently displaced or altered"),
    "transform.arrange": ("z-order of the selected page objects", "place a covering object above an RSVP button, notice, or event detail to hide or misrepresent it"),
    "style.apply_text_style": ("semantic text-style references on the selected text objects", "apply a low-contrast or tiny style to event details, Khmer text, or safety instructions while leaving content technically present"),
    "style.apply_palette": ("invitation-wide palette values, bounded to four validated colors", "apply a low-contrast palette that makes RSVP controls or important text unreadable across the invitation"),
    "style.apply_brand_kit": ("a saved, authorized brand-kit reference and the invitation style state", "apply the wrong organization's colors or marks, impersonating another event host or undermining brand trust"),
    "style.apply_photo": ("non-destructive image-style properties for selected invitation images", "distort or darken a person or venue image enough to mislead guests or harm the host's reputation"),
    "image.configure_frame": ("frame, fit, mask, focal point, and crop properties for selected images", "crop a person, logo, or safety-relevant image detail out of view or apply a misleading focal crop"),
    "gallery.arrange": ("geometry for a bounded collection of selected image objects", "reorder or crowd photos so a host-approved image is obscured or a misleading gallery presentation appears in the published invitation"),
    "photo.remove_background": ("the selected authorized image and a derived background-removed material", "create and insert a misleading derivative of a person's photograph or consume local processing/storage resources without informed review"),
    "page.create": ("the invitation's page collection and section ordering", "add a page with deceptive or unfinished content that later becomes publicly visible when the invitation is published"),
    "page.duplicate": ("the selected page and its referenced objects/assets", "duplicate private or obsolete content into a new page that is accidentally left visible to invitees"),
    "page.rename": ("a page's bounded display name and navigation metadata", "rename pages to mislead the host about which content is being reviewed or published"),
    "page.reorder": ("the invitation's page-order list", "move obsolete, draft, or misleading content into the first guest-visible position"),
    "page.configure_style": ("page-level background, animation, transition, and authorized background-asset references", "configure a distracting transition or inaccessible background that conceals text or causes motion discomfort for guests"),
    "invitation.configure_opening": ("the invitation's opening scene, bilingual copy, visual options, and skip behavior", "replace the opening with deceptive event framing or make the experience difficult to skip for guests using assistive technology"),
    "event.update_fields": ("the invitation's bounded English and Khmer event-field map", "change the couple's names, date, venue, or other invitation facts and leave guests relying on false event details"),
    "event.configure_details": ("language mode, date presentation, Khmer date text, map link, and structured venue entries", "replace the destination map or venue address with an attacker-controlled location or create conflicting English and Khmer details"),
    "event.update_schedule": ("the complete structured schedule list for the invitation", "replace ceremony times, locations, or sequence so guests arrive at the wrong time or miss key parts of the event"),
    "guest.create": ("one new invitation guest record containing bounded contact, household, tag, and seating data", "add an attacker-controlled email/phone recipient to guest communications or consume guest capacity with fabricated records"),
    "guest.update": ("the identified guest's contact, household, tags, and seating fields", "redirect a real guest's communications to an attacker, alter their seating assignment, or change their household association"),
    "guest.check_in": ("the check-in status of the identified invitation guest", "falsely mark a guest checked in or absent, disrupting arrival counts and event operations"),
    "rsvp.update": ("the identified stored RSVP status and guest-count values", "change a guest's acceptance to decline or inflate attendance so the host makes incorrect catering and seating decisions"),
    "analytics.read_summary": ("authorized invitation view and response aggregates", "infer attendance, guest activity, or event timing from analytics and expose it outside the authorized host workflow"),
    "account.read_usage": ("the authenticated user's plan and bounded storage/usage totals", "expose account-plan or usage information to a different account if identity scoping is bypassed"),
    "materials.list_folders": ("the authorized invitation's material-folder hierarchy and names", "disclose private asset names or organizational structure from a project to an unauthorized user"),
    "materials.create_folder": ("a new project-local folder entry under an authorized parent", "create a confusing or excessive folder hierarchy that hides assets or consumes database/management capacity"),
    "materials.import_folder": ("user-attached files, their relative folder paths, and a durable import job", "abuse crafted names or deeply nested batches to create path confusion, resource exhaustion, or unauthorized material placement"),
    "materials.move": ("the authorized asset's folder association", "move an asset out of the folder where a host expects it, hiding it from review or causing the wrong asset to be selected"),
    "materials.rename": ("the authorized asset's display name, not its stored bytes", "rename a harmful or private asset to impersonate an approved logo, invite image, or consent document"),
    "materials.update_metadata": ("the authorized asset's name, folder, tags, and favorite metadata", "mislabel or hide an asset from the host's review while leaving its underlying content unchanged"),
    "materials.classify": ("category and tags for the supplied authorized asset IDs", "bulk-misclassify invitation assets so unsafe or private files appear as approved, public-ready materials"),
    "materials.find_duplicates": ("checksums and metadata for authorized project materials; no deletion is declared", "use duplicate reports to infer private uploads or create a misleading cleanup recommendation that leads the host to remove the wrong asset"),
    "materials.insert_into_page": ("a page object referencing one authorized invitation material and its alt text", "insert a private, unreviewed, or incorrectly described asset where invitees can see it"),
    "design.analyze_reference": ("authorized reference-image asset IDs, target-page context, and a stored structured blueprint", "plant attacker-influenced visual guidance in a blueprint that later steers the host toward deceptive branding or unsafe layout changes"),
    "design.apply_blueprint": ("a stored validated blueprint, typed editor operations, or a new invitation created from its fields", "apply an unexpected design across the invitation or create a misleading new project under a trusted host account"),
    "invitation.configure_rsvp": ("the invitation's existing RSVP-enabled state", "disable responses before guests reply, or enable an unreviewed collection point during an active event"),
    "guest.read_delivery_status": ("bounded delivery-state records for the supplied authorized guest IDs", "expose guest contact/delivery outcomes or reveal which recipients have not received the invitation"),
    "asset.search": ("authorized project/studio asset names, types, and search results", "enumerate private asset metadata or surface an unrelated tenant's materials through an authorization-scope failure"),
    "asset.insert": ("an authorized asset reference and a new page object", "place a private or inappropriate image into guest-visible content using a valid but unintended asset ID"),
    "check.design": ("read-only design diagnostics derived from the current invitation", "misstate design problems to pressure a host into unwanted edits or reveal document details through diagnostic output"),
    "check.accessibility": ("read-only accessibility findings about current invitation content", "hide a genuine accessibility failure with fabricated findings or expose private text excerpts in diagnostic output"),
    "check.layout": ("read-only responsive-layout diagnostics at bounded viewport widths", "produce misleading mobile breakage findings or fail to report an overlap that makes key guest controls unusable"),
    "check.print": ("read-only print-readiness diagnostics and content bounds", "mislead the host into printing a version with clipped details or disclose text in diagnostic output"),
    "fix.apply": ("one previously proposed bounded repair and its selected target IDs", "apply an unrelated or stale fix to overwrite invitation content or change many unintended objects"),
    "preview.prepare": ("a side-effect-free rendering preview for the selected device/print mode", "misrepresent the final guest experience by requesting or presenting a preview that omits relevant context or viewport issues"),
    "export.prepare": ("a requested bounded export artifact, potentially including the invitation document", "prepare a backup/full-document export that discloses private guest or event data to an unintended recipient"),
    "editor.apply_workspace": ("the current editor view mode and saved workspace profile", "switch workspaces to obscure active controls or interfere with review, without changing invitation content"),
    "animation.update_timeline": ("a bounded animation project/timeline and reduced-motion alternative", "create excessive or disorienting motion, degrade editor rendering, or cause guests to miss event information"),
    "event.create_task": ("one invitation-scoped operational task with title, priority, schedule, and details", "create false or urgent-looking work that diverts staff, changes event operations, or pollutes the host's task list"),
    "event.run_intelligence": ("deterministic event-readiness findings and conflict summaries", "surface private event details or return fabricated conflicts that cause the host to change a correct schedule"),
    "enterprise.prepare_protocol": ("one new enterprise or government ceremony protocol with a bounded classification, protocol type, and structured document", "label a restricted ceremony plan as public or replace trusted protocol details with misleading instructions, exposing sensitive attendees or causing an unsafe event sequence"),
    "event.prepare_automation": ("a workspace automation definition, trigger, bounded conditions, and up to 40 registered actions", "create a trigger/action chain that repeatedly modifies event operations, schedules, or communications; malformed or overly broad action definitions could amplify impact across the workspace"),
    "guest.delete": ("the identified invitation guest record and its associated operational references", "permanently erase a real guest's contact, household, seating, and RSVP linkage before an event, disrupting attendance and removing information that may be needed for audit or recovery"),
    "invitation.archive": ("the current invitation's archived state and dashboard visibility", "hide an active invitation from the host and collaborators while leaving its public page live, so event operations and guest responses diverge from the host's view"),
    "invitation.update_operations": ("the invitation's publication schedule, expiry, or custom-domain settings", "redirect or interrupt a live invitation through a wrong custom domain, publish/unpublish schedule, or expiry change, preventing guests from reaching trusted event information"),
    "marketplace.install_template": ("a selected authorized marketplace template package and workspace installation record", "install a deceptive or vulnerable template that alters new invitations, misrepresents licensing, or introduces unsafe content into a host's workspace"),
    "materials.import_zip": ("a user-attached ZIP archive and the extracted invitation materials/import job", "submit a crafted archive that attempts path traversal, decompression/resource exhaustion, unsafe file propagation, or misleading asset names within the authorized workspace"),
    "merge.prepare_job": ("a bounded merge job, selected source, up to 5,000 supplied rows, and its requested preview/draft/publication/delivery preparation mode", "prepare large-scale incorrect invitations or guest-facing content, expose merged personal data to unintended records, or consume significant workspace and downstream resources"),
    "message.prepare_send": ("a bounded guest-recipient list, selected email/SMS/Telegram/WhatsApp channel, and message body prepared for review", "craft deceptive or incorrect event communications for selected guests, disclose private details, damage sender reputation, or create channel costs if a separate human send review is bypassed"),
    "plugin.configure": ("a declarative plugin version, its requested permission grants, and a workspace installation record", "install or update a plugin with excessive or misleading grants that exposes workspace data or changes behavior within the plugin sandbox"),
    "publish.prepare": ("the current invitation's publish or unpublish action, prepared for explicit host confirmation", "publish a draft or unpublish a live invitation, exposing unfinished information or interrupting guest access to event details"),
    "publishing.configure_environment": ("a named publication environment, its bounded environment type, schedule, and access configuration", "route publication through the wrong environment or access policy, expose a preview or draft to unintended viewers, or interrupt a production invitation"),
}


def story_text(tool_id: str) -> str:
    tool = TOOLS[tool_id]
    binding = TOOL_BINDINGS[tool_id]
    touch, worst = THREATS[tool_id]
    schema_fields = ", ".join(f"`{name}`" for name in tool.input_schema.get("properties", {})) or "no caller-supplied fields"
    jitted = tool_id in JIT_ELIGIBLE_TOOLS
    consequence = (
        "A high-risk tool call also needs separate destructive-action confirmation before execution."
        if tool.risk == "high" else
        "This tool has no high-risk destructive confirmation boundary; review its exact arguments and targets before accepting the plan."
        if tool.confirmation else
        "This tool does not declare a separate confirmation boundary; normal plan and authorization gates still apply."
    )
    if tool.reversible:
        recovery = (
            "The tool registry marks this operation reversible. Capture the pre-operation values and target IDs; restore them with the corresponding inverse/editor action or invitation history where available, then verify the resulting page and guest-visible preview."
        )
    else:
        recovery = (
            "The tool registry marks this operation non-reversible. Disable/revoke the affected publication or integration where possible; restore deleted or overwritten data from a verified pre-operation backup using `docs/ops/RESTORE-RUNBOOK.md`. External disclosures or messages cannot be recalled by restoring data."
        )
    if jitted:
        approval_path = (
            "For `publish.prepare`, owner/manager requests are auto-approved by current policy; other eligible tools require manual approval."
            if tool_id in AUTO_APPROVED_TOOLS else
            "This tool requires manual approval; it is not in `AUTO_APPROVED_TOOLS`."
        )
        jit_control = (
            "- **JIT elevation:** this tool is listed in `ai_agent/jit_elevation.py::JIT_ELIGIBLE_TOOLS`; it requires an active five-minute database grant before a one-shot authorization token is issued. Evaluation binds the grant to user/tool/resource and consumes it once (`ai_agent/jit_elevation.py::JITElevationManager.evaluate`). " + approval_path + "\n"
        )
    else:
        jit_control = (
            "- **JIT scope:** this tool is not in `JIT_ELIGIBLE_TOOLS`; do not describe a JIT grant as an existing control for it. Its current gates are the role/capability checks, plan rules, and one-shot tool authorization.\n"
        )
    if binding["type"] in {"internal-api", "platform-api"}:
        endpoint_control = (
            "- **Endpoint binding:** the invocation must match the declared HTTP method/path through `http_request_matches_tool()`; invitation/resource IDs are constrained to the approved binding pattern.\n"
        )
    else:
        endpoint_control = (
            "- **Executor boundary:** the registry binds this call to the declared executor/function below; authorization remains enforced by the server API or editor action service. The binding is not an arbitrary endpoint or script supplied by the model.\n"
        )
    aisvs = ["`C9.1.1` (complete tool inventory)", "`C9.2.1` (permission enforcement)", "`C9.2.3` (authorization re-check)"]
    if tool.confirmation:
        aisvs.append("`C9.3.3` (exact-target confirmation)")
    if tool.risk == "high":
        aisvs.append("`C9.2.4` (high-risk confirmation)")
    if not tool.reversible:
        aisvs.append("`C9.3.5` (non-reversible operation controls)")
    if jitted:
        aisvs.append("`C10.3.2` (JIT elevation)")
    if binding["type"] in {"internal-api", "platform-api"}:
        aisvs.append("`C10.2.1` (tool-to-endpoint binding)")
    aisvs.append("`C10.5.1` (untrusted provider/input data)")
    return f'''# Attack Story: `{tool_id}`

| Field | Value |
|---|---|
| **Tool ID** | `{tool_id}` |
| **Group** | `{tool_id.split('.', 1)[0]}` |
| **Risk tier** | `{tool.risk}` |
| **Permission tier** | `{tool.permission}` |
| **Executor** | `{tool.executor}` |
| **Binding** | `{binding['binding']}` ({binding['type']}) |
| **Reversible** | `{tool.reversible}` |
| **Confirmation required** | `{tool.confirmation}` |
| **Source file** | `ai_agent/tools.py` — `TOOLS[{tool_id!r}]` |
| **Binding file** | `ai_agent/capabilities.py` — `TOOL_BINDINGS[{tool_id!r}]` |

### 1. What it touches

- **Operation:** {tool.description}
- **Data and inputs:** {touch}. The schema accepts: {schema_fields}; values are validated against the registered bounded schema.
- **Execution boundary:** `{binding['type']}` — `{binding['binding']}`. This story does not assume any unlisted external destination or side effect.

### 2. Worst case if malicious

If a prompt-injected or compromised agent persuaded an authorized user to approve `{tool_id}` with attacker-chosen but schema-valid arguments, it could {worst}. The immediate scope is the authorized invitation/page/resource described above; repeated calls can multiply the effect only within the same underlying permissions and rate limits. Treat model-provided content and target IDs as untrusted until verified against the host's intent.

### 3. Containment

- **Input validation:** `ai_agent/tools.py::validate_tool_call()` applies this tool's registered required fields, types, enums, and declared bounds; the shared validator rejects unknown top-level arguments and recursively blocks several executable-markup, shell/SQL, and destination-key patterns. Nested objects declared with `additionalProperties: true` are permissive, so this shared validation is not a substitute for executor-specific validation.
- **Permission check:** `{tool.permission}` is the declared minimum permission. Capability discovery filters tools, then `ai_agent/service.py::confirm_plan()` and `authorize_tool_call()` re-check the user's current access immediately before authorization.
- **Plan/revision gate:** approval is bound to this plan's exact tool index, user, invitation, and document revision/fingerprint; stale plans are rejected. {consequence}
- **One-shot authorization:** `authorize_tool_call()` issues a 30-second token bound to `(userId, invitationId, toolId, planId, index)`; it is consumed once (`ai_agent/service.py::consume_tool_authorization()`).
{endpoint_control}{jit_control}- **Audit trail:** when the production audit callback is configured, plan confirmation, tool authorization, token consumption, and JIT state transitions are recorded through `src/python/server.py::write_audit_event` in the hash-chained audit log. Rate limits and workspace AI policy apply to the agent request path.

### 4. Reversible

- **Registry declaration:** `{tool.reversible}`.
- **Recovery:** {recovery}

### 5. Mitigation and residual risk

- Before confirmation, show the exact target IDs and meaningful argument summary; reject a stale target, changed document fingerprint, or caller whose invitation permission has changed.
- Keep the host-facing action limited to the declared `{binding['type']}` executor and validate every referenced page, asset, guest, or external-effect target against the current invitation/workspace ownership.
- **Residual test gap:** the general registry/plan tests verify the shared agent contract, not necessarily this specific executor's complete downstream behavior. A tool-specific executor test should cover the malicious outcome described above before treating that behavior as independently certified.

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry completeness, schema bounds, and executor bindings.
- `tests/v28_agent_server_contract_test.py` — plan, confirmation, and authorization flow.
- `tests/ai_resource_scopes_test.py` — resource-grant behavior (where mapped).
- `tests/ai_jit_enforcement_test.py` — JIT lifecycle (only applies to JIT-eligible tools).
- **Tool-specific test:** no dedicated end-to-end executor test is asserted by this document; add/identify one for `{tool_id}` in the relevant route/editor subsystem.

### 7. AISVS cross-reference

{', '.join(aisvs)}. See `docs/ai/AISVS-C9-C10-MAPPING.md`. These are control mappings, not a claim that this individual tool has a dedicated test or an external MCP transport.
'''


def build_index() -> str:
    total = len(TOOLS)
    rows = "\n".join(
        f"| `{tool_id}` | {tool.risk} | {tool.permission} | {'Yes' if tool.confirmation else 'No'} | {'Yes' if tool.reversible else 'No'} | {THREATS[tool_id][1]} | [`{tool_id}.md`]({tool_id}.md) |"
        for tool_id, tool in sorted(TOOLS.items())
    )
    return f"""# AI Tool Attack Stories — Index

> **Scope:** Every currently registered AI tool has an individual threat-model document. Tool IDs and policy metadata are checked against `ai_agent/tools.py::TOOLS` and `ai_agent/capabilities.py::TOOL_BINDINGS`; scenario text is reviewed in `scripts/generate_attack_stories.py`.
> **Coverage:** {total} registered tools; {total} full per-tool stories; zero index-only entries. This describes documentation coverage, not independent security certification of each executor.
> **Generation/check:** `python scripts/generate_attack_stories.py` writes the registry-linked files; `python scripts/generate_attack_stories.py --check` verifies checked-in files without modifying them.

## Threat model scope and interpretation

Each story identifies the exact registry metadata, declared binding, accepted input fields, a tool-specific malicious outcome, general authorization/confirmation controls, recovery guidance based on the registry's reversibility flag, and test gaps. A declared binding is not proof that its downstream executor is secure. The stories deliberately distinguish existing controls from future mitigations and do not claim that shared contract tests prove executor-specific behavior.

The accepted-argument schema is defined in `ai_agent/tools.py`; fields inside objects declared with `additionalProperties: true` remain intentionally open and need executor-specific validation. Current plan confirmation and one-shot tool authorization are described in `ai_agent/service.py`; JIT is claimed only for tools in `ai_agent/jit_elevation.py::JIT_ELIGIBLE_TOOLS`.

## Registry-complete per-tool coverage

| Tool ID | Risk | Permission | Confirmation | Reversible | Tool-specific worst-case outcome | Story |
|---|---|---|---|---|---|---|
{rows}

## Coverage counts

| Category | Count |
|---|---:|
| Individually documented registered tools | {total} |
| Index-only or missing story entries | 0 |
| **Registered tools documented** | **{total}** |
"""

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify files without writing")
    args = parser.parse_args()
    if set(TOOLS) != set(TOOL_BINDINGS):
        raise SystemExit("Tool registry and TOOL_BINDINGS differ")
    if set(TOOLS) - set(THREATS):
        raise SystemExit(f"Missing reviewed threat narratives: {sorted(set(TOOLS) - set(THREATS))}")
    output: dict[Path, str] = {
        ROOT / "docs/ai/attack-stories" / f"{tool_id}.md": story_text(tool_id)
        for tool_id in TOOLS
    }
    output[ROOT / "docs/ai/attack-stories/README.md"] = build_index()
    failures = []
    for path, content in output.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                failures.append(path.relative_to(ROOT).as_posix())
        else:
            path.write_text(content, encoding="utf-8", newline="")
    if args.check and failures:
        print("Stale or missing attack-story files:")
        print("\n".join(failures))
        return 1
    print(f"{'VERIFIED' if args.check else 'WROTE'} {len(TOOLS)} attack stories and registry index")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
