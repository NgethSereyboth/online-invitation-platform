# Khmer translation map — ADDENDUM 2: JS string-table repairs (2026-10-24)

**Purpose:** closes the Khmer that decisions OD-8 and OD-12 left "owner-supplied". Read from the **current source**, not from the old
ledger: several items in OD-12 are already fixed (`សម្ភារៈ`, `បញ្ជីភ្ញៀវ`, `ការឆ្លើយតប`, `ការវិភាគ` now show correctly in the
rail; `admin/chart.js` and `admin/analytics.js` no longer exist; `users.js` `confirmForceMfa` no longer contains CJK).
What is **still** wrong in the source I read is listed below. Used by plan item **LT-1.2**.

**Authorship and status:** drafted by Claude at the owner's standing request; not native-reviewed (OD-18, non-blocking). The agent
pastes exactly, never edits or extends this Khmer, and lists every applied key in `docs/i18n/KHMER-REVIEW-QUEUE.md`.

## 0. How to apply (JS string tables)

1. These files are **JS objects**, not HTML. Extend `tools/i18n-apply-khmer-map.py` (or add a sibling `tools/i18n-apply-khmer-keys.py`)
   so a section headed `### \`path\` (STRINGS.km)` replaces the **value of the named key inside that file's `km:` block only**.
   Each replacement must change exactly one value on one line, leave the key, quotes, commas and neighbours byte-identical, and
   preserve placeholders (`{key}`, `{days}`, `{error}`) exactly. If the key is absent, or appears in more than one `km:` block, report a mismatch and skip.
2. Never touch the `en:` block. Never touch a key not listed here.
3. After applying: `scripts/check-bilingual-consistency.py` must exit 0 and its foreign-script and Latin-in-Khmer rules must report no
   hit in these two files; then remove any `KNOWN_FOREIGN_SCRIPT_DAMAGE` entry that no longer matches anything, and delete the
   now-false `KH_PENDING` comment in `feature-flags.js`.
4. **Re-scan first.** Run the foreign-script / Latin-in-Khmer scan over `src/js/pages/admin/*.js` and `src/js/pages/**` and put every
   hit that is **not** listed below into `docs/i18n/KHMER-GAP-ROUND5-2026-10-24.md` with file, key and the damaged text (copy it by
   script). Claude drafts the next addendum from that list. Do not repair unlisted keys yourself.

## 1. `src/js/pages/admin/feature-flags.js` (STRINGS.km)

| KEY | KM |
|---|---|
| flagSaved | បានរក្សាទុក {key}។ |
| saveFailed | មិនអាចរក្សាទុកការផ្លាស់ប្ដូរបានទេ។ សូមព្យាយាមម្ដងទៀត។ |
| updatedAt | បានធ្វើបច្ចុប្បន្នភាព |

(`updatedAt` is a typo repair: the current value is missing a letter in "បច្ចុប្បន្ន". `flagSaved` and `saveFailed` are the two
strings still carrying the English fallback behind the `KH_PENDING` comment.)

## 2. `src/js/pages/admin/users.js` (STRINGS.km)

| KEY | KM |
|---|---|
| confirmSuspend | ផ្អាកអ្នកប្រើនេះឬ? សម័យដែលកំពុងសកម្មនឹងត្រូវលុបចោល។ |
| tipStepUp | ត្រូវការសិទ្ធិអ្នកគ្រប់គ្រងជាន់ខ្ពស់ (ការផ្ទៀងផ្ទាត់បន្ថែម) |

(`confirmSuspend` currently has Latin letters inside the Khmer word for "session"; `tipStepUp` currently keeps `super-admin (step-up)`
in Latin, while `feature-flags.js` already uses "អ្នកគ្រប់គ្រងជាន់ខ្ពស់" for super-admin.)

## 3. Notes for the native reviewer (not for the agent)

- I left `feature-flags.js` `title` (`ទងជម្រើសមុខងារ`) and `users.js` `impersonate` (`សាកល្បងក្នុងនាម`) untouched. The first starts
  with a word I could not confirm; the second reads as "try in the name of" rather than "impersonate". Both are worth a look.
- Digits are Arabic as in the English source (`30 នាទី`); the Khmer-numeral toggle (plan LT-2.2) is a separate feature.
