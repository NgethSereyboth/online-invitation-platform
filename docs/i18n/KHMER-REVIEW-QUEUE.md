# Khmer review queue — FB-54

**Drafted by Claude, applied by Freebuff, unreviewed by a native speaker.**

Every string in this table is Khmer text that is live in the product after FB-54 and came
from `docs/i18n/KHMER-TRANSLATION-MAP-2026-10-24.md`. Review before a public launch (OD-18).
Rows where the map's Khmer was not pasted because the source already carried a different
translation are **not** listed here; FB-54 did not change them.

## Applied / confirmed in source

| File | English | Khmer |
|---|---|---|
| `src/js/components/chart.js` | Desktop | កុំព្យូទ័រ |
| `src/js/pages/admin/users.js` | Force this user to re-enroll MFA on next login? | បង្ខំអ្នកប្រើនេះឱ្យចុះឈ្មោះ MFA ឡើងវិញនៅពេលចូលគណនីលើកក្រោយឬ? |
| `src/js/pages/admin/users.js` | Start an impersonation session as this user? You will be logged in as them for 30 minutes. | ចាប់ផ្ដើមសម័យតំណាងក្នុងនាមអ្នកប្រើនេះឬ? អ្នកនឹងចូលគណនីក្នុងនាមពួកគេរយៈពេល 30 នាទី។ |
| `src/js/pages/admin/impersonate.js` | Start impersonation session? You will be logged in as this user for 30 minutes. Every action will be audit-logged. | ចាប់ផ្ដើមសម័យតំណាងឬ? អ្នកនឹងចូលគណនីក្នុងនាមអ្នកប្រើនេះរយៈពេល 30 នាទី។ រាល់សកម្មភាពនឹងត្រូវបានកត់ត្រាសម្រាប់ការត្រួតពិនិត្យ។ |
| `src/js/pages/dashboard/analytics.js` | This permanently deletes every session + event for this invitation. Continue? | នេះនឹងលុបសម័យ និងព្រឹត្តិការណ៍ទាំងអស់សម្រាប់ការអញ្ជើញនេះជាអចិន្ត្រៃយ៍។ បន្តឬ? |
| `src/js/designer.js` | Stored materials | សម្ភារៈដែលបានរក្សាទុក |
| `src/js/materials.js` | materials | សម្ភារៈ |
| `src/js/dashboard.js` | Responses | ការឆ្លើយតប |
| `src/js/dashboard.js` | Analytics | ការវិភាគ |
| `src/js/pages/admin/feature-flags.js` | Flag | ជម្រើស |
| `src/js/pages/admin/feature-flags.js` | No flags defined. | មិនមានជម្រើសមុខងារត្រូវបានកំណត់ទេ។ |
| `src/js/pages/admin/feature-flags.js` | Tier | កម្រិត |
| `src/js/pages/admin/feature-flags.js` | Save this flag value? | រក្សាទុកតម្លៃជម្រើសនេះឬ? |
| `src/js/pages/admin/feature-flags.js` | Super-admin access required to modify flags. | ត្រូវការសិទ្ធិអ្នកគ្រប់គ្រងជាន់ខ្ពស់ដើម្បីកែប្រែជម្រើសមុខងារ។ |
| `src/js/pages/admin/feature-flags.js` | Non-admin session idle window | រយៈពេលទំនេរនៃសម័យសម្រាប់អ្នកមិនមែនអ្នកគ្រប់គ្រង |
| `src/js/pages/admin/feature-flags.js` | How long a non-admin session may sit idle before it expires. Changing this affects all non-admin users. | រយៈពេលដែលសម័យរបស់អ្នកមិនមែនអ្នកគ្រប់គ្រងអាចទុកចោលទំនេរមុនផុតកំណត់។ ការផ្លាស់ប្ដូរនេះប៉ះពាល់ដល់អ្នកប្រើមិនមែនអ្នកគ្រប់គ្រងទាំងអស់។ |
| `src/js/pages/admin/feature-flags.js` | Idle window (days) | រយៈពេលទំនេរ (ថ្ងៃ) |
| `src/js/pages/admin/feature-flags.js` | Save idle window | រក្សាទុករយៈពេលទំនេរ |
| `src/js/pages/admin/feature-flags.js` | Change the non-admin session idle window to {days} days? | ប្ដូររយៈពេលទំនេរនៃសម័យសម្រាប់អ្នកមិនមែនអ្នកគ្រប់គ្រងទៅ {days} ថ្ងៃឬ? |
| `src/js/pages/admin/feature-flags.js` | Idle window updated to {days} days. | បានធ្វើបច្ចុប្បន្នភាពរយៈពេលទំនេរទៅ {days} ថ្ងៃ។ |
| `src/js/pages/admin/feature-flags.js` | Failed to update idle window: {error} | ធ្វើបច្ចុប្បន្នភាពរយៈពេលទំនេរមិនបានសម្រេច៖ {error} |
| `src/js/guests.js` | Invited | បានអញ្ជើញ |
| `src/js/guests.js` | Attending | នឹងចូលរួម |
| `src/js/guests.js` | Pending | កំពុងរង់ចាំ |
| `src/js/guests.js` | Off | បិទ |
| `src/js/guests.js` | Group: | ក្រុម៖ |
| `src/js/guests.js` | Household: | គ្រួសារ៖ |
| `src/js/guests.js` | Table: | តុ៖ |
| `src/js/guests.js` | at | នៅ |
| `src/js/guests.js` | RSVP | RSVP |
| `src/js/guests.js` | Opened | បានបើក |
| `src/js/guests.js` | Link | តំណ |
| `src/js/guests.js` | QR | QR |
| `src/js/guests.js` | Guest name | ឈ្មោះភ្ញៀវ |
| `src/js/guests.js` | Email | អ៊ីមែល |
| `src/js/guests.js` | Group | ក្រុម |
| `src/js/guests.js` | Household | គ្រួសារ |
| `src/js/guests.js` | Table | តុ |
| `src/js/guests.js` | Cancel | បោះបង់ |
| `src/js/guests.js` | Save | រក្សាទុក |
| `src/js/guests.js` | Personal invitation link | តំណអញ្ជើញផ្ទាល់ខ្លួន |
| `src/js/guests.js` | Expires | ផុតកំណត់ |
| `src/js/guests.js` | Copy personal link | ចម្លងតំណផ្ទាល់ខ្លួន |
| `src/js/guests.js` | QR code | កូដ QR |
| `src/js/guests.js` | Download QR | ទាញយក QR |
| `src/js/guests.js` | Name | ឈ្មោះ |
| `src/js/guests.js` | Tags | ស្លាក |
| `src/js/guests.js` | RSVP status | ស្ថានភាព RSVP |
| `src/js/guests.js` | Invitation mode | របៀបអញ្ជើញ |
| `src/js/guests.js` | Personal link | តំណផ្ទាល់ខ្លួន |
| `src/js/guests.js` | No | ទេ |
| `src/js/templates.js` | Marketplace | ទីផ្សារ |
| `src/js/templates.js` | Preview | មើលជាមុន |
| `src/js/templates.js` | Use | ប្រើ |
| `src/js/templates.js` | Details | ព័ត៌មានលម្អិត |
| `src/js/templates.js` | Continue | បន្ត |
| `src/js/templates.js` | Sections: | ផ្នែក៖ |
| `src/js/templates.js` | Name | ឈ្មោះ |
| `src/js/templates.js` | Category | ប្រភេទ |
| `src/js/templates.js` | Wedding | អាពាហ៍ពិពាហ៍ |
| `src/js/templates.js` | Business | អាជីវកម្ម |
| `src/js/templates.js` | Other | ផ្សេងៗ |
| `src/js/templates.js` | Description | ការពិពណ៌នា |
| `src/js/templates.js` | Save details | រក្សាទុកព័ត៌មានលម្អិត |
| `src/js/templates.js` | Current | បច្ចុប្បន្ន |
| `src/js/account.js` | Verified | បានផ្ទៀងផ្ទាត់ |
| `src/js/account.js` | Allowed | អនុញ្ញាត |
| `src/js/account.js` | Preparing export… | កំពុងរៀបចំការនាំចេញ… |
| `src/js/account.js` | Sending verification email… | កំពុងផ្ញើអ៊ីមែលផ្ទៀងផ្ទាត់… |
| `src/js/analytics.js` | Invitation | ការអញ្ជើញ |
| `src/js/analytics.js` | Total views | ចំនួនមើលសរុប |
| `src/js/analytics.js` | Last 30 days | 30 ថ្ងៃចុងក្រោយ |
| `src/js/analytics.js` | Recent invitation opens | ការបើកការអញ្ជើញថ្មីៗ |
| `src/js/analytics.js` | RSVP | RSVP |
| `src/js/analytics.js` | RSVP responses | ការឆ្លើយតប RSVP |
| `src/js/analytics.js` | guests on list | ភ្ញៀវក្នុងបញ្ជី |
| `src/js/analytics.js` | Views — last 30 days | ចំនួនមើល — 30 ថ្ងៃចុងក្រោយ |
| `src/js/analytics.js` | RSVP breakdown | ការបែងចែក RSVP |
| `src/js/analytics.js` | No RSVP responses yet. | មិនទាន់មានការឆ្លើយតប RSVP នៅឡើយទេ។ |
| `src/js/analytics.js` | Public slug: | ឈ្មោះតំណសាធារណៈ៖ |
| `src/js/monitoring.js` | System | ប្រព័ន្ធ |
| `src/js/monitoring.js` | RSVPs | RSVP |
| `src/js/monitoring.js` | API | API |
| `src/js/monitoring.js` | Database | មូលដ្ឋានទិន្នន័យ |
| `src/js/monitoring.js` | Connected | បានភ្ជាប់ |
| `src/js/monitoring.js` | Configured | បានកំណត់រចនាសម្ព័ន្ធ |
| `src/js/monitoring.js` | SMTP | SMTP |
| `src/html/designer.html` | Skip to content | រំលងទៅមាតិកា |
| `src/html/designer.html` | Dashboard | ផ្ទាំងគ្រប់គ្រង |
| `src/html/designer.html` | Materials | សម្ភារៈ |
| `src/html/designer.html` | A focused launch point for professional template creation, reusable assets, and invitation production. | ចំណុចចាប់ផ្ដើមផ្ដោតសម្រាប់ការបង្កើតគំរូប្រកបដោយវិជ្ជាជីវៈ ធនធានដែលប្រើឡើងវិញបាន និងការផលិតការអញ្ជើញ។ |
| `src/html/designer.html` | Create complete reusable invitation designs, manage versions, preview thumbnails, and publish selected templates to the marketplace. | បង្កើតការរចនាការអញ្ជើញពេញលេញដែលប្រើឡើងវិញបាន គ្រប់គ្រងកំណែ មើលរូបភាពតូចជាមុន និងផ្សព្វផ្សាយគំរូដែលបានជ្រើសរើសទៅទីផ្សារ។ |
| `src/html/designer.html` | Open Template Studio | បើកស្ទូឌីយោគំរូ |
| `src/html/designer.html` | Material Library | បណ្ណាល័យសម្ភារៈ |
| `src/html/designer.html` | Open Materials | បើកសម្ភារៈ |
| `src/js/responses.js` | RSVP status | ស្ថានភាព RSVP |
| `src/js/responses.js` | Responses | ការឆ្លើយតប |
| `src/js/responses.js` | No RSVP responses match this view. | គ្មានការឆ្លើយតប RSVP ត្រូវនឹងទិដ្ឋភាពនេះទេ។ |
| `src/js/responses.js` | Saved | បានរក្សាទុក |
| `src/js/responses.js` | Save | រក្សាទុក |
| `src/js/responses.js` | Delete RSVP response | លុបការឆ្លើយតប RSVP |
| `src/html/billing.html` | Skip to content | រំលងទៅមាតិកា |
| `src/html/billing.html` | Dashboard | ផ្ទាំងគ្រប់គ្រង |
| `src/html/billing.html` | Account | គណនី |
| `src/html/billing.html` | Membership | សមាជិកភាព |
| `src/html/billing.html` | Plans & usage | គម្រោង និងការប្រើប្រាស់ |
| `src/html/billing.html` | Current plan | គម្រោងបច្ចុប្បន្ន |
| `src/js/dashboard.js` | The passwords do not match. | ពាក្យសម្ងាត់មិនត្រូវគ្នាទេ។ |
| `src/js/dashboard.js` | Two-step verification was cancelled. | ការផ្ទៀងផ្ទាត់ពីរជំហានត្រូវបានបោះបង់។ |
| `src/js/reset.js` | Requesting reset link… | កំពុងស្នើសុំតំណកំណត់ឡើងវិញ… |
| `src/js/reset.js` | The passwords do not match. | ពាក្យសម្ងាត់មិនត្រូវគ្នាទេ។ |
| `src/js/reset.js` | Resetting password… | កំពុងកំណត់ពាក្យសម្ងាត់ឡើងវិញ… |
| `src/html/admin.html` | Skip to content | រំលងទៅមាតិកា |
| `src/html/admin.html` | Dashboard | ផ្ទាំងគ្រប់គ្រង |
| `src/html/responses.html` | Skip to content | រំលងទៅមាតិកា |
| `src/html/responses.html` | Dashboard | ផ្ទាំងគ្រប់គ្រង |
| `src/html/responses.html` | Maybe | ប្រហែល |
| `src/html/templates.html` | Skip to content | រំលងទៅមាតិកា |
| `src/html/templates.html` | Dashboard | ផ្ទាំងគ្រប់គ្រង |
| `src/html/templates.html` | Refresh | ធ្វើបច្ចុប្បន្នភាព |
| `src/js/designer.js` | Back to dashboard | ត្រឡប់ទៅផ្ទាំងគ្រប់គ្រង |
| `src/js/designer.js` | Active invitations | ការអញ្ជើញសកម្ម |
| `src/html/materials.html` | Search name, folder, or tags… | ស្វែងរកតាមឈ្មោះ ថតឯកសារ ឬស្លាក… |
| `src/html/materials.html` | e.g. Wedding Materials/Bride | ឧ. សម្ភារៈមង្គលការ/កូនក្រមុំ |
| `src/html/guests.html` | Search name or phone | ស្វែងរកឈ្មោះ ឬលេខទូរសព្ទ |
| `src/js/pages/admin/invitations.js` | Slug | ឈ្មោះតំណ |
| `src/js/pages/admin/invitations.js` | RSVPs | RSVP |
| `src/js/components/chart.js` | RSVPs | RSVP |
| `src/js/pages/admin/audit-log.js` | IP | IP |
| `src/html/privacy.html` | Skip to content | រំលងទៅមាតិកា |
| `src/html/dashboard.html` | Poster canvas size (px) | ទំហំផ្ទាំងប៉ូស្ទ័រ (px) |

## Not yet translatable — no map row (2026-10-24, FB-61)

The audit found **72 occurrences / 42 unique strings** in `<span class="i18n-km">` slots that still
render English to a Khmer reader, concentrated in the shared header rebuilt in FB-48/FB-55
(`Workspace` 20×, `Plans` 11×, `Passkeys`, `Administration`, `Sign out`, `Welcome back`, …).
They are not in this queue because there is nothing to review yet: rule R3 forbids applying Khmer
that the map does not contain, and `tools/i18n-apply-khmer-map.py` matches no row for those slots.

The full inventory — English string, occurrence count, pages, and whether a map row exists
elsewhere — is `docs/i18n/KHMER-GAP-SHARED-HEADER-2026-10-24.md`. The next Khmer round needs a map
section per file for those strings before any of them can ship.

## LT-1.2 — ADDENDUM and ADDENDUM-2 applied (2026-10-24)

Drafted by Claude, applied by `tools/i18n-apply-khmer-map.py`; still unreviewed by a native speaker (OD-18).
The row values below are copied from the two addendum maps by script; the conditional dashboard row carries the
new English text as well as its Khmer. ADDENDUM-2 rows are JS keys, listed as `key`.

| File | English | Khmer |
|---|---|---|
| `src/html/account.html` | Workspace | កន្លែងធ្វើការ |
| `src/html/account.html` | Plans | គម្រោង |
| `src/html/account.html` | Passkeys | Passkey |
| `src/html/admin.html` | Workspace | កន្លែងធ្វើការ |
| `src/html/admin.html` | Plans | គម្រោង |
| `src/html/admin.html` | Administration | ការគ្រប់គ្រងប្រព័ន្ធ |
| `src/html/analytics.html` | Workspace | កន្លែងធ្វើការ |
| `src/html/analytics.html` | Plans | គម្រោង |
| `src/html/analytics.html` | Analytics | ការវិភាគ |
| `src/html/billing.html` | Workspace | កន្លែងធ្វើការ |
| `src/html/billing.html` | Plans | គម្រោង |
| `src/html/billing.html` | Plans & usage | គម្រោង និងការប្រើប្រាស់ |
| `src/html/checkin.html` | Online | អនឡាញ |
| `src/html/designer.html` | Workspace | កន្លែងធ្វើការ |
| `src/html/designer.html` | Plans | គម្រោង |
| `src/html/designer.html` | Designer | អ្នករចនា |
| `src/html/guests.html` | Workspace | កន្លែងធ្វើការ |
| `src/html/guests.html` | Plans | គម្រោង |
| `src/html/guests.html` | Event Check-in | ការចុះឈ្មោះចូលព្រឹត្តិការណ៍ |
| `src/html/materials.html` | Workspace | កន្លែងធ្វើការ |
| `src/html/materials.html` | Plans | គម្រោង |
| `src/html/materials.html` | Delete | លុប |
| `src/html/responses.html` | Workspace | កន្លែងធ្វើការ |
| `src/html/responses.html` | Plans | គម្រោង |
| `src/html/templates.html` | Workspace | កន្លែងធ្វើការ |
| `src/html/templates.html` | Plans | គម្រោង |
| `src/html/templates.html` | Template Studio | ស្ទូឌីយោគំរូ |
| `src/html/templates.html` | ＋ New poster | ＋ ប៉ូស្ទ័រថ្មី |
| `src/html/dashboard.html` | Workspace | កន្លែងធ្វើការ |
| `src/html/dashboard.html` | Plans | គម្រោង |
| `src/html/dashboard.html` | Welcome back | សូមស្វាគមន៍ត្រឡប់មកវិញ |
| `src/html/dashboard.html` | Sign in to continue working on your invitations and events. | ចូលគណនីដើម្បីបន្តធ្វើការលើការអញ្ជើញ និងព្រឹត្តិការណ៍របស់អ្នក។ |
| `src/html/dashboard.html` | Sign out | ចាកចេញ |
| `src/html/dashboard.html` | or | ឬ |
| `src/html/dashboard.html` | Design invitations that feel premium, personal, and alive. | រចនាការអញ្ជើញដែលមានអារម្មណ៍ប្រណីត ផ្ទាល់ខ្លួន និងរស់រវើក។ |
| `src/html/dashboard.html` | Khmer + English, light + dark, publish-ready pages | ខ្មែរ + អង់គ្លេស ភ្លឺ + ងងឹត ទំព័រដែលរួចរាល់សម្រាប់ផ្សព្វផ្សាយ |
| `src/html/dashboard.html` | Guest list, RSVP responses and analytics in one workspace | បញ្ជីភ្ញៀវ ការឆ្លើយតប RSVP និងការវិភាគ ក្នុងកន្លែងធ្វើការតែមួយ |
| `src/html/dashboard.html` | Canva-like design studio for invitations and posters | ស្ទូឌីយោរចនាបែប Canva សម្រាប់ការអញ្ជើញ និងប៉ូស្ទ័រ |
| `src/html/dashboard.html` | Designer Workspace | កន្លែងធ្វើការរបស់អ្នករចនា |
| `src/html/dashboard.html` | Marketplace | ទីផ្សារ |
| `src/html/dashboard.html` | My invitations | ការអញ្ជើញរបស់ខ្ញុំ |
| `src/html/dashboard.html` | My templates | គំរូរបស់ខ្ញុំ |
| `src/html/dashboard.html` | ★ Favorites | ★ ចំណូលចិត្ត |
| `src/html/dashboard.html` | Create invitation | បង្កើតការអញ្ជើញ |
| `src/html/dashboard.html` | Create from template | បង្កើតពីគំរូ |
| `src/html/dashboard.html` | Use this template | ប្រើគំរូនេះ |
| `src/html/dashboard.html` | Invitation name | ឈ្មោះការអញ្ជើញ |
| `src/html/dashboard.html` | Event type | ប្រភេទព្រឹត្តិការណ៍ |
| `src/html/dashboard.html` | Cancel | បោះបង់ |
| `src/html/dashboard.html` | Close | បិទ |
| `src/html/dashboard.html` | Built-in templates now include page structure, palette, section styling, animation, and visual-page layouts. Invitations saved as your own templates appear here too. | គំរូដែលមានស្រាប់ឥឡូវនេះរួមមានរចនាសម្ព័ន្ធទំព័រ ក្រុមពណ៌ រចនាប័ទ្មផ្នែក ចលនា និងប្លង់ទំព័រមើលឃើញ។ ការអញ្ជើញដែលបានរក្សាទុកជាគំរូផ្ទាល់ខ្លួនក៏បង្ហាញនៅទីនេះដែរ។ |
| `src/html/dashboard.html` | Design studio for invitations and posters | ស្ទូឌីយោរចនាសម្រាប់ការអញ្ជើញ និងប៉ូស្ទ័រ |
| `src/html/index.html` | Undo | មិនធ្វើវិញ |
| `src/html/index.html` | Redo | ធ្វើឡើងវិញ |
| `src/html/index.html` | Guest preview | ការមើលជាមុនសម្រាប់ភ្ញៀវ |
| `src/html/index.html` | Publish snapshot | ផ្សព្វផ្សាយកំណែបច្ចុប្បន្ន |
| `src/html/index.html` | Canvas zoom | ការពង្រីកផ្ទាំង |
| `src/html/index.html` | Filter materials | ត្រងសម្ភារៈ |
| `src/html/index.html` | Local mode | របៀបមូលដ្ឋាន |
| `src/html/index.html` | Style & motion | រចនាប័ទ្ម និងចលនា |
| `src/html/index.html` | Untitled design | ការរចនាគ្មានចំណងជើង |
| `` | ពុម្ពអត្ថបទ |  |
| `src/js/pages/admin/feature-flags.js` | key `flagSaved` | បានរក្សាទុក {key}។ |
| `src/js/pages/admin/feature-flags.js` | key `saveFailed` | មិនអាចរក្សាទុកការផ្លាស់ប្ដូរបានទេ។ សូមព្យាយាមម្ដងទៀត។ |
| `src/js/pages/admin/feature-flags.js` | key `updatedAt` | បានធ្វើបច្ចុប្បន្នភាព |
| `src/js/pages/admin/users.js` | key `confirmSuspend` | ផ្អាកអ្នកប្រើនេះឬ? សម័យដែលកំពុងសកម្មនឹងត្រូវលុបចោល។ |
| `src/js/pages/admin/users.js` | key `tipStepUp` | ត្រូវការសិទ្ធិអ្នកគ្រប់គ្រងជាន់ខ្ពស់ (ការផ្ទៀងផ្ទាត់បន្ថែម) |

The ADDENDUM §4 terminology replacement (the "text template" word → the term-base word) was applied
to 24 occurrences in 14 files; the file:line list is in `artifacts/next-work/lt-1-2/NOTES.md`.

## Khmer event template pack (TP-6.1)

Every key in `template-pack/copy-bank.json` (117), copied verbatim into the 36 built
templates. English is the pack's own companion line; the Khmer is the copy bank's,
unreviewed by a native speaker. Review before launch (OD-18).

| Source | Key · English | Khmer |
|---|---|---|
| `template-pack/copy-bank.json` | key `anniv.invite` · Join us as we celebrate our wedding anniversary | សូម​អញ្ជើញ​ចូលរួម​អបអរសាទរ​ខួប​អាពាហ៍​ពិពាហ៍​របស់​យើងខ្ញុំ |
| `template-pack/copy-bank.json` | key `anniv.title` · Wedding Anniversary | ខួប​អាពាហ៍​ពិពាហ៍ |
| `template-pack/copy-bank.json` | key `baby.line` · A new life, a new joy | ជីវិត​ថ្មី សេចក្តី​រីករាយ​ថ្មី |
| `template-pack/copy-bank.json` | key `baby.title` · Welcome, Little One | សូមស្វាគមន៍​សមាជិក​ថ្មី |
| `template-pack/copy-bank.json` | key `bd.first` · My First Birthday | ខួបកំណើត​គម្រប់ ១ ឆ្នាំ |
| `template-pack/copy-bank.json` | key `bd.happy` · Happy Birthday | រីករាយ​ថ្ងៃកំណើត |
| `template-pack/copy-bank.json` | key `bd.invite` · You are invited to celebrate the birthday of | សូម​អញ្ជើញ​ចូលរួម​អបអរសាទរ​ខួបកំណើត​របស់ |
| `template-pack/copy-bank.json` | key `bd.kids_invite` · Come and celebrate with us! | សូម​អញ្ជើញ​មក​អបអរសាទរ​ជាមួយ​យើង! |
| `template-pack/copy-bank.json` | key `bd.longevity.invite` · Join us in honouring our elder on this special birthday | សូម​គោរព​អញ្ជើញ​ចូលរួម​ពិធីបុណ្យ​ចម្រើន​អាយុ |
| `template-pack/copy-bank.json` | key `bd.longevity.title` · Longevity Blessing Ceremony | ពិធីបុណ្យ​ចម្រើន​អាយុ |
| `template-pack/copy-bank.json` | key `bd.longevity.wish` · May you enjoy a long life and good health | សូមជូនពរ​ឱ្យ​មាន​អាយុ​យឺនយូរ សុខភាព​ល្អ |
| `template-pack/copy-bank.json` | key `bd.sixty` · 60th Birthday | ខួបកំណើត​គម្រប់ ៦០ ឆ្នាំ |
| `template-pack/copy-bank.json` | key `bd.title` · Birthday Celebration | ពិធី​អបអរសាទរ​ខួបកំណើត |
| `template-pack/copy-bank.json` | key `bless.elder` · May you be blessed with long life, good health, strength and wisdom | សូម​ឱ្យ​លោកអ្នក​មាន​អាយុ​យឺនយូរ សុខភាព​ល្អ កម្លាំង​មាំមួន និង​ប្រាជ្ញាវាងវៃ |
| `template-pack/copy-bank.json` | key `bless.line` · May your life be filled with happiness, health and good fortune | សូម​ឱ្យ​ជីវិត​របស់​លោកអ្នក​ពោរពេញ​ដោយ​សុភមង្គល សុខភាព​ល្អ និង​សំណាងល្អ |
| `template-pack/copy-bank.json` | key `bless.title` · Blessings and Good Wishes | សូមជូនពរ |
| `template-pack/copy-bank.json` | key `cong.title` · Congratulations | សូម​អបអរសាទរ |
| `template-pack/copy-bank.json` | key `gala.invite` · The pleasure of your company is requested | សូម​គោរព​អញ្ជើញលោក​អ្នកចូលរួម​ជា​ភ្ញៀវ​កិត្តិយស |
| `template-pack/copy-bank.json` | key `gala.title` · Annual Gala Dinner | ពិធីជប់លៀង​អាហារ​ពេលល្ងាច​ប្រចាំឆ្នាំ |
| `template-pack/copy-bank.json` | key `gny.title` · Happy New Year | សួស្តី​ឆ្នាំ​សកល​ថ្មី |
| `template-pack/copy-bank.json` | key `gny.wish` · Wishing you a bright and joyful year ahead | សូមជូនពរ​ឱ្យ​លោកអ្នក​មាន​ឆ្នាំ​ថ្មី​ដ៏​ភ្លឺស្វាង និង​ពោរពេញ​ដោយ​សេចក្តី​សុខ |
| `template-pack/copy-bank.json` | key `grad.title` · Congratulations, Graduate | អបអរសាទរ​បញ្ចប់​ការសិក្សា |
| `template-pack/copy-bank.json` | key `grad.wish` · Wishing you success in every step ahead | សូមជូនពរ​ឱ្យ​ទទួល​បាន​ជោគជ័យ​គ្រប់​ជំហាន​បន្ទាប់ |
| `template-pack/copy-bank.json` | key `hw.invite` · We invite you to bless our new home | សូម​គោរព​អញ្ជើញ​ចូលរួម​ពិធីបុណ្យ​ឡើងផ្ទះ​ថ្មី​របស់​យើងខ្ញុំ |
| `template-pack/copy-bank.json` | key `hw.title` · House Blessing Ceremony | ពិធីបុណ្យ​ឡើងផ្ទះ​ថ្មី |
| `template-pack/copy-bank.json` | key `kathina.invite` · We invite all benefactors to join the Kathina ceremony | សូម​អញ្ជើញ​សប្បុរសជន​ចូលរួម​បុណ្យកឋិន​ទាន |
| `template-pack/copy-bank.json` | key `kathina.title` · Kathina Robe Offering | បុណ្យកឋិន​ទាន |
| `template-pack/copy-bank.json` | key `label.afternoon` · Afternoon | ពេលរសៀល |
| `template-pack/copy-bank.json` | key `label.bride` · Bride | កូនក្រមុំ |
| `template-pack/copy-bank.json` | key `label.contact` · Contact | ទំនាក់ទំនង |
| `template-pack/copy-bank.json` | key `label.date` · Date | កាលបរិច្ឆេទ |
| `template-pack/copy-bank.json` | key `label.daughter_of` · Daughter of | កូនស្រី​របស់ |
| `template-pack/copy-bank.json` | key `label.day1` · Day 1 | ថ្ងៃទី ១ |
| `template-pack/copy-bank.json` | key `label.day2` · Day 2 | ថ្ងៃទី ២ |
| `template-pack/copy-bank.json` | key `label.day3` · Day 3 | ថ្ងៃទី ៣ |
| `template-pack/copy-bank.json` | key `label.dress_traditional` · Traditional Khmer attire | ស្លៀកពាក់​ប្រពៃណី​ខ្មែរ |
| `template-pack/copy-bank.json` | key `label.dresscode` · Dress code | ការ​ស្លៀកពាក់ |
| `template-pack/copy-bank.json` | key `label.evening` · Evening | ពេលល្ងាច |
| `template-pack/copy-bank.json` | key `label.groom` · Groom | កូនកំលោះ |
| `template-pack/copy-bank.json` | key `label.host` · Hosts | ម្ចាស់​ពិធី |
| `template-pack/copy-bank.json` | key `label.hosted_by` · Hosted by | រៀបចំ​ដោយ |
| `template-pack/copy-bank.json` | key `label.in_memory` · In loving memory | ក្នុង​សេចក្តី​នឹករលឹក |
| `template-pack/copy-bank.json` | key `label.invited` · You are cordially invited | សូម​គោរព​អញ្ជើញ |
| `template-pack/copy-bank.json` | key `label.location` · Location | ទីតាំង |
| `template-pack/copy-bank.json` | key `label.map` · Map | ផែនទី |
| `template-pack/copy-bank.json` | key `label.morning` · Morning | ពេលព្រឹក |
| `template-pack/copy-bank.json` | key `label.program` · Programme | កម្មវិធី |
| `template-pack/copy-bank.json` | key `label.rsvp` · Kindly confirm your attendance | សូម​បញ្ជាក់​ការចូលរួម |
| `template-pack/copy-bank.json` | key `label.save_the_date` · Save the Date | សូម​កត់ទុក​ថ្ងៃ |
| `template-pack/copy-bank.json` | key `label.son_of` · Son of | កូនប្រុស​របស់ |
| `template-pack/copy-bank.json` | key `label.time` · Time | ម៉ោង |
| `template-pack/copy-bank.json` | key `label.venue` · Venue | ទីកន្លែង |
| `template-pack/copy-bank.json` | key `label.with_love` · With love and gratitude | ដោយ​ក្តី​ស្រឡាញ់ និង​ការ​ដឹងគុណ |
| `template-pack/copy-bank.json` | key `label.with_respect` · With respect, we wish you | ដោយ​ក្តី​គោរព សូមជូនពរ |
| `template-pack/copy-bank.json` | key `memorial.invite` · You are respectfully invited to a ceremony dedicating merit to | សូម​គោរព​អញ្ជើញ​ចូលរួម​ពិធីបុណ្យ​ឧទ្ទិស​កុសល​ជូន |
| `template-pack/copy-bank.json` | key `memorial.title` · Memorial Ceremony | ពិធីបុណ្យ​ខួប |
| `template-pack/copy-bank.json` | key `memorial.wish` · May the soul rest in peace | សូម​ឱ្យ​វិញ្ញាណក្ខន្ធ​បាន​ទៅកាន់​សុគតិភព |
| `template-pack/copy-bank.json` | key `merit.invite` · You are invited to join us in making merit | សូម​គោរព​អញ្ជើញ​ចូលរួម​ធ្វើបុណ្យ​ទាន |
| `template-pack/copy-bank.json` | key `merit.title` · Merit-Making Ceremony | ពិធីបុណ្យ​ទាន |
| `template-pack/copy-bank.json` | key `ny.greeting` · Happy Khmer New Year | សួស្តី​ឆ្នាំ​ថ្មី |
| `template-pack/copy-bank.json` | key `ny.title` · Khmer New Year | បុណ្យចូលឆ្នាំ​ថ្មី​ប្រពៃណី​ខ្មែរ |
| `template-pack/copy-bank.json` | key `ny.wish` · May the new year bring you health, happiness and prosperity | សូមជូនពរ​លោកអ្នក​ប្រកបដោយ​សុខភាព​ល្អ សុភមង្គល និង​ភាព​រុងរឿង​ក្នុង​ឆ្នាំ​ថ្មី |
| `template-pack/copy-bank.json` | key `open.invite` · You are invited to the grand opening of | សូម​គោរព​អញ្ជើញ​ចូលរួម​ពិធីសម្ពោធ​បើក​ដំណើរការ |
| `template-pack/copy-bank.json` | key `open.title` · Grand Opening | ពិធីសម្ពោធ​បើក​ដំណើរការ |
| `template-pack/copy-bank.json` | key `pchum.invite` · In remembrance of our ancestors | ដើម្បីរំលឹក​គុណ​ដូនតា |
| `template-pack/copy-bank.json` | key `pchum.line` · You are invited to join the ceremony and dedicate merit to our ancestors | សូម​អញ្ជើញ​ចូលរួម​បុណ្យភ្ជុំបិណ្ឌ ឧទ្ទិស​កុសល​ជូន​ដូនតា |
| `template-pack/copy-bank.json` | key `pchum.title` · Pchum Ben | បុណ្យភ្ជុំបិណ្ឌ |
| `template-pack/copy-bank.json` | key `ph.address` · [Address] | [អាសយដ្ឋាន] |
| `template-pack/copy-bank.json` | key `ph.age` · [Age] | [អាយុ] |
| `template-pack/copy-bank.json` | key `ph.baby` · [Baby name] | [ឈ្មោះ​កូន] |
| `template-pack/copy-bank.json` | key `ph.bride` · [Bride name] | [ឈ្មោះ​កូនក្រមុំ] |
| `template-pack/copy-bank.json` | key `ph.company` · [Company name] | [ឈ្មោះ​ក្រុមហ៊ុន] |
| `template-pack/copy-bank.json` | key `ph.date` · [Date] | [កាលបរិច្ឆេទ] |
| `template-pack/copy-bank.json` | key `ph.departed` · [Name of the departed] | [ឈ្មោះ​អ្នក​ដែល​បាន​ចែកឋាន] |
| `template-pack/copy-bank.json` | key `ph.groom` · [Groom name] | [ឈ្មោះ​កូនកំលោះ] |
| `template-pack/copy-bank.json` | key `ph.host` · [Host name] | [ឈ្មោះ​ម្ចាស់​ពិធី] |
| `template-pack/copy-bank.json` | key `ph.message` · [Your message] | [សារ​ជូនពរ​របស់​អ្នក] |
| `template-pack/copy-bank.json` | key `ph.name` · [Name] | [ឈ្មោះ] |
| `template-pack/copy-bank.json` | key `ph.parents_bride` · [Bride's parents] | [ឪពុក​ម្តាយកូន​ក្រមុំ] |
| `template-pack/copy-bank.json` | key `ph.parents_groom` · [Groom's parents] | [ឪពុក​ម្តាយកូន​កំលោះ] |
| `template-pack/copy-bank.json` | key `ph.phone` · [Phone] | [លេខទូរស័ព្ទ] |
| `template-pack/copy-bank.json` | key `ph.school` · [School or university] | [សាលា ឬ សាកល​វិទ្យាល័យ] |
| `template-pack/copy-bank.json` | key `ph.time` · [Time] | [ម៉ោង] |
| `template-pack/copy-bank.json` | key `ph.venue` · [Venue] | [ទីកន្លែង] |
| `template-pack/copy-bank.json` | key `sched.ancestors` · Offering to ancestors | ពិធី​សែនដូនតា |
| `template-pack/copy-bank.json` | key `sched.banquet` · Wedding banquet | ពិធីជប់លៀង |
| `template-pack/copy-bank.json` | key `sched.ceremony` · Wedding ceremony | ពិធី​រៀប​អាពាហ៍​ពិពាហ៍ |
| `template-pack/copy-bank.json` | key `sched.chanting` · Monks' blessing chant | ពិធីសូត្រមន្ត |
| `template-pack/copy-bank.json` | key `sched.dinner` · Dinner | អាហារ​ពេលល្ងាច |
| `template-pack/copy-bank.json` | key `sched.engagement` · Engagement ceremony | ពិធី​ភ្ជាប់ពាក្យ |
| `template-pack/copy-bank.json` | key `sched.hair` · Hair-cutting ceremony | ពិធីកាត់សក់ |
| `template-pack/copy-bank.json` | key `sched.lunch` · Lunch | អាហារ​ថ្ងៃត្រង់ |
| `template-pack/copy-bank.json` | key `sched.monks_meal` · Chanting and meal offering to the monks | សូត្រ​មន្ត និង​ប្រគេន​ភត្តាហារ​ដល់​ព្រះសង្ឃ |
| `template-pack/copy-bank.json` | key `sched.procession` · Gift procession | ពិធីហែជំនូន |
| `template-pack/copy-bank.json` | key `sched.ribbon` · Ribbon-cutting | ពិធី​កាត់ខ្សែបូ |
| `template-pack/copy-bank.json` | key `sched.welcome` · Welcome of guests | ពិធី​ស្វាគមន៍​ភ្ញៀវ |
| `template-pack/copy-bank.json` | key `sched.wrist` · Wrist-tying blessing | ពិធីចងដៃ |
| `template-pack/copy-bank.json` | key `symp.line` · Our thoughts are with you and your family | យើងខ្ញុំ​សូម​រំលែកទុក្ខ​ជាមួយ​លោកអ្នក និង​ក្រុម​គ្រួសារ |
| `template-pack/copy-bank.json` | key `symp.title` · With Deepest Sympathy | សូម​ចូលរួម​រំលែកទុក្ខ |
| `template-pack/copy-bank.json` | key `thanks.line` · Thank you for celebrating with us | អរគុណ​ដែល​បាន​ចូលរួម​អបអរសាទរ​ជាមួយ​យើងខ្ញុំ |
| `template-pack/copy-bank.json` | key `thanks.title` · Thank You | សូម​អរគុណ |
| `template-pack/copy-bank.json` | key `wedding.engagement.invite` · You are warmly invited to witness our engagement ceremony | សូម​គោរព​អញ្ជើញលោក​អ្នកចូលរួម​ជា​ភ្ញៀវ​កិត្តិយស​ក្នុង​ពិធី​ភ្ជាប់ពាក្យ |
| `template-pack/copy-bank.json` | key `wedding.engagement.title` · Engagement Ceremony | ពិធី​ភ្ជាប់ពាក្យ |
| `template-pack/copy-bank.json` | key `wedding.hair.invite` · Join us for the traditional blessing before the wedding | សូម​គោរព​អញ្ជើញ​ចូលរួម​ពិធីកាត់សក់ តាម​ប្រពៃណី​ខ្មែរ មុន​ពិធី​អាពាហ៍​ពិពាហ៍ |
| `template-pack/copy-bank.json` | key `wedding.hair.title` · Hair-Cutting Ceremony | ពិធីកាត់សក់ |
| `template-pack/copy-bank.json` | key `wedding.honour` · Your presence is a great honour to us | ការចូលរួម​របស់​លោកអ្នក គឺជា​កិត្តិយស​ដ៏​ខ្ពង់ខ្ពស់​សម្រាប់​យើងខ្ញុំ |
| `template-pack/copy-bank.json` | key `wedding.invite_formal` · Together with their families, request the honour of your presence at the wedding of their son and daughter | សូម​គោរព​អញ្ជើញ ឯកឧត្តម លោកជំទាវ លោក លោកស្រី អ្នកនាង កញ្ញា ចូលរួម​ជា​ភ្ញៀវ​កិត្តិយស ក្នុង​ពិធី​អាពាហ៍​ពិពាហ៍​កូនប្រុស និង​កូនស្រី​របស់​យើងខ្ញុំ |
| `template-pack/copy-bank.json` | key `wedding.invite_short` · Together with our families, we invite you to celebrate our wedding | សូម​គោរព​អញ្ជើញលោក​អ្នកចូលរួម​អបអរសាទរ​ពិធី​អាពាហ៍​ពិពាហ៍​របស់​យើងខ្ញុំ |
| `template-pack/copy-bank.json` | key `wedding.program.intro` · Please join us for the following ceremonies | សូម​គោរព​អញ្ជើញ​ចូលរួម​ក្នុង​ពិធី​ដូច​ខាងក្រោម |
| `template-pack/copy-bank.json` | key `wedding.program.title` · Three Days of Celebration | កម្មវិធី​អាពាហ៍​ពិពាហ៍​បី​ថ្ងៃ |
| `template-pack/copy-bank.json` | key `wedding.reception.invite` · Join us for an evening of dinner and celebration | សូម​គោរព​អញ្ជើញ​ចូលរួម​ពិធីជប់លៀង​អាហារ​ពេលល្ងាច ដើម្បី​អបអរសាទរ​អាពាហ៍​ពិពាហ៍ |
| `template-pack/copy-bank.json` | key `wedding.reception.title` · Wedding Reception | ពិធីជប់លៀង​អាពាហ៍​ពិពាហ៍ |
| `template-pack/copy-bank.json` | key `wedding.title` · Wedding Ceremony | សិរីមង្គល​អាពាហ៍​ពិពាហ៍ |
| `template-pack/copy-bank.json` | key `well.line` · Wishing you good health again very soon | សូមជូនពរ​ឱ្យ​មាន​សុខភាព​ល្អ​ឡើង​វិញ​ឆាប់​ៗ |
| `template-pack/copy-bank.json` | key `well.title` · Get Well Soon | សូម​ឱ្យ​ឆាប់​ជាសះស្បើយ |
| `template-pack/copy-bank.json` | key `wf.title` · Water Festival | បុណ្យអុំទូក |
| `template-pack/copy-bank.json` | key `wf.wish` · Wishing you joy and good fortune this Water Festival | សូមជូនពរ​ឱ្យ​លោកអ្នក​រីករាយ និង​ជួប​តែ​សំណាងល្អ​ក្នុង​បុណ្យអុំទូក |
