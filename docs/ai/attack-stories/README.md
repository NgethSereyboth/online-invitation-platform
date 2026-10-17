# AI Tool Attack Stories — Index

> **Scope:** Every currently registered AI tool has an individual threat-model document. Tool IDs and policy metadata are checked against `ai_agent/tools.py::TOOLS` and `ai_agent/capabilities.py::TOOL_BINDINGS`; scenario text is reviewed in `scripts/generate_attack_stories.py`.
> **Coverage:** 80 registered tools; 80 full per-tool stories; zero index-only entries. This describes documentation coverage, not independent security certification of each executor.
> **Generation/check:** `python scripts/generate_attack_stories.py` writes the registry-linked files; `python scripts/generate_attack_stories.py --check` verifies checked-in files without modifying them.

## Threat model scope and interpretation

Each story identifies the exact registry metadata, declared binding, accepted input fields, a tool-specific malicious outcome, general authorization/confirmation controls, recovery guidance based on the registry's reversibility flag, and test gaps. A declared binding is not proof that its downstream executor is secure. The stories deliberately distinguish existing controls from future mitigations and do not claim that shared contract tests prove executor-specific behavior.

The accepted-argument schema is defined in `ai_agent/tools.py`; fields inside objects declared with `additionalProperties: true` remain intentionally open and need executor-specific validation. Current plan confirmation and one-shot tool authorization are described in `ai_agent/service.py`; JIT is claimed only for tools in `ai_agent/jit_elevation.py::JIT_ELIGIBLE_TOOLS`.

## Registry-complete per-tool coverage

| Tool ID | Risk | Permission | Confirmation | Reversible | Tool-specific worst-case outcome | Story |
|---|---|---|---|---|---|---|
| `account.read_usage` | low | read | No | Yes | expose account-plan or usage information to a different account if identity scoping is bypassed | [`account.read_usage.md`](account.read_usage.md) |
| `analytics.read_summary` | low | read | No | Yes | infer attendance, guest activity, or event timing from analytics and expose it outside the authorized host workflow | [`analytics.read_summary.md`](analytics.read_summary.md) |
| `animation.update_timeline` | medium | edit | No | Yes | create excessive or disorienting motion, degrade editor rendering, or cause guests to miss event information | [`animation.update_timeline.md`](animation.update_timeline.md) |
| `asset.insert` | medium | edit | No | Yes | place a private or inappropriate image into guest-visible content using a valid but unintended asset ID | [`asset.insert.md`](asset.insert.md) |
| `asset.search` | low | read | No | Yes | enumerate private asset metadata or surface an unrelated tenant's materials through an authorization-scope failure | [`asset.search.md`](asset.search.md) |
| `check.accessibility` | low | read | No | Yes | hide a genuine accessibility failure with fabricated findings or expose private text excerpts in diagnostic output | [`check.accessibility.md`](check.accessibility.md) |
| `check.design` | low | read | No | Yes | misstate design problems to pressure a host into unwanted edits or reveal document details through diagnostic output | [`check.design.md`](check.design.md) |
| `check.layout` | low | read | No | Yes | produce misleading mobile breakage findings or fail to report an overlap that makes key guest controls unusable | [`check.layout.md`](check.layout.md) |
| `check.print` | low | read | No | Yes | mislead the host into printing a version with clipped details or disclose text in diagnostic output | [`check.print.md`](check.print.md) |
| `design.analyze_reference` | low | edit | No | Yes | plant attacker-influenced visual guidance in a blueprint that later steers the host toward deceptive branding or unsafe layout changes | [`design.analyze_reference.md`](design.analyze_reference.md) |
| `design.apply_blueprint` | medium | edit | No | Yes | apply an unexpected design across the invitation or create a misleading new project under a trusted host account | [`design.apply_blueprint.md`](design.apply_blueprint.md) |
| `editor.apply_workspace` | low | edit | No | Yes | switch workspaces to obscure active controls or interfere with review, without changing invitation content | [`editor.apply_workspace.md`](editor.apply_workspace.md) |
| `enterprise.prepare_protocol` | medium | manage | Yes | Yes | label a restricted ceremony plan as public or replace trusted protocol details with misleading instructions, exposing sensitive attendees or causing an unsafe event sequence | [`enterprise.prepare_protocol.md`](enterprise.prepare_protocol.md) |
| `event.configure_details` | medium | edit | No | Yes | replace the destination map or venue address with an attacker-controlled location or create conflicting English and Khmer details | [`event.configure_details.md`](event.configure_details.md) |
| `event.create_task` | low | edit | No | Yes | create false or urgent-looking work that diverts staff, changes event operations, or pollutes the host's task list | [`event.create_task.md`](event.create_task.md) |
| `event.prepare_automation` | high | manage | Yes | No | create a trigger/action chain that repeatedly modifies event operations, schedules, or communications; malformed or overly broad action definitions could amplify impact across the workspace | [`event.prepare_automation.md`](event.prepare_automation.md) |
| `event.run_intelligence` | low | read | No | Yes | surface private event details or return fabricated conflicts that cause the host to change a correct schedule | [`event.run_intelligence.md`](event.run_intelligence.md) |
| `event.update_fields` | medium | edit | No | Yes | change the couple's names, date, venue, or other invitation facts and leave guests relying on false event details | [`event.update_fields.md`](event.update_fields.md) |
| `event.update_schedule` | medium | edit | No | Yes | replace ceremony times, locations, or sequence so guests arrive at the wrong time or miss key parts of the event | [`event.update_schedule.md`](event.update_schedule.md) |
| `export.prepare` | medium | edit | Yes | Yes | prepare a backup/full-document export that discloses private guest or event data to an unintended recipient | [`export.prepare.md`](export.prepare.md) |
| `fix.apply` | medium | edit | No | Yes | apply an unrelated or stale fix to overwrite invitation content or change many unintended objects | [`fix.apply.md`](fix.apply.md) |
| `gallery.arrange` | medium | edit | No | Yes | reorder or crowd photos so a host-approved image is obscured or a misleading gallery presentation appears in the published invitation | [`gallery.arrange.md`](gallery.arrange.md) |
| `guest.check_in` | medium | manage | Yes | Yes | falsely mark a guest checked in or absent, disrupting arrival counts and event operations | [`guest.check_in.md`](guest.check_in.md) |
| `guest.create` | medium | manage | Yes | Yes | add an attacker-controlled email/phone recipient to guest communications or consume guest capacity with fabricated records | [`guest.create.md`](guest.create.md) |
| `guest.delete` | high | manage | Yes | No | permanently erase a real guest's contact, household, seating, and RSVP linkage before an event, disrupting attendance and removing information that may be needed for audit or recovery | [`guest.delete.md`](guest.delete.md) |
| `guest.read_delivery_status` | low | manage | No | Yes | expose guest contact/delivery outcomes or reveal which recipients have not received the invitation | [`guest.read_delivery_status.md`](guest.read_delivery_status.md) |
| `guest.update` | medium | manage | Yes | Yes | redirect a real guest's communications to an attacker, alter their seating assignment, or change their household association | [`guest.update.md`](guest.update.md) |
| `image.configure_frame` | low | edit | No | Yes | crop a person, logo, or safety-relevant image detail out of view or apply a misleading focal crop | [`image.configure_frame.md`](image.configure_frame.md) |
| `invitation.archive` | high | manage | Yes | Yes | hide an active invitation from the host and collaborators while leaving its public page live, so event operations and guest responses diverge from the host's view | [`invitation.archive.md`](invitation.archive.md) |
| `invitation.configure_opening` | medium | edit | No | Yes | replace the opening with deceptive event framing or make the experience difficult to skip for guests using assistive technology | [`invitation.configure_opening.md`](invitation.configure_opening.md) |
| `invitation.configure_rsvp` | medium | manage | Yes | Yes | disable responses before guests reply, or enable an unreviewed collection point during an active event | [`invitation.configure_rsvp.md`](invitation.configure_rsvp.md) |
| `invitation.update_operations` | high | manage | Yes | Yes | redirect or interrupt a live invitation through a wrong custom domain, publish/unpublish schedule, or expiry change, preventing guests from reaching trusted event information | [`invitation.update_operations.md`](invitation.update_operations.md) |
| `marketplace.install_template` | medium | manage | Yes | Yes | install a deceptive or vulnerable template that alters new invitations, misrepresents licensing, or introduces unsafe content into a host's workspace | [`marketplace.install_template.md`](marketplace.install_template.md) |
| `materials.classify` | low | edit | No | Yes | bulk-misclassify invitation assets so unsafe or private files appear as approved, public-ready materials | [`materials.classify.md`](materials.classify.md) |
| `materials.create_folder` | low | edit | No | Yes | create a confusing or excessive folder hierarchy that hides assets or consumes database/management capacity | [`materials.create_folder.md`](materials.create_folder.md) |
| `materials.find_duplicates` | low | read | No | Yes | use duplicate reports to infer private uploads or create a misleading cleanup recommendation that leads the host to remove the wrong asset | [`materials.find_duplicates.md`](materials.find_duplicates.md) |
| `materials.import_folder` | medium | edit | Yes | Yes | abuse crafted names or deeply nested batches to create path confusion, resource exhaustion, or unauthorized material placement | [`materials.import_folder.md`](materials.import_folder.md) |
| `materials.import_zip` | medium | edit | Yes | Yes | submit a crafted archive that attempts path traversal, decompression/resource exhaustion, unsafe file propagation, or misleading asset names within the authorized workspace | [`materials.import_zip.md`](materials.import_zip.md) |
| `materials.insert_into_page` | medium | edit | No | Yes | insert a private, unreviewed, or incorrectly described asset where invitees can see it | [`materials.insert_into_page.md`](materials.insert_into_page.md) |
| `materials.list_folders` | low | read | No | Yes | disclose private asset names or organizational structure from a project to an unauthorized user | [`materials.list_folders.md`](materials.list_folders.md) |
| `materials.move` | low | edit | No | Yes | move an asset out of the folder where a host expects it, hiding it from review or causing the wrong asset to be selected | [`materials.move.md`](materials.move.md) |
| `materials.rename` | low | edit | No | Yes | rename a harmful or private asset to impersonate an approved logo, invite image, or consent document | [`materials.rename.md`](materials.rename.md) |
| `materials.update_metadata` | medium | edit | Yes | Yes | mislabel or hide an asset from the host's review while leaving its underlying content unchanged | [`materials.update_metadata.md`](materials.update_metadata.md) |
| `merge.prepare_job` | high | manage | Yes | No | prepare large-scale incorrect invitations or guest-facing content, expose merged personal data to unintended records, or consume significant workspace and downstream resources | [`merge.prepare_job.md`](merge.prepare_job.md) |
| `message.prepare_send` | high | manage | Yes | No | craft deceptive or incorrect event communications for selected guests, disclose private details, damage sender reputation, or create channel costs if a separate human send review is bypassed | [`message.prepare_send.md`](message.prepare_send.md) |
| `object.create_image` | medium | edit | No | Yes | insert an inappropriate, deceptive, or privacy-sensitive image into the invitation, or attempt to reference an asset outside the authorized project | [`object.create_image.md`](object.create_image.md) |
| `object.create_shape` | low | edit | No | Yes | obscure a disclaimer, RSVP control, or event detail with a large or high-contrast shape before the host notices the design change | [`object.create_shape.md`](object.create_shape.md) |
| `object.create_text` | low | edit | No | Yes | insert misleading RSVP instructions, defamatory text, or a phishing URL-like string that changes what guests see when the invitation is published | [`object.create_text.md`](object.create_text.md) |
| `object.delete` | high | edit | Yes | Yes | remove the invitation title, RSVP directions, accessibility content, or a host's authored design; repeated authorized plans could compound the loss | [`object.delete.md`](object.delete.md) |
| `object.duplicate` | low | edit | No | Yes | duplicate costly or sensitive objects repeatedly to bloat the document, exhaust storage limits, or create confusing near-identical content | [`object.duplicate.md`](object.duplicate.md) |
| `object.update` | low | edit | No | Yes | replace text, geometry, visibility, or style with deceptive content or move critical invitation information off-canvas | [`object.update.md`](object.update.md) |
| `page.configure_style` | medium | edit | No | Yes | configure a distracting transition or inaccessible background that conceals text or causes motion discomfort for guests | [`page.configure_style.md`](page.configure_style.md) |
| `page.create` | medium | edit | No | Yes | add a page with deceptive or unfinished content that later becomes publicly visible when the invitation is published | [`page.create.md`](page.create.md) |
| `page.duplicate` | medium | edit | No | Yes | duplicate private or obsolete content into a new page that is accidentally left visible to invitees | [`page.duplicate.md`](page.duplicate.md) |
| `page.rename` | low | edit | No | Yes | rename pages to mislead the host about which content is being reviewed or published | [`page.rename.md`](page.rename.md) |
| `page.reorder` | medium | edit | No | Yes | move obsolete, draft, or misleading content into the first guest-visible position | [`page.reorder.md`](page.reorder.md) |
| `photo.remove_background` | medium | edit | Yes | Yes | create and insert a misleading derivative of a person's photograph or consume local processing/storage resources without informed review | [`photo.remove_background.md`](photo.remove_background.md) |
| `plugin.configure` | high | manage | Yes | No | install or update a plugin with excessive or misleading grants that exposes workspace data or changes behavior within the plugin sandbox | [`plugin.configure.md`](plugin.configure.md) |
| `preview.prepare` | low | read | No | Yes | misrepresent the final guest experience by requesting or presenting a preview that omits relevant context or viewport issues | [`preview.prepare.md`](preview.prepare.md) |
| `publish.prepare` | high | manage | Yes | No | publish a draft or unpublish a live invitation, exposing unfinished information or interrupting guest access to event details | [`publish.prepare.md`](publish.prepare.md) |
| `publishing.configure_environment` | high | manage | Yes | No | route publication through the wrong environment or access policy, expose a preview or draft to unintended viewers, or interrupt a production invitation | [`publishing.configure_environment.md`](publishing.configure_environment.md) |
| `read.page_summary` | low | read | No | Yes | choose a page containing private notes or sensitive event details and cause them to be included in model context or returned to a user without page-level authorization | [`read.page_summary.md`](read.page_summary.md) |
| `read.project_summary` | low | read | No | Yes | use an unauthorized read to expose guest-facing event details, draft content, or scheduling information to a caller or provider that should not receive it | [`read.project_summary.md`](read.project_summary.md) |
| `read.selection_summary` | low | read | No | Yes | select a text object containing a private address, access code, or personal detail and exfiltrate that content through a later prompt or provider | [`read.selection_summary.md`](read.selection_summary.md) |
| `rich_text.replace` | low | edit | No | Yes | silently replace invitation wording, Khmer translations, dates, or accessibility text while preserving formatting that makes the altered text look authentic | [`rich_text.replace.md`](rich_text.replace.md) |
| `rsvp.update` | medium | manage | Yes | Yes | change a guest's acceptance to decline or inflate attendance so the host makes incorrect catering and seating decisions | [`rsvp.update.md`](rsvp.update.md) |
| `selection.select_layers` | low | edit | No | Yes | select an unintended set of layers to mislead a host about which objects a later edit or confirmation will affect | [`selection.select_layers.md`](selection.select_layers.md) |
| `style.apply_brand_kit` | medium | edit | No | Yes | apply the wrong organization's colors or marks, impersonating another event host or undermining brand trust | [`style.apply_brand_kit.md`](style.apply_brand_kit.md) |
| `style.apply_palette` | medium | edit | No | Yes | apply a low-contrast palette that makes RSVP controls or important text unreadable across the invitation | [`style.apply_palette.md`](style.apply_palette.md) |
| `style.apply_photo` | low | edit | No | Yes | distort or darken a person or venue image enough to mislead guests or harm the host's reputation | [`style.apply_photo.md`](style.apply_photo.md) |
| `style.apply_text_style` | low | edit | No | Yes | apply a low-contrast or tiny style to event details, Khmer text, or safety instructions while leaving content technically present | [`style.apply_text_style.md`](style.apply_text_style.md) |
| `transform.align` | low | edit | No | Yes | rearrange a group so the visual hierarchy hides a date change, consent language, or important host-provided details | [`transform.align.md`](transform.align.md) |
| `transform.arrange` | low | edit | No | Yes | place a covering object above an RSVP button, notice, or event detail to hide or misrepresent it | [`transform.arrange.md`](transform.arrange.md) |
| `transform.distribute` | low | edit | No | Yes | spread a related set of labels and controls apart, causing text to appear associated with the wrong date, venue, or response option | [`transform.distribute.md`](transform.distribute.md) |
| `transform.group` | low | edit | No | Yes | group unrelated content so later movement or deletion affects labels, decorations, and event details together | [`transform.group.md`](transform.group.md) |
| `transform.move` | low | edit | No | Yes | move a venue, date, RSVP link, or disclosure outside the visible canvas so guests miss essential event information | [`transform.move.md`](transform.move.md) |
| `transform.resize` | low | edit | No | Yes | shrink essential text or enlarge a decorative layer over the event details, making the invitation misleading or unusable | [`transform.resize.md`](transform.resize.md) |
| `transform.rotate` | low | edit | No | Yes | rotate key wording or controls until they are unreadable or overlap other invitation content | [`transform.rotate.md`](transform.rotate.md) |
| `transform.tidy` | medium | edit | No | Yes | reflow a carefully composed invitation into overlapping or misleading groupings that a host may accept as a routine cleanup | [`transform.tidy.md`](transform.tidy.md) |
| `transform.ungroup` | low | edit | No | Yes | break a carefully constrained layout apart so related elements can be independently displaced or altered | [`transform.ungroup.md`](transform.ungroup.md) |

## Coverage counts

| Category | Count |
|---|---:|
| Individually documented registered tools | 80 |
| Index-only or missing story entries | 0 |
| **Registered tools documented** | **80** |
