# Khmer translation map — eInvite / OKID (2026-10-24)

**Purpose:** the Khmer text for every English-only (`fallback`) string in `docs/i18n/TRANSLATIONS.csv`, the strings
that are damaged (foreign-script or Latin letters inside Khmer words), the wrongly translated rail labels, the
admin feature-flag strings (OD-8), the dashboard strings that are still English, and the new brand strings.
Used by work item **FB-54** of `FREEBUFF-REFINEMENT-ORDER-ROUND4-2026-10-23.md`.

**Authorship and status:** the owner approved on 2026-10-24 that Claude drafts this Khmer and the agent applies it.
Claude is not a native Khmer speaker. Every string below is standard-Khmer UI wording, consistent with the terms
already used in the product, but it is a **draft for native review before public launch**. The agent does not review
or rewrite it; it applies it exactly and lists every applied string in `docs/i18n/KHMER-REVIEW-QUEUE.md`.

## 0. How the agent must use this file (hard rules)

1. **Paste, never generate.** The Khmer comes from the `KM` column of this file only. Parse the tables with a script
   (read the file as UTF-8, split each table row on ` | `) and write the strings into source with a script.
   Do not retype Khmer by hand, do not "improve" it, do not translate anything that is not in this file.
2. **Match before replacing.** For each row, the `EN` column must equal the source English **after trimming** and
   after decoding JS escapes. If it does not match, skip the row and list it under "Mismatches" in the evidence.
   Preserve the source's own leading/trailing spaces and punctuation spacing (e.g. `"Version history — "`,
   `"Password changed successfully. "`): trim only for the comparison, never in the written value.
3. **Keep placeholders exactly:** `%d`, `{days}`, `{error}`, `→`, `—`, `…`, `+`, `(px)`. The set of placeholders in
   KM must equal the set in EN. Never add or remove one.
4. **Keep Latin where this file keeps it:** `RSVP`, `QR`, `SMTP`, `API`, `AI`, `IP`, `MFA`, `Redis`, `Webhook`,
   `Visa`, `Mastercard`, `Passkey`, `px`, and digits. These are separate tokens, always surrounded by a space or
   punctuation. A Latin letter directly touching a Khmer **letter or vowel/sign mark** inside one word is always an error
   (see FB-54 check 4). Khmer punctuation (`។` `៖`) is not a letter: `Passkey។` is fine.
5. **Keys vs labels.** Only visible labels change. Never change a `value=""`, an object key, a CSS class, a
   `localStorage` key (`einvite-lang`), a route, an API field, or an `EINVITE_*` setting.
6. **Where each row lives.** The `file` is the heading above the table. Match rows by `(file, EN)`; apply to every
   occurrence of that English string in that file whose km argument is currently identical to the English
   (`fallback`). Shapes: `_txt(en, km)`, `_html(en, km)`, `b(en, km)`, `langText(en, km)`, `STRINGS.km.<key>`, and
   `<span class="i18n-km">…</span>` or `data-km` / `data-i18n-km` in `src/html`. Edit `src/` only, never
   `src/python/build/*` mirrors or `bundle-*` files (rebuild with `python3 build.py all`).
7. **Do not touch** `docs/i18n/TRANSLATIONS.csv` by hand. Regenerate it with the repo's reconcile tools
   (`tools/i18n-reconcile-csv.py`, `tools/i18n-apply-reconcile.py`): read their usage first. Status of every applied
   row becomes `translated`.
8. **Anything not listed here** stays English; add or keep a `fallback` row. Never invent.

## 1. Term base (use these words for any related row; they match existing translated rows)

| EN | KM | Notes |
|---|---|---|
| Invitation | ការអញ្ជើញ | existing |
| Guest / Guests | ភ្ញៀវ | existing |
| Guest list | បញ្ជីភ្ញៀវ | existing correct form (guests.html) |
| Template(s) | គំរូ | draft; admin.html still has `ពុម្ពអត្ថបទ`: see OD-20 |
| Materials | សម្ភារៈ | fixes damaged `សម្ភារែ` |
| Responses | ការឆ្លើយតប | fixes damaged `បញ្ចូលទា` |
| Analytics | ការវិភាគ | fixes damaged `វិភានសម្តែង` |
| Dashboard | ផ្ទាំងគ្រប់គ្រង | |
| Account | គណនី | |
| Plan | គម្រោង | existing |
| Save / Cancel / Delete | រក្សាទុក / បោះបង់ / លុប | existing |
| Edit | កែប្រែ | existing |
| Remove | យកចេញ | existing |
| Copy / Duplicate | ចម្លង | existing |
| Restore | ស្ដារ | existing |
| Preview | មើលជាមុន | existing |
| Publish | ផ្សព្វផ្សាយ | |
| Version | កំណែ | existing |
| Settings | ការកំណត់ | existing |
| Checked in / Check in | បានចុះឈ្មោះចូល / ចុះឈ្មោះចូល | |
| Attending / Declined / Pending / Maybe | នឹងចូលរួម / បដិសេធ / កំពុងរង់ចាំ / ប្រហែល | |
| Password | ពាក្យសម្ងាត់ | |
| Link | តំណ | |
| Server (app server) | ម៉ាស៊ីនបម្រើ | |
| Marketplace | ទីផ្សារ | |

## 2. Brand (FB-55)

| Where | EN | KM |
|---|---|---|
| Full product name (page `<title>`, meta, manifest `name`, `og:site_name`, auth pages, footer, About) | OKID-Online Khmer Invitation Design | អូខេអាយឌី |
| Short wordmark (compact headers at 540 px and below) | OKID | អូខេអាយឌី |
| Public invitation footer credit | Created with OKID | បង្កើតដោយ អូខេអាយឌី |

The Khmer long name is **not** provided by the owner. Use `អូខេអាយឌី` everywhere the Khmer brand appears. Do not invent an expansion.

## 3. Repairs of existing damaged or wrong Khmer (replace the whole km value)

Find each existing km text by its **English** row in the file (key shown), replace the entire km value. After the
replacement, delete the three entries from `KNOWN_FOREIGN_SCRIPT_DAMAGE` in `scripts/check-bilingual-consistency.py`.

### `src/js/components/chart.js`  (key `desktop`)
| EN | KM |
|---|---|
| Desktop | កុំព្យូទ័រ |

### `src/js/pages/admin/users.js`  (keys `confirmForceMfa`, `confirmImpersonate`)
| EN | KM |
|---|---|
| Force this user to re-enroll MFA on next login? | បង្ខំអ្នកប្រើនេះឱ្យចុះឈ្មោះ MFA ឡើងវិញនៅពេលចូលគណនីលើកក្រោយឬ? |
| Start an impersonation session as this user? You will be logged in as them for 30 minutes. | ចាប់ផ្ដើមសម័យតំណាងក្នុងនាមអ្នកប្រើនេះឬ? អ្នកនឹងចូលគណនីក្នុងនាមពួកគេរយៈពេល 30 នាទី។ |

### `src/js/pages/admin/impersonate.js`  (key `confirmStart`) — contains Latin letters inside a Khmer word (`សessian`)
| EN | KM |
|---|---|
| Start impersonation session? You will be logged in as this user for 30 minutes. Every action will be audit-logged. | ចាប់ផ្ដើមសម័យតំណាងឬ? អ្នកនឹងចូលគណនីក្នុងនាមអ្នកប្រើនេះរយៈពេល 30 នាទី។ រាល់សកម្មភាពនឹងត្រូវបានកត់ត្រាសម្រាប់ការត្រួតពិនិត្យ។ |

### `src/js/pages/dashboard/analytics.js`  (key `purgeConfirm`)
| EN | KM |
|---|---|
| This permanently deletes every session + event for this invitation. Continue? | នេះនឹងលុបសម័យ និងព្រឹត្តិការណ៍ទាំងអស់សម្រាប់ការអញ្ជើញនេះជាអចិន្ត្រៃយ៍។ បន្តឬ? |

### Wrong rail labels and other wrong terms — exact find → replace across `src/` (not mirrors or bundles)
Grep `src/js`, `src/html` for each **find** string, replace with the **replace** string, and list every hit.
Replace the whole km value only where the English next to it matches the EN column.

| EN | find (existing Khmer) | replace with |
|---|---|---|
| Materials | សម្ភារែ | សម្ភារៈ |
| Stored materials (`designer.js`) | សម្ភារែ | សម្ភារៈដែលបានរក្សាទុក |
| materials (`materials.js`, lowercase) | សម្ភារែ | សម្ភារៈ |
| Responses (`dashboard.js`) | បញ្ចូលទា | ការឆ្លើយតប |
| Analytics (`dashboard.js`) | វិភានសម្តែង | ការវិភាគ |
| Guest list | បញ្ចូលភ្ញៀវ | បញ្ជីភ្ញៀវ |
| New invitation | សំណាងគំរូ | ការអញ្ជើញថ្មី |
| Feature flags (admin tab label, joined text `Feature flagsទងជម្រើសសមុខងារ`) | ទងជម្រើសសមុខងារ | ជម្រើសមុខងារ |

## 4. Admin feature flags (OD-8) — `src/js/pages/admin/feature-flags.js` (`STRINGS.km.<key>`)

| EN | KM |
|---|---|
| Flag | ជម្រើស |
| No flags defined. | មិនមានជម្រើសមុខងារត្រូវបានកំណត់ទេ។ |
| Tier | កម្រិត |
| Save this flag value? | រក្សាទុកតម្លៃជម្រើសនេះឬ? |
| Super-admin access required to modify flags. | ត្រូវការសិទ្ធិអ្នកគ្រប់គ្រងជាន់ខ្ពស់ដើម្បីកែប្រែជម្រើសមុខងារ។ |
| Non-admin session idle window | រយៈពេលទំនេរនៃសម័យសម្រាប់អ្នកមិនមែនអ្នកគ្រប់គ្រង |
| How long a non-admin session may sit idle before it expires. Changing this affects all non-admin users. | រយៈពេលដែលសម័យរបស់អ្នកមិនមែនអ្នកគ្រប់គ្រងអាចទុកចោលទំនេរមុនផុតកំណត់។ ការផ្លាស់ប្ដូរនេះប៉ះពាល់ដល់អ្នកប្រើមិនមែនអ្នកគ្រប់គ្រងទាំងអស់។ |
| Idle window (days) | រយៈពេលទំនេរ (ថ្ងៃ) |
| Save idle window | រក្សាទុករយៈពេលទំនេរ |
| Change the non-admin session idle window to {days} days? | ប្ដូររយៈពេលទំនេរនៃសម័យសម្រាប់អ្នកមិនមែនអ្នកគ្រប់គ្រងទៅ {days} ថ្ងៃឬ? |
| Idle window updated to {days} days. | បានធ្វើបច្ចុប្បន្នភាពរយៈពេលទំនេរទៅ {days} ថ្ងៃ។ |
| Failed to update idle window: {error} | ធ្វើបច្ចុប្បន្នភាពរយៈពេលទំនេរមិនបានសម្រេច៖ {error} |

Also, if still English in the same file (keys `flagSaved`, `saveFailed`):

| EN | KM |
|---|---|
| Flag saved. | បានរក្សាទុកជម្រើស។ |
| Save failed. | រក្សាទុកមិនបានសម្រេច។ |

(Use the source's exact English for these two; if it differs, match by key and keep the meaning, otherwise skip and report.)

## 5. Shared dashboard and editor chrome that is still English (FB-48)

These are visible English strings on the Khmer dashboard. Find them in `src/html/dashboard.html`, `src/js/dashboard*.js`
and shared header code. If they are hard-coded English, wire them through the normal bilingual path
(`.i18n-en` / `.i18n-km` or `langText`) with the English text unchanged and the Khmer from this table.

| EN | KM |
|---|---|
| Designs | ការរចនា |
| Template Studio | ស្ទូឌីយោគំរូ |
| + Create invitation | + បង្កើតការអញ្ជើញ |
| New invitation | ការអញ្ជើញថ្មី |
| Search invitations… | ស្វែងរកការអញ្ជើញ… |
| Guest list | បញ្ជីភ្ញៀវ |
| Materials | សម្ភារៈ |
| Responses | ការឆ្លើយតប |
| Analytics | ការវិភាគ |
| Reply | ឆ្លើយតប |
| Reply to this invitation | ឆ្លើយតបការអញ្ជើញនេះ |

(The last two are the RSVP jump button of FB-56 on the public invitation.)

## 6. The 306 `fallback` rows, by file

For `src/js/guests.js` line 36 only (CSV export headers and values: `Name`, `Phone`, `Email`, `Group`, `Household`,
`Table`, `Seat`, `Tags`, `RSVP status`, `Invitation mode`, `Checked in`, `Delivery`, `Opened`, `Personal link`,
`Pending`, `RSVP disabled`, `Yes`, `No`): first check whether the import path reads those headers back. If yes, leave
those line-36 rows English and list them. If they are display-only, apply the rows below.

### `src/js/guests.js`
| EN | KM |
|---|---|
| Guest management, personal links, QR codes, and check-in require the full application server. | ការគ្រប់គ្រងភ្ញៀវ តំណផ្ទាល់ខ្លួន កូដ QR និងការចុះឈ្មោះចូល ត្រូវការម៉ាស៊ីនបម្រើកម្មវិធីពេញលេញ។ |
| This invitation is not available in the current server context. | ការអញ្ជើញនេះមិនមានក្នុងបរិបទម៉ាស៊ីនបម្រើបច្ចុប្បន្នទេ។ |
| Invited | បានអញ្ជើញ |
| Attending | នឹងចូលរួម |
| Declined | បដិសេធ |
| Pending | កំពុងរង់ចាំ |
| Checked in | បានចុះឈ្មោះចូល |
| Off | បិទ |
| RSVP disabled | បិទ RSVP |
| Awaiting reply | រង់ចាំការឆ្លើយតប |
| Group: | ក្រុម៖ |
| Household: | គ្រួសារ៖ |
| Table: | តុ៖ |
| Seat: | កៅអី៖ |
| at | នៅ |
| RSVP | RSVP |
| Opened | បានបើក |
| Edit | កែប្រែ |
| Link | តំណ |
| Rotate link | ប្ដូរតំណ |
| QR | QR |
| Undo check-in | ដកការចុះឈ្មោះចូលវិញ |
| Check in | ចុះឈ្មោះចូល |
| Remove | យកចេញ |
| No guests match this filter. | គ្មានភ្ញៀវត្រូវនឹងតម្រងនេះទេ។ |
| Guest name | ឈ្មោះភ្ញៀវ |
| Phone number | លេខទូរសព្ទ |
| Email | អ៊ីមែល |
| Group | ក្រុម |
| Household | គ្រួសារ |
| Table | តុ |
| Seat | កៅអី |
| Tags (comma separated) | ស្លាក (ញែកដោយសញ្ញាក្បៀស) |
| Edit guest | កែប្រែភ្ញៀវ |
| Cancel | បោះបង់ |
| Save | រក្សាទុក |
| Remove this guest? | យកភ្ញៀវនេះចេញឬ? |
| Remove guest | យកភ្ញៀវចេញ |
| Optional expiration in days. Leave blank for no expiration. | ចំនួនថ្ងៃផុតកំណត់ (ស្រេចចិត្ត)។ ទុកទទេប្រសិនបើមិនចង់ឱ្យផុតកំណត់។ |
| Rotate personal invitation link | ប្ដូរតំណអញ្ជើញផ្ទាល់ខ្លួន |
| Personal invitation link | តំណអញ្ជើញផ្ទាល់ខ្លួន |
| Expires | ផុតកំណត់ |
| No expiration set | មិនបានកំណត់ការផុតកំណត់ |
| Copy personal link | ចម្លងតំណផ្ទាល់ខ្លួន |
| Revoke link | ដកហូតតំណ |
| Copied! | បានចម្លង! |
| Revoke this personal link? Existing copies and QR codes will stop working. | ដកហូតតំណផ្ទាល់ខ្លួននេះឬ? ច្បាប់ចម្លង និងកូដ QR ដែលមានស្រាប់នឹងឈប់ដំណើរការ។ |
| Revoke personal link | ដកហូតតំណផ្ទាល់ខ្លួន |
| Revoke | ដកហូត |
| QR code | កូដ QR |
| Run the local server to generate a private QR code. | ដំណើរការម៉ាស៊ីនបម្រើក្នុងកុំព្យូទ័រ ដើម្បីបង្កើតកូដ QR ឯកជន។ |
| Download QR | ទាញយក QR |
| QR generation is unavailable. The personal link can still be copied safely. | មិនអាចបង្កើតកូដ QR បានទេ។ នៅតែអាចចម្លងតំណផ្ទាល់ខ្លួនបានដោយសុវត្ថិភាព។ |
| Imported %d guest(s). | បាននាំចូលភ្ញៀវ %d នាក់។ |
| Name | ឈ្មោះ |
| Phone | ទូរសព្ទ |
| Tags | ស្លាក |
| RSVP status | ស្ថានភាព RSVP |
| Invitation mode | របៀបអញ្ជើញ |
| Delivery | ការចែកចាយ |
| Personal link | តំណផ្ទាល់ខ្លួន |
| Yes | បាទ/ចាស |
| No | ទេ |

### `src/js/templates.js`
| EN | KM |
|---|---|
| No templates match these filters | គ្មានគំរូត្រូវនឹងតម្រងទាំងនេះទេ |
| Try another category or template source. | សាកល្បងប្រភេទ ឬប្រភពគំរូផ្សេងទៀត។ |
| Built-in | មានស្រាប់ |
| Marketplace | ទីផ្សារ |
| Your template | គំរូរបស់អ្នក |
| Reusable invitation design | ការរចនាការអញ្ជើញដែលប្រើឡើងវិញបាន |
| Preview | មើលជាមុន |
| Use | ប្រើ |
| Edit design | កែប្រែការរចនា |
| Details | ព័ត៌មានលម្អិត |
| Versions | កំណែ |
| Remove from marketplace | យកចេញពីទីផ្សារ |
| Publish to marketplace | ផ្សព្វផ្សាយទៅទីផ្សារ |
| Duplicate | ចម្លង |
| Loading templates… | កំពុងផ្ទុកគំរូ… |
| Static preview | ការមើលជាមុនឋិតិវន្ត |
| Built-in template preview | ការមើលគំរូដែលមានស្រាប់ជាមុន |
| Creating server invitations, personal templates, marketplace publishing, and version history require the full application server. | ការបង្កើតការអញ្ជើញលើម៉ាស៊ីនបម្រើ គំរូផ្ទាល់ខ្លួន ការផ្សព្វផ្សាយលើទីផ្សារ និងប្រវត្តិកំណែ ត្រូវការម៉ាស៊ីនបម្រើកម្មវិធីពេញលេញ។ |
| Sign in to manage templates | ចូលគណនីដើម្បីគ្រប់គ្រងគំរូ |
| Authentication is required for personal and marketplace templates. | ត្រូវចូលគណនីសម្រាប់គំរូផ្ទាល់ខ្លួន និងគំរូលើទីផ្សារ។ |
| Publish this template to the shared marketplace? Anyone using this server will be able to create invitations from it. | ផ្សព្វផ្សាយគំរូនេះទៅទីផ្សារចែករំលែកឬ? អ្នកប្រើម៉ាស៊ីនបម្រើនេះទាំងអស់នឹងអាចបង្កើតការអញ្ជើញពីគំរូនេះបាន។ |
| Remove this template from the shared marketplace? Existing invitations created from it will not be affected. | យកគំរូនេះចេញពីទីផ្សារចែករំលែកឬ? ការអញ្ជើញដែលបានបង្កើតពីគំរូនេះរួចហើយនឹងមិនរងផលប៉ះពាល់ទេ។ |
| Publish template | ផ្សព្វផ្សាយគំរូ |
| Publish | ផ្សព្វផ្សាយ |
| Remove | យកចេញ |
| Delete template | លុបគំរូ |
| Delete permanently | លុបជាអចិន្ត្រៃយ៍ |
| Name the temporary invitation used to edit this template: | ដាក់ឈ្មោះការអញ្ជើញបណ្ដោះអាសន្នដែលប្រើសម្រាប់កែប្រែគំរូនេះ៖ |
| Choose a name for the new invitation: | ជ្រើសរើសឈ្មោះសម្រាប់ការអញ្ជើញថ្មី៖ |
| Edit template design | កែប្រែការរចនាគំរូ |
| Create from template | បង្កើតពីគំរូ |
| Continue | បន្ត |
| Visual page | ទំព័រការរចនា |
| Current version: | កំណែបច្ចុប្បន្ន៖ |
| Visual pages: | ទំព័រការរចនា៖ |
| Sections: | ផ្នែក៖ |
| Create invitation from this template | បង្កើតការអញ្ជើញពីគំរូនេះ |
| Edit template details | កែប្រែព័ត៌មានលម្អិតរបស់គំរូ |
| Name | ឈ្មោះ |
| Category | ប្រភេទ |
| Wedding | អាពាហ៍ពិពាហ៍ |
| Birthday | ខួបកំណើត |
| Business | អាជីវកម្ម |
| Other | ផ្សេងៗ |
| Description | ការពិពណ៌នា |
| Tags — comma separated | ស្លាក — ញែកដោយសញ្ញាក្បៀស |
| Marketplace license | អាជ្ញាប័ណ្ណទីផ្សារ |
| Personal use | ប្រើប្រាស់ផ្ទាល់ខ្លួន |
| Commercial use | ប្រើប្រាស់ពាណិជ្ជកម្ម |
| Extended studio use | ប្រើប្រាស់ស្ទូឌីយោបន្ថែម |
| Save details | រក្សាទុកព័ត៌មានលម្អិត |
| Version history —  | ប្រវត្តិកំណែ —  |
| Restoring an older version creates a new current version, so history remains intact. | ការស្ដារកំណែចាស់នឹងបង្កើតកំណែបច្ចុប្បន្នថ្មី ដូច្នេះប្រវត្តិនៅដដែល។ |
| Current | បច្ចុប្បន្ន |
| Restore | ស្ដារ |
| Restore template version | ស្ដារកំណែគំរូ |

(In the category form the option `value` stays English; only the visible label changes.)

### `src/js/account.js`
| EN | KM |
|---|---|
| Verified | បានផ្ទៀងផ្ទាត់ |
| Not verified | មិនទាន់ផ្ទៀងផ្ទាត់ |
| Your plan limits are currently enforced. | ដែនកំណត់នៃគម្រោងរបស់អ្នកកំពុងត្រូវបានអនុវត្ត។ |
| Usage limits are informational in this development build; an administrator can assign plans manually. | ដែនកំណត់ការប្រើប្រាស់គ្រាន់តែជាព័ត៌មានក្នុងកំណែអភិវឌ្ឍន៍នេះ អ្នកគ្រប់គ្រងអាចកំណត់គម្រោងដោយដៃបាន។ |
| Allowed | អនុញ្ញាត |
| Disabled by administrator | បិទដោយអ្នកគ្រប់គ្រង |
| Upload permission | សិទ្ធិផ្ទុកឡើង |
| Sign in through the full application server to manage this account. | ចូលតាមរយៈម៉ាស៊ីនបម្រើកម្មវិធីពេញលេញ ដើម្បីគ្រប់គ្រងគណនីនេះ។ |
| The new passwords do not match. | ពាក្យសម្ងាត់ថ្មីមិនត្រូវគ្នាទេ។ |
| Changing password… | កំពុងប្ដូរពាក្យសម្ងាត់… |
| Password changed. Other signed-in sessions were ended. | បានប្ដូរពាក្យសម្ងាត់។ សម័យចូលផ្សេងទៀតត្រូវបានបញ្ចប់។ |
| Preparing export… | កំពុងរៀបចំការនាំចេញ… |
| Export downloaded. | បានទាញយកការនាំចេញ។ |
| Sending verification email… | កំពុងផ្ញើអ៊ីមែលផ្ទៀងផ្ទាត់… |
| Your email is already verified. | អ៊ីមែលរបស់អ្នកត្រូវបានផ្ទៀងផ្ទាត់រួចហើយ។ |
| Verification email sent. | បានផ្ញើអ៊ីមែលផ្ទៀងផ្ទាត់។ |
| Verification token created, but SMTP delivery is not configured. | បានបង្កើតថូខឹនផ្ទៀងផ្ទាត់ ប៉ុន្តែមិនទាន់បានកំណត់ការផ្ញើតាម SMTP ទេ។ |

### `src/js/analytics.js`
| EN | KM |
|---|---|
| Invitation | ការអញ្ជើញ |
| Total views | ចំនួនមើលសរុប |
| All-time public opens | ការបើកជាសាធារណៈសរុបគ្រប់ពេល |
| Last 30 days | 30 ថ្ងៃចុងក្រោយ |
| Recent invitation opens | ការបើកការអញ្ជើញថ្មីៗ |
| RSVP | RSVP |
| RSVP responses | ការឆ្លើយតប RSVP |
| Disabled | បិទ |
| Historical responses are preserved | ការឆ្លើយតបពីមុនត្រូវបានរក្សាទុក |
| total responding guests | ភ្ញៀវដែលបានឆ្លើយតបសរុប |
| Checked in | បានចុះឈ្មោះចូល |
| guests on list | ភ្ញៀវក្នុងបញ្ជី |
| Views — last 30 days | ចំនួនមើល — 30 ថ្ងៃចុងក្រោយ |
| view | ដងមើល |
| RSVP breakdown | ការបែងចែក RSVP |
| RSVP disabled for this invitation. Historical response data remains available. | បានបិទ RSVP សម្រាប់ការអញ្ជើញនេះ។ ទិន្នន័យការឆ្លើយតបពីមុននៅតែអាចប្រើបាន។ |
| No RSVP responses yet. | មិនទាន់មានការឆ្លើយតប RSVP នៅឡើយទេ។ |
| Guest check-in | ការចុះឈ្មោះចូលរបស់ភ្ញៀវ |
| of listed guests checked in. | នៃភ្ញៀវក្នុងបញ្ជីបានចុះឈ្មោះចូល។ |
| Publishing | ការផ្សព្វផ្សាយ |
| Public slug: | ឈ្មោះតំណសាធារណៈ៖ |
| Access: | ការចូលប្រើ៖ |
| Analytics unavailable | មិនមានការវិភាគទេ |

### `src/js/monitoring.js`
| EN | KM |
|---|---|
| System | ប្រព័ន្ធ |
| Uptime | រយៈពេលដំណើរការ |
| Publications | ការផ្សព្វផ្សាយ |
| RSVPs | RSVP |
| Assets | ធនធាន |
| Material storage | ទំហំផ្ទុកសម្ភារៈ |
| API | API |
| Healthy | ដំណើរការល្អ |
| Database | មូលដ្ឋានទិន្នន័យ |
| Asset storage | ឃ្លាំងផ្ទុកធនធាន |
| Redis rate limiting | ការកំណត់អត្រា Redis |
| Connected | បានភ្ជាប់ |
| In-memory fallback | ការប្រើអង្គចងចាំជំនួស |
| AI provider | អ្នកផ្ដល់សេវា AI |
| Configured | បានកំណត់រចនាសម្ព័ន្ធ |
| Local assistant | ជំនួយការក្នុងម៉ាស៊ីន |
| SMTP | SMTP |
| Not configured | មិនទាន់កំណត់រចនាសម្ព័ន្ធ |
| Billing webhook | Webhook ការទូទាត់ |

### `src/html/designer.html`
| EN | KM |
|---|---|
| Skip to content | រំលងទៅមាតិកា |
| Dashboard | ផ្ទាំងគ្រប់គ្រង |
| Materials | សម្ភារៈ |
| Template Studio | ស្ទូឌីយោគំរូ |
| Designer Workspace | កន្លែងធ្វើការរបស់អ្នករចនា |
| A focused launch point for professional template creation, reusable assets, and invitation production. | ចំណុចចាប់ផ្ដើមផ្ដោតសម្រាប់ការបង្កើតគំរូប្រកបដោយវិជ្ជាជីវៈ ធនធានដែលប្រើឡើងវិញបាន និងការផលិតការអញ្ជើញ។ |
| Create complete reusable invitation designs, manage versions, preview thumbnails, and publish selected templates to the marketplace. | បង្កើតការរចនាការអញ្ជើញពេញលេញដែលប្រើឡើងវិញបាន គ្រប់គ្រងកំណែ មើលរូបភាពតូចជាមុន និងផ្សព្វផ្សាយគំរូដែលបានជ្រើសរើសទៅទីផ្សារ។ |
| Open Template Studio | បើកស្ទូឌីយោគំរូ |
| Material Library | បណ្ណាល័យសម្ភារៈ |
| Organize account-level photos, audio, and video with folders, tags, favorites, and reusable media across projects. | រៀបចំរូបថត សំឡេង និងវីដេអូនៅកម្រិតគណនី ដោយប្រើថតឯកសារ ស្លាក ចំណូលចិត្ត និងមេឌៀដែលប្រើឡើងវិញបានក្នុងគ្រប់គម្រោង។ |
| Open Materials | បើកសម្ភារៈ |
| Invitation Production | ការផលិតការអញ្ជើញ |
| Create client invitations from built-in, personal, or marketplace templates and manage the complete editing and publishing workflow. | បង្កើតការអញ្ជើញសម្រាប់អតិថិជនពីគំរូដែលមានស្រាប់ គំរូផ្ទាល់ខ្លួន ឬគំរូលើទីផ្សារ ហើយគ្រប់គ្រងដំណើរការកែប្រែ និងផ្សព្វផ្សាយទាំងមូល។ |
| Create or edit invitations | បង្កើត ឬកែប្រែការអញ្ជើញ |
| Professional workflow | ដំណើរការការងារប្រកបដោយវិជ្ជាជីវៈ |
| Recommended flow: build a reusable master design in the invitation editor → save it as a complete template → manage and version it in Template Studio → publish it to the marketplace when ready → create independent customer invitations from that template. | ដំណើរការដែលណែនាំ៖ បង្កើតការរចនាមេដែលប្រើឡើងវិញបានក្នុងកម្មវិធីកែប្រែការអញ្ជើញ → រក្សាទុកជាគំរូពេញលេញ → គ្រប់គ្រង និងកំណត់កំណែក្នុងស្ទូឌីយោគំរូ → ផ្សព្វផ្សាយទៅទីផ្សារនៅពេលរួចរាល់ → បង្កើតការអញ្ជើញឯករាជ្យសម្រាប់អតិថិជនពីគំរូនោះ។ |

### `src/js/responses.js`
| EN | KM |
|---|---|
| Disabled | បិទ |
| RSVP status | ស្ថានភាព RSVP |
| Historical responses | ការឆ្លើយតបពីមុន |
| Guest wishes | ពាក្យជូនពរពីភ្ញៀវ |
| Responses | ការឆ្លើយតប |
| Attending replies | ចម្លើយថានឹងចូលរួម |
| Attending guests | ភ្ញៀវដែលនឹងចូលរួម |
| No message | គ្មានសារ |
| No RSVP responses match this view. | គ្មានការឆ្លើយតប RSVP ត្រូវនឹងទិដ្ឋភាពនេះទេ។ |
| No private guest wishes yet. | មិនទាន់មានពាក្យជូនពរឯកជនពីភ្ញៀវនៅឡើយទេ។ |
| Saved | បានរក្សាទុក |
| Save | រក្សាទុក |
| Delete this RSVP response? | លុបការឆ្លើយតប RSVP នេះឬ? |
| Delete RSVP response | លុបការឆ្លើយតប RSVP |
| Delete this guest wish? | លុបពាក្យជូនពរនេះឬ? |
| Delete guest wish | លុបពាក្យជូនពរ |

### `src/html/billing.html`
| EN | KM |
|---|---|
| Skip to content | រំលងទៅមាតិកា |
| Dashboard | ផ្ទាំងគ្រប់គ្រង |
| Account | គណនី |
| Membership | សមាជិកភាព |
| Plans & usage | គម្រោង និងការប្រើប្រាស់ |
| Choose the capacity that fits your invitation work. | ជ្រើសរើសសមត្ថភាពដែលសមស្របនឹងការងារអញ្ជើញរបស់អ្នក។ |
| Current plan | គម្រោងបច្ចុប្បន្ន |
| Hosted payment | ការទូទាត់តាមទំព័រទូទាត់ |
| Card details stay with the payment gateway | ព័ត៌មានកាតស្ថិតនៅជាមួយច្រកទូទាត់ |
| The gateway processes Visa and Mastercard details on its secure checkout. The invitation platform receives only a verified payment result and then updates the account tier. | ច្រកទូទាត់ដំណើរការព័ត៌មាន Visa និង Mastercard នៅលើទំព័រទូទាត់សុវត្ថិភាពរបស់ខ្លួន។ ប្រព័ន្ធអញ្ជើញទទួលបានតែលទ្ធផលទូទាត់ដែលបានផ្ទៀងផ្ទាត់ ហើយបន្ទាប់មកធ្វើបច្ចុប្បន្នភាពកម្រិតគណនី។ |
| Payment provider | អ្នកផ្ដល់សេវាទូទាត់ |
| Checking configuration | កំពុងពិនិត្យការកំណត់រចនាសម្ព័ន្ធ |

### `src/js/dashboard.js`
| EN | KM |
|---|---|
| Static preview mode | របៀបមើលជាមុនឋិតិវន្ត |
| Server-backed accounts, collaboration, materials, campaigns, and check-in synchronization require the full application server. | គណនីលើម៉ាស៊ីនបម្រើ ការសហការ សម្ភារៈ យុទ្ធនាការ និងការធ្វើសមកាលកម្មការចុះឈ្មោះចូល ត្រូវការម៉ាស៊ីនបម្រើកម្មវិធីពេញលេញ។ |
| Enter a valid email address. | បញ្ចូលអាសយដ្ឋានអ៊ីមែលដែលត្រឹមត្រូវ។ |
| Use a password of at least 8 characters. | ប្រើពាក្យសម្ងាត់យ៉ាងតិច 8 តួអក្សរ។ |
| The passwords do not match. | ពាក្យសម្ងាត់មិនត្រូវគ្នាទេ។ |
| Enter the 6-digit code from your authenticator app. | បញ្ចូលលេខកូដ 6 ខ្ទង់ពីកម្មវិធីផ្ទៀងផ្ទាត់របស់អ្នក។ |
| Two-step verification was cancelled. | ការផ្ទៀងផ្ទាត់ពីរជំហានត្រូវបានបោះបង់។ |
| Enter your email first, then choose Use a passkey. | បញ្ចូលអ៊ីមែលរបស់អ្នកជាមុន បន្ទាប់មកជ្រើសរើសប៊ូតុង Passkey។ |
| This browser does not support passkeys. | កម្មវិធីរុករកនេះមិនគាំទ្រ Passkey ទេ។ |
| Waiting for your passkey… | កំពុងរង់ចាំ Passkey របស់អ្នក… |

(For "Enter your email first, then choose Use a passkey.": if the sign-in button already has a Khmer label, change the
end of this sentence to name that exact label and list it in the evidence.)

### `src/js/reset.js`
| EN | KM |
|---|---|
| Requesting reset link… | កំពុងស្នើសុំតំណកំណត់ឡើងវិញ… |
| If the account exists, a reset link has been sent. | ប្រសិនបើមានគណនីនេះ តំណកំណត់ពាក្យសម្ងាត់ឡើងវិញត្រូវបានផ្ញើហើយ។ |
| The request was accepted, but email delivery is not configured on this server. Contact the administrator or configure SMTP. | សំណើត្រូវបានទទួលយក ប៉ុន្តែមិនទាន់បានកំណត់ការផ្ញើអ៊ីមែលលើម៉ាស៊ីនបម្រើនេះទេ។ សូមទាក់ទងអ្នកគ្រប់គ្រង ឬកំណត់រចនាសម្ព័ន្ធ SMTP។ |
| Development reset link | តំណកំណត់ឡើងវិញសម្រាប់ការអភិវឌ្ឍន៍ |
| The passwords do not match. | ពាក្យសម្ងាត់មិនត្រូវគ្នាទេ។ |
| Resetting password… | កំពុងកំណត់ពាក្យសម្ងាត់ឡើងវិញ… |
| Password changed successfully. | បានប្ដូរពាក្យសម្ងាត់ដោយជោគជ័យ។ |
| Return to sign in | ត្រឡប់ទៅការចូលគណនី |

### `src/html/admin.html`
| EN | KM |
|---|---|
| Skip to content | រំលងទៅមាតិកា |
| Dashboard | ផ្ទាំងគ្រប់គ្រង |
| Manage accounts, shared templates, and public invitation availability. | គ្រប់គ្រងគណនី គំរូចែករំលែក និងភាពអាចរកបាននៃការអញ្ជើញសាធារណៈ។ |
| AI providers | អ្នកផ្ដល់សេវា AI |

### `src/html/responses.html`
| EN | KM |
|---|---|
| Skip to content | រំលងទៅមាតិកា |
| Dashboard | ផ្ទាំងគ្រប់គ្រង |
| Attending | នឹងចូលរួម |
| Maybe | ប្រហែល |

### `src/js/materials.js`
| EN | KM |
|---|---|
| No matching materials | គ្មានសម្ភារៈត្រូវគ្នាទេ |
| Upload a file or change your filters. | ផ្ទុកឯកសារឡើង ឬប្ដូរតម្រងរបស់អ្នក។ |
| No folder | គ្មានថតឯកសារ |
| Cancel upload | បោះបង់ការផ្ទុកឡើង |

### `src/html/templates.html`
| EN | KM |
|---|---|
| Skip to content | រំលងទៅមាតិកា |
| Dashboard | ផ្ទាំងគ្រប់គ្រង |
| Refresh | ធ្វើបច្ចុប្បន្នភាព |

### `src/js/designer.js`
| EN | KM |
|---|---|
| Designer Workspace unavailable | កន្លែងធ្វើការរបស់អ្នករចនាមិនអាចប្រើបាន |
| Back to dashboard | ត្រឡប់ទៅផ្ទាំងគ្រប់គ្រង |
| Active invitations | ការអញ្ជើញសកម្ម |

### `src/html/materials.html`  (`data-attr` placeholders)
| EN | KM |
|---|---|
| Search name, folder, or tags… | ស្វែងរកតាមឈ្មោះ ថតឯកសារ ឬស្លាក… |
| e.g. Wedding Materials/Bride | ឧ. សម្ភារៈមង្គលការ/កូនក្រមុំ |

### `src/html/guests.html`  (`data-attr` placeholder)
| EN | KM |
|---|---|
| Search name or phone | ស្វែងរកឈ្មោះ ឬលេខទូរសព្ទ |

### `src/js/pages/admin/invitations.js`
| EN | KM |
|---|---|
| Slug | ឈ្មោះតំណ |
| RSVPs | RSVP |

### `src/js/components/chart.js`  (key `rsvps`)
| EN | KM |
|---|---|
| RSVPs | RSVP |

### `src/js/pages/admin/audit-log.js`
| EN | KM |
|---|---|
| IP | IP |

### `src/html/privacy.html`
| EN | KM |
|---|---|
| Skip to content | រំលងទៅមាតិកា |

### `src/html/dashboard.html`
| EN | KM |
|---|---|
| Poster canvas size (px) | ទំហំផ្ទាំងប៉ូស្ទ័រ (px) |

## 7. Notes for the native reviewer (not for the agent)

- Terms chosen that you may want to change globally: **គំរូ** for "template" (admin.html still uses `ពុម្ពអត្ថបទ`), **ផ្ទាំងគ្រប់គ្រង** for "Dashboard", **ការអញ្ជើញ** for "invitation", **ដកហូត** for "revoke", **ធនធាន** for "assets".
- Strings that carry the most risk of an awkward literal feel: the designer workflow sentence, the billing gateway paragraph, "Redis rate limiting", "In-memory fallback", "Public slug".
- Digits are kept as Arabic numerals (30, 8, 6) to match the English strings.
