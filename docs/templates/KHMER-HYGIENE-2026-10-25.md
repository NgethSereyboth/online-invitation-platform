# Khmer hygiene — template pack (TP-6.1)

Evidence recorded on 2026-10-26 against the built pack in `assets/template-pack/`.
Commands are reproducible from the repo root.

## 1. Repo bilingual consistency

```
.venv/bin/python scripts/check-bilingual-consistency.py
```

Result: `OK: bilingual consistency check passed.` (same run also lists every remaining
`[PLACEHOLDER]` string in the app; those are pre-existing and outside the pack.)

## 2. Khmer scan and copy provenance

```
.venv/bin/python -m pytest tests/test_template_pack.py -q
```

Result: `12 passed`. Among those tests:

- `test_no_placeholder_content_leaks_a_real_identity` — no phone number, email or
  invented person in any built document.
- the repo-wide Khmer scan — no Khmer code point outside the allowed set
  (`docs/i18n/**`, `template-pack/copy-bank.json`, `template-pack/KHMER-COPY-MAP.md`,
  `assets/template-pack/built/*.js`, and the files that already carried Khmer before
  this order). `tools/build-template-pack.py` itself contains no Khmer.
- `test_ornaments_exist_are_small_and_safe` — 27 procedural SVGs, ≤ 12 KB, no
  `!important`, `<script>`, `on*=` handler or external URL.

## 3. Word breaks and letter-spacing in the built documents

Scan of all 453 text objects across the 36 built documents:

| Check | Result |
|---|---|
| Khmer strings longer than 18 code points without U+200B | 0 |
| Khmer text objects with `letterSpacing ≠ 0` | 0 |
| Khmer text objects at all | 240 |

The U+200B break survives conversion because the converter copies strings from
`copy-bank.json` byte-for-byte; it never re-types or normalises them.

## 4. Review queue coverage

`docs/i18n/KHMER-REVIEW-QUEUE.md` gained a **Khmer event template pack (TP-6.1)**
section with one row per copy-bank key: 117 rows for 117 keys. Each key appears in
exactly one dedicated row (`key \`<key>\``); three keys are substrings of longer keys
(`ny.title` in `gny.title`, `ny.wish` in `gny.wish`, `label.host` in
`label.hosted_by`), which is why a naive substring count reports 2.

## 5. Rendered Khmer

Acceptance run A4 (`tools/accept-template-pack.py`, 36 templates) records, per text
object: the computed family stack, font size, letter-spacing and line-height. Every
Khmer object renders from the bundled `EInvite Noto Serif Khmer` (or
`EInvite Noto Sans Khmer` for the modern register) first in the stack, with
`letter-spacing: normal`, never a fallback-only stack. The rendered line-height is the
registered face's recommendation (1.6) rather than the pack's 1.75–1.95 design value;
that is recorded as **deviation #1** in `ACCEPTANCE-2026-10-25.md` and queued for the
typography owner, because changing it moves every Khmer document in the app.

## 6. What is still open

- A native speaker has not reviewed the 117 pack strings (they came from the pack's
  own copy bank). The queue rows are the review surface.
- The Moul/Moulpali/Koulen/Battambang families are substituted by the registered Noto
  faces; see `FONT-GAP-2026-10-25.md` and `FONT-SUBSTITUTIONS.md`.
