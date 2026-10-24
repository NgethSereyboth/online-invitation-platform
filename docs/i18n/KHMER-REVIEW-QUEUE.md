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
