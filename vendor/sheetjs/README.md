# vendor/sheetjs — SheetJS, vendored for the guest-list import

**What is here.** `xlsx.mini.min.js` from npm `xlsx@0.18.5`
(<https://registry.npmjs.org/xlsx>, tarball `xlsx-0.18.5.tgz`, 2,441,660 bytes),
250,826 bytes after minification, sha256 in `INTEGRITY.txt`. Apache-2.0
(<https://unpkg.com/xlsx@0.18.5/package.json>), licence text in `LICENSE.txt`.

**Why the `mini` build.** The SheetJS README for this exact version describes what
`dist/xlsx.mini.min.js` omits — "no support for XLSB / XLS / Lotus 1-2-3 /
SpreadsheetML 2003 / Numbers"
(<https://unpkg.com/xlsx@0.18.5/README.md>) — and `.xlsx` is not in that list, so
the mini build reads the one format the import needs. `xlsx.full.min.js` is
881,727 bytes in the same tarball and buys nothing here.

**Why it is loaded lazily and not bundled.** `src/js/build/build_page_manifests.py`
counts every `<script src>` in a page against the route budget, and the
`event-operations` route (which owns `guests.html`) is budgeted at 3 scripts and
440,000 bytes (`src/python/build/build_page_manifests.py`, `BUDGETS`). A fourth
script tag or a 250 KB addition to `bundle-guests-v15.js` breaks that gate for a
format most guest lists never arrive in. `guests.js` therefore fetches this file
with a `document.createElement('script')` only when a `.xlsx`/`.xls` file is
actually chosen (`loadSheetJs()`), which is the same second-stage-loading pattern
`photo-style-library-v23.js` already uses. The file is served from `vendor/`,
which `server.public_static_path()` already allow-lists for `.js`.

**Usage.** The global is `XLSX`:

```js
const workbook = XLSX.read(new Uint8Array(await file.arrayBuffer()));
const sheet = workbook.Sheets[workbook.SheetNames[0]];
const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, blankrows: false, defval: '' });
```

`type: 'array'` is not needed for a `Uint8Array` or `ArrayBuffer`
(<https://docs.sheetjs.com/docs/demos/local/file/>, and `header: 1` is documented
to produce an array of arrays at
<https://docs.sheetjs.com/docs/getting-started/examples/import/>).

**Staying current.** Bump by re-downloading the tarball, replacing
`xlsx.mini.min.js` and `LICENSE.txt`, regenerating `INTEGRITY.txt`
(`python3 -c "import hashlib,pathlib; p=pathlib.Path('vendor/sheetjs/xlsx.mini.min.js'); print('xlsx.mini.min.js', p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())"`)
and running `python3 build.py mirror`.
