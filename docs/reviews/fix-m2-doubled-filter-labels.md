# The materials and responses filters read every label twice

Scope: the two library filter `<select>`s on `materials.html` (`#typeFilter`, `#sort`),
the RSVP status filter on `responses.html` (`#responseFilter`), and the empty-state
option `materials.js` injects into the upload dialog.

The reported symptom for this region was a spacing problem in the materials toolbar.
The spacing measurement did not reproduce — see
[`no-repro-e2-m1-m2-spacing.md`](no-repro-e2-m1-m2-spacing.md). What the toolbar did show
was this: every option rendered its label twice — "All typesAll types", "Newest
firstNewest first" — visible in [`before-m1.png`](before-m1.png).

## 1. Cause

Each option held the platform's bilingual pair of `<span>`s. `<option>` cannot contain
elements: the HTML parser discards a start tag it does not expect inside a `select`, so
the EN and KM strings survive as *text* and concatenate inside one option. The
`.i18n-en`/`.i18n-km` hiding convention that makes those pairs work everywhere else
(`organized/styles.css`: `[lang="km"] .i18n-en{display:none}`) needs real elements, so it
can never apply inside an option.

The Khmer halves are countable, and the counts drop by exactly the number of options
converted:

```
$ git show HEAD:src/html/materials.html | grep -o 'class="i18n i18n-km khmer-text" lang="km"' | wc -l
40
```

```
$ grep -o 'class="i18n i18n-km khmer-text" lang="km"' src/html/materials.html | wc -l
30
```

```
$ git show HEAD:src/html/responses.html | grep -o 'class="i18n i18n-km khmer-text" lang="km"' | wc -l
17
```

```
$ grep -o 'class="i18n i18n-km khmer-text" lang="km"' src/html/responses.html | wc -l
15
```

Twelve static options carried the pattern (10 in `materials.html`, 2 in `responses.html`)
plus one the script builds:

```
$ git show HEAD:src/js/materials.js | grep -o "Create an invitation first"
Create an invitation first
Create an invitation first
```

```
$ grep -o "Create an invitation first" src/js/materials.js
Create an invitation first
```

In all thirteen the KM string is identical to the EN string — the Khmer copy in this
toolbar lives on the real, hidden `<label>`s ("ប្រភេទសម្ភារៈ", "តម្រៀបតាម"), which are
elements and were never affected. So no translation was lost by making the option labels
plain text, and no Khmer was invented to fill the gap.

## 2. The fix

Plain text, with the constraint written down where the next person will meet it
(`src/html/materials.html`):

```html
<!-- NOTE: <option> cannot contain elements — the HTML parser drops a <span>
     inside it and concatenates the surviving text, which is how these filter
     labels came to read "All typesAll types". Option labels are plain text
     (the EN and KM strings in this toolbar are identical; the Khmer copy
     lives on the sr-only <label>s, which are real elements). -->
```

Files touched: `src/html/materials.html` (10 options), `src/html/responses.html`
(2 options), `src/js/materials.js` (1 injected option). No CSS was involved: the change
removes invalid markup instead of styling around it.

The count of Khmer carriers in the two files drops by exactly the number of options
converted (10 and 2), and the last `lang="km"` left inside the materials toolbar
belongs to the sr-only `<label>`s, not to an option:

```
$ grep -o 'lang="km"' src/html/materials.html | wc -l
30
```

```
$ grep -o 'lang="km"' src/html/responses.html | wc -l
15
```

## 3. Verification

<!-- report-verify: measurement needs the dev server and a browser; the values are one run's rendered DOM -->

Rendered option labels read back from the live pages through `agent-browser`:

| page | element | rendered option labels |
| --- | --- | --- |
| materials.html | `#typeFilter` | All types, Images, Audio, Video, Fonts, Favorites |
| materials.html | `#sort` | Newest first, Oldest first, Name A–Z, Largest first |
| responses.html | `#responseFilter` | All statuses, Attending, Declined, Maybe |

Each list equals its own first half (no doubled string), the selected values render as
"All types" and "Newest first", and the option markup the browser kept is the valid
single-text form `<option value="all">All types</option>`.

[`after-m1.png`](after-m1.png) is the same 1440px toolbar crop as `before-m1.png`:
"Search name, folder, or tags…", "All types", "Folder", "Newest first", each label once.
[`after-m1-390.png`](after-m1-390.png) is the 390px one — see
[`no-repro-e2-m1-m2-spacing.md`](no-repro-e2-m1-m2-spacing.md) §4 for the separate
narrow-viewport problem visible in that crop.

## 4. What was not verified

- Khmer rendering of these labels was not checked, because there is no Khmer text there:
  with `<html lang="km">` the labels are the same strings (`All types`, `Newest first`,
  …). If real Khmer is added later, `<option>` still cannot hold the `.i18n` spans, so
  the fix has to be plain KM text or a `data-en`/`data-km` attribute read by
  `core/i18n.js` — and that module currently applies those attributes to
  `INPUT`/`TEXTAREA`/`SELECT` only, not to `OPTION`.
- The upload dialog's empty-invitation-list state was checked in the source and against
  the fixed pattern, but not produced in the browser: the review account has invitations,
  so `materials.js` never injects that option in this session.
- `bundle-materials-v15.js` carries the built copy of `materials.js`; the pages were
  re-verified after `python3 build.py all` re-synced it, not before.
