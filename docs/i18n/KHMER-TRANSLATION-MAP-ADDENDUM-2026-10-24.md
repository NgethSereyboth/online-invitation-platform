# Khmer translation map — ADDENDUM (2026-10-24)

**Purpose:** Khmer for the 42 unique strings (72 slots, 12 pages) that `docs/i18n/KHMER-GAP-SHARED-HEADER-2026-10-24.md`
found still rendering English inside `<span class="i18n-km">` slots — mostly the shared header and page furniture.
Used by plan item **LT-1.2** of `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` (it was FB-64 of the superseded round-5 order).

**Authorship and status:** same arrangement as `KHMER-TRANSLATION-MAP-2026-10-24.md`. Claude drafted this Khmer at the
owner's standing request; Claude is not a native Khmer speaker; every row is a **draft for native review** (OD-18).
The agent applies it exactly, lists every applied string in `docs/i18n/KHMER-REVIEW-QUEUE.md`, and does not review,
reword or extend it.

## 0. Rules (identical to the main map's §0, plus three)

1. **Paste, never generate.** Parse the tables with `tools/i18n-apply-khmer-map.py` (extend it to read this file too;
   do not copy Khmer by hand). Rules 2–8 of the main map's §0 apply unchanged (match by `(file, EN)` after trimming,
   keep placeholders, keep Latin tokens, never touch keys or classes, edit `src/` only, regenerate the CSV with the
   repo tools, anything not listed stays English).
2. **HTML entities.** The gap audit shows `Plans &amp; usage` in `billing.html` and `Style & motion` in `index.html`.
   Compare after decoding HTML entities on both sides, and write the Khmer back without entities. This is the likely
   reason `billing.html`'s row (already in the main map) did not match before: say so in the evidence if it is.
3. **Shared header slots.** `Workspace` and `Plans` occur in the header of 10 pages. If the header is built once in a
   shared JS module and not per page, apply the row **once at the source** and list the module in the evidence; the
   per-page sections below then report `matched via shared source`. If it is per page, apply per page.
4. **New Latin token:** `Canva` (only in the one row marked below). It must be separated from Khmer letters by a space.

## 1. Shared header and page furniture

### `src/html/account.html`
| EN | KM |
|---|---|
| Workspace | កន្លែងធ្វើការ |
| Plans | គម្រោង |
| Passkeys | Passkey |

### `src/html/admin.html`
| EN | KM |
|---|---|
| Workspace | កន្លែងធ្វើការ |
| Plans | គម្រោង |
| Administration | ការគ្រប់គ្រងប្រព័ន្ធ |

### `src/html/analytics.html`
| EN | KM |
|---|---|
| Workspace | កន្លែងធ្វើការ |
| Plans | គម្រោង |
| Analytics | ការវិភាគ |

### `src/html/billing.html`
| EN | KM |
|---|---|
| Workspace | កន្លែងធ្វើការ |
| Plans | គម្រោង |
| Plans & usage | គម្រោង និងការប្រើប្រាស់ |

### `src/html/checkin.html`
| EN | KM |
|---|---|
| Online | អនឡាញ |

### `src/html/designer.html`
| EN | KM |
|---|---|
| Workspace | កន្លែងធ្វើការ |
| Plans | គម្រោង |
| Designer | អ្នករចនា |

### `src/html/guests.html`
| EN | KM |
|---|---|
| Workspace | កន្លែងធ្វើការ |
| Plans | គម្រោង |
| Event Check-in | ការចុះឈ្មោះចូលព្រឹត្តិការណ៍ |

### `src/html/materials.html`
| EN | KM |
|---|---|
| Workspace | កន្លែងធ្វើការ |
| Plans | គម្រោង |
| Delete | លុប |

### `src/html/responses.html`
| EN | KM |
|---|---|
| Workspace | កន្លែងធ្វើការ |
| Plans | គម្រោង |

### `src/html/templates.html`
| EN | KM |
|---|---|
| Workspace | កន្លែងធ្វើការ |
| Plans | គម្រោង |
| Template Studio | ស្ទូឌីយោគំរូ |
| ＋ New poster | ＋ ប៉ូស្ទ័រថ្មី |

## 2. Dashboard

### `src/html/dashboard.html`
| EN | KM |
|---|---|
| Workspace | កន្លែងធ្វើការ |
| Plans | គម្រោង |
| Welcome back | សូមស្វាគមន៍ត្រឡប់មកវិញ |
| Sign in to continue working on your invitations and events. | ចូលគណនីដើម្បីបន្តធ្វើការលើការអញ្ជើញ និងព្រឹត្តិការណ៍របស់អ្នក។ |
| Sign out | ចាកចេញ |
| or | ឬ |
| Design invitations that feel premium, personal, and alive. | រចនាការអញ្ជើញដែលមានអារម្មណ៍ប្រណីត ផ្ទាល់ខ្លួន និងរស់រវើក។ |
| Khmer + English, light + dark, publish-ready pages | ខ្មែរ + អង់គ្លេស ភ្លឺ + ងងឹត ទំព័រដែលរួចរាល់សម្រាប់ផ្សព្វផ្សាយ |
| Guest list, RSVP responses and analytics in one workspace | បញ្ជីភ្ញៀវ ការឆ្លើយតប RSVP និងការវិភាគ ក្នុងកន្លែងធ្វើការតែមួយ |
| Canva-like design studio for invitations and posters | ស្ទូឌីយោរចនាបែប Canva សម្រាប់ការអញ្ជើញ និងប៉ូស្ទ័រ |
| Designer Workspace | កន្លែងធ្វើការរបស់អ្នករចនា |
| Marketplace | ទីផ្សារ |
| My invitations | ការអញ្ជើញរបស់ខ្ញុំ |
| My templates | គំរូរបស់ខ្ញុំ |
| ★ Favorites | ★ ចំណូលចិត្ត |
| Create invitation | បង្កើតការអញ្ជើញ |
| Create from template | បង្កើតពីគំរូ |
| Use this template | ប្រើគំរូនេះ |
| Invitation name | ឈ្មោះការអញ្ជើញ |
| Event type | ប្រភេទព្រឹត្តិការណ៍ |
| Cancel | បោះបង់ |
| Close | បិទ |
| Built-in templates now include page structure, palette, section styling, animation, and visual-page layouts. Invitations saved as your own templates appear here too. | គំរូដែលមានស្រាប់ឥឡូវនេះរួមមានរចនាសម្ព័ន្ធទំព័រ ក្រុមពណ៌ រចនាប័ទ្មផ្នែក ចលនា និងប្លង់ទំព័រមើលឃើញ។ ការអញ្ជើញដែលបានរក្សាទុកជាគំរូផ្ទាល់ខ្លួនក៏បង្ហាញនៅទីនេះដែរ។ |

**Conditional row — APPROVED (OD-28, decided in `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` §3): apply it.** It replaces the row above for the same
slot and also changes the *English* text of that slot to the EN column below (English is the agent's to write; the Khmer is pasted).

| EN (new English text) | KM |
|---|---|
| Design studio for invitations and posters | ស្ទូឌីយោរចនាសម្រាប់ការអញ្ជើញ និងប៉ូស្ទ័រ |

## 3. Editor

### `src/html/index.html`
| EN | KM |
|---|---|
| Undo | មិនធ្វើវិញ |
| Redo | ធ្វើឡើងវិញ |
| Guest preview | ការមើលជាមុនសម្រាប់ភ្ញៀវ |
| Publish snapshot | ផ្សព្វផ្សាយកំណែបច្ចុប្បន្ន |
| Canvas zoom | ការពង្រីកផ្ទាំង |
| Filter materials | ត្រងសម្ភារៈ |
| Local mode | របៀបមូលដ្ឋាន |
| Style & motion | រចនាប័ទ្ម និងចលនា |
| Untitled design | ការរចនាគ្មានចំណងជើង |

## 4. Terminology rows — APPROVED (OD-20, decided in the long-term plan §3): apply them (plan item LT-1.2)

The main map's term base uses **គំរូ** for "template"; the dashboard tile and `admin.html` still use `ពុម្ពអត្ថបទ`
("text template"), so one page shows both words for one thing. LT-1.2 replaces every visible
`ពុម្ពអត្ថបទ` that stands for "template" with `គំរូ`, **by script, from this line**, and lists each occurrence.
It must not touch `ពុម្ពអក្សរ` (typeface) or any other word that merely contains the same letters.

| Replace | With |
|---|---|
| ពុម្ពអត្ថបទ | គំរូ |

## 5. Notes for the native reviewer (not for the agent)

- Choices you may want to change globally: **កន្លែងធ្វើការ** for "Workspace", **គម្រោង** for "Plans",
  **មិនធ្វើវិញ / ធ្វើឡើងវិញ** for Undo / Redo, **ការគ្រប់គ្រងប្រព័ន្ធ** for "Administration",
  **ក្រុមពណ៌** for "palette", **ប្រណីត** for "premium".
- `Passkeys` is shown as the Latin token `Passkey` (the main map keeps Passkey Latin); drop the plural.
- Digits and `+` signs are kept exactly as in the English.
