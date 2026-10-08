# v54 Khmer gate — re-derived 11-string table

**Dispatch:** V54-RC §5 · **Date:** 2026-10-05 · **Method:** every Khmer string below was
copy-pasted from command output (`git diff HEAD -- src/html/index.html` parsed by
`%TEMP%\einvite-platform\v54rc-khmer-extract.py`, output saved to
`%TEMP%\einvite-platform\v54rc-khmer-extract.txt`; CSV cross-check from
`docs/i18n/TRANSLATIONS.csv` read via `utf-8-sig`). No Khmer was typed by hand.

## Derivation

```
$ git diff HEAD -- src/html/index.html
  total added/changed lines: 48
  added/changed lines containing Khmer U+1780-U+17FF: 11
```

Working-tree lines carrying Khmer (full-file grep): 75, 84, 86, 87, 88, 89, 90, 91,
207, 278, 300, 301 (12 lines). Line 75 is the mobile banner, **unchanged vs HEAD**
(it is not a diff line), so the changeset adds/modifies exactly **11** Khmer lines:
84, 86, 87, 88, 89, 90, 91 (new), 207, 278 (pre-existing `EN / KM` labels restructured
into i18n span pairs — same Khmer values as the removed lines), 300, 301 (new).

Two removed lines carried the pre-existing Khmer for lines 207/278:

```
-        <label class="sr-only" for="assetTypeFilter">Filter materials / តម្រងសម្ភារៈ</label><select ...
-        <label class="sr-only" for="zoomLevel">Canvas zoom / ពង្រីកផ្ទាំងគំរូ</label><select ...
```

## 11-string table

| # | file | line (WT) | key | EN (context) | Khmer current (verbatim from diff) | Intended meaning (from label) | CSV row (line in CSV) | CSV status |
|---|------|-----------|-----|--------------|------------------------------------|-------------------------------|-----------------------|------------|
| 1 | src/html/index.html | 84 | `header.more-summary` | More | ច្រើនជាងមួយចំនោទំព័ឹន | "More" (canvas-header dropdown) | 84 | translated |
| 2 | src/html/index.html | 86 | `saveState` | Saved locally | រក្សាទុកភ្ជាដេស៊ូរ | "Saved locally" (save-state chip) | 86 | translated |
| 3 | src/html/index.html | 87 | `serverState` | Local mode | របៀបភ្ជាដេស៊ូរ | "Local mode" (server-state chip) | 87 | translated |
| 4 | src/html/index.html | 88 | `undoBtn` | Undo (`title="Undo (Ctrl+Z)"`) | ថម្ងម់កម្រ | "Undo" (undo button) | 88 | translated |
| 5 | src/html/index.html | 89 | `redoBtn` | Redo (`title="Redo (Ctrl+Y)"`) | ធ្វើបន្ថែម | "Redo" (redo button) | 89 | translated |
| 6 | src/html/index.html | 90 | `previewBtn` | Guest preview | មើលចាស់ | "Guest preview" (preview button) | 90 | translated |
| 7 | src/html/index.html | 91 | `publishBtn` | Publish snapshot | ច្រើម | "Publish snapshot" (primary publish button) | 91 | translated |
| 8 | src/html/index.html | 207 | `assetTypeFilter` sr-only label | Filter materials | តម្រងសម្ភារៈ | "Filter materials" (screen-reader label) | 206 (pre-G1 numbering) | translated |
| 9 | src/html/index.html | 278 | `zoomLevel` sr-only label | Canvas zoom | ពង្រីកផ្ទាំងគំរូ | "Canvas zoom" (screen-reader label) | 277 (pre-G1 numbering) | translated |
| 10 | src/html/index.html | 300 | inspector heading | Style & motion | រ៉ញម្ញានង់ | "Style & motion" (inspector panel heading) | 299 (pre-G1 numbering) | translated |
| 11 | src/html/index.html | 301 | `#noSelection` placeholder | Select an object on the canvas to edit its properties. | ចង់ផ្តល់សំបកអំពីគ្របៅគាំបូងសម្រាប់កើតោមានភាពសំបក។ | No-selection placeholder text | 300 (pre-G1 numbering) | translated |

Full-line context (verbatim from the extraction, each line is a single source line):

| line | full line (verbatim) |
|------|----------------------|
| 84 | `    <div class="canvas-header-more"><summary><span class="i18n i18n-en">More</span><span class="i18n i18n-km khmer-text" lang="km">ច្រើនជាងមួយចំនោទំព័ឹន</span></summary></div>` |
| 86 | `      <span id="saveState"><span class="i18n i18n-en">Saved locally</span><span class="i18n i18n-km khmer-text" lang="km">រក្សាទុកភ្ជាដេស៊ូរ</span></span>` |
| 87 | `      <span id="serverState"><span class="i18n i18n-en">Local mode</span><span class="i18n i18n-km khmer-text" lang="km">របៀបភ្ជាដេស៊ូរ</span></span>` |
| 88 | `      <button id="undoBtn" title="Undo (Ctrl+Z)"><span class="i18n i18n-en">Undo</span><span class="i18n i18n-km khmer-text" lang="km">ថម្ងម់កម្រ</span></button>` |
| 89 | `      <button id="redoBtn" title="Redo (Ctrl+Y)"><span class="i18n i18n-en">Redo</span><span class="i18n i18n-km khmer-text" lang="km">ធ្វើបន្ថែម</span></button>` |
| 90 | `      <button id="previewBtn"><span class="i18n i18n-en">Guest preview</span><span class="i18n i18n-km khmer-text" lang="km">មើលចាស់</span></button>` |
| 91 | `      <button id="publishBtn" class="primary"><span class="i18n i18n-en">Publish snapshot</span><span class="i18n i18n-km khmer-text" lang="km">ច្រើម</span></button>` |
| 207 | `        <label class="sr-only" for="assetTypeFilter"><span class="i18n i18n-en">Filter materials</span><span class="i18n i18n-km khmer-text" lang="km">តម្រងសម្ភារៈ</span></label><select id="assetTypeFilter" aria-label="Filter materials"><option value="image">Images</option><option value="audio">Audio</option><option value="video">Video</option><option value="favorites">Favorites</option><option value="all">All materials</option></select>` |
| 278 | `        <label class="sr-only" for="zoomLevel"><span class="i18n i18n-en">Canvas zoom</span><span class="i18n i18n-km khmer-text" lang="km">ពង្រីកផ្ទាំងគំរូ</span></label><select id="zoomLevel" aria-label="Canvas zoom"><option value="0.5">50%</option><option value="0.75">75%</option><option value="1" selected>100%</option><option value="1.25">125%</option><option value="1.5">150%</option><option value="2">200%</option></select>` |
| 300 | `        <h2 class="studio-inspector-heading"><span class="i18n i18n-en">Style & motion</span><span class="i18n i18n-km khmer-text" lang="km">រ៉ញម្ញានង់</span></h2>` |
| 301 | `        <div id="noSelection" class="empty v54-inspector-placeholder"><span class="i18n i18n-en">Select an object on the canvas to edit its properties.</span><span class="i18n i18n-km khmer-text" lang="km">ចង់ផ្តល់សំបកអំពីគ្របៅគាំបូងសម្រាប់កើតោមានភាពសំបក។</span></div>` |

## CSV snippet (columns per dispatch; `khmer_proposed` left blank for the user)

```csv
file,line,key,khmer_current,khmer_proposed,notes
src/html/index.html,84,header.more-summary,ច្រើនជាងមួយចំនោទំព័ឹន,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,86,saveState,រក្សាទុកភ្ជាដេស៊ូរ,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,87,serverState,របៀបភ្ជាដេស៊ូរ,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,88,undoBtn,ថម្ងម់កម្រ,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,89,redoBtn,ធ្វើបន្ថែម,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,90,previewBtn,មើលចាស់,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,91,publishBtn,ច្រើម,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,207,assetTypeFilter-label,តម្រងសម្ភារៈ,,restructured from 'EN / KM' label; Khmer unchanged; in CSV status=translated
src/html/index.html,278,zoomLevel-label,ពង្រីកផ្ទាំងគំរូ,,restructured from 'EN / KM' label; Khmer unchanged; in CSV status=translated
src/html/index.html,300,inspector.heading,រ៉ញម្ញានង់,,new in v54 diff; in TRANSLATIONS.csv status=translated
src/html/index.html,301,noSelection.placeholder,ចង់ផ្តល់សំបកអំពីគ្របៅគាំបូងសម្រាប់កើតោមានភាពសំបក។,,new in v54 diff; in TRANSLATIONS.csv status=translated
```

## TRANSLATIONS.csv location & coverage

- `git grep -n "TRANSLATIONS.csv" -- .` → referenced by tracked
  `scripts/check-bilingual-consistency.py` (lines 27, 951, 1003).
- File: `docs/i18n/TRANSLATIONS.csv` (untracked, 151,483 bytes, 1,150 lines).
- Header (verbatim): `"text","key","en","km","status","file","line"`
- First 5 data rows (verbatim):

```csv
"span","span","Skip to content","Skip to content","fallback","src/html/account.html","9"
"span","span","Dashboard","Dashboard","fallback","src/html/account.html","9"
"span","span","Plans & usage","Plans & usage","fallback","src/html/account.html","9"
"span","span","Account settings","Account settings","fallback","src/html/account.html","9"
"span","span","Manage account security and export a portable copy of your platform data.","Manage account security and export a portable copy of your platform data.","fallback","src/html/account.html","9"
```

- Coverage of the 11 strings: **all 11 present**, `status=translated`, and each CSV
  `km` value matches the working-tree HTML byte-for-byte (verified by
  `%TEMP%\einvite-platform\v54rc-csv-check.py`). The 12th (line 74 CSV / line 75 WT,
  the mobile banner) is also present and matches; it is not part of this diff.
- Note: CSV `line` values for lines ≥ 206 are one less than the current working-tree
  line numbers, exactly consistent with the CSV having been generated before the G1
  one-line restore at line 99 (all CSV lines ≥ 99 are offset −1; lines 74–91 match).

## Judgment placeholder

The strings were generated by the prior i18n pipeline and recorded in
TRANSLATIONS.csv as `translated`; their linguistic correctness is **UNKNOWN**
(predecessor G1 report U3 already flagged several as machine-generated-looking,
e.g. `Undo → ថម្ងម់កម្រ`, `Publish snapshot → ច្រើម`). The `khmer_proposed` column
is intentionally blank for the user to fill in. No Khmer in this file was invented.
