# How to add a template to the Khmer pack

This is the procedure for adding template 37. It assumes the pack's design source is
present (`template-pack/`) and that you are not changing the app's renderer.

There are two routes. Use **A** when the generator runs on your machine (Pillow with
Raqm, cairosvg, Node); use **B** when it does not, which is the case in the repo venv
(see TP-OD-2). Route B edits one template's layer numbers directly and logs the
deviation.

## A. Generator route (preferred)

1. **Write the copy.** Add the strings to `template-pack/copy-bank.json` under a new
   key with `km` and `en`. Khmer strings must carry U+200B at word boundaries, no
   letter-spacing, no Latin inside a Khmer string (placeholders in `[ ]` are fine).
   Never type Khmer in a script or a layer file.
2. **Add the catalogue entry.** `template-pack/catalog.json`: `id` (lowercase,
   hyphenated, must not collide with an existing or built-in template), `name.en`,
   `name.km`, `category` (one of `wedding`, `birthday`, `ceremony`, `greeting`,
   `business`), `canvas` (`a5p`, `p45`, `sq`, `story`), `tags`, palette roles.
3. **Add the layer file.** `template-pack/templates/<id>.json`: ordered layers per
   page. Layers name palette roles, never hex. A text layer uses `copy` (a key from
   step 1) or `literal` for non-Khmer glyphs (`&`, `·`); `lang` is `km` or `en`;
   `slot` marks owner-editable fields. `x/y/w/h` are percentages of the canvas;
   `size`, `strokeWidth`, `radius`, `tile` are pixels at the declared canvas width.
4. **Pick the opening scene and style kit.** Use the closest existing option from
   `FREEBUFF-TEMPLATES-WORKORDER-2026-10-25.md` Appendix D. Never invent a scene id.
   Memorial, sympathy, Pchum Ben, Kathina, merit and get-well always take the
   quietest option (`minimal-editorial`); birthdays take the playful one.
5. **Design-time check.** `python3 template-pack/generator/lint.py` must report
   0 errors. It checks contrast, safe area, text overlap, copy keys, ornament files,
   Khmer line-height, minimum size and Khmer-in-source.
6. **Build.** `PACK_FONTS=<dir of the 14 TTFs> python3 template-pack/generator/build_pack.py --write`
   writes the pack's own JSON; then
   `.venv/bin/python tools/build-template-pack.py` converts it to the app's native
   documents and writes `assets/template-pack/catalog.js` and `built/<id>.js`.
   `--check` must pass afterwards and must not rewrite unchanged files.
7. **Rebuild the app mirrors.** `python3 build.py mirror` (the server serves from
   `src/python/`), then `python3 build.py bundles --check`.
8. **Thumbnail.** `.venv/bin/python tools/render-template-thumbs.py --only <id>`.
   The WebP must be ≤ 40 KB, 420 px wide, rendered in the real editor.
9. **Accept.** Add the id to `BATCHES` in `tools/accept-template-pack.py`, run
   `.venv/bin/python tools/accept-template-pack.py --ids <id>`, and record the
   A1–A12 row in `ACCEPTANCE-2026-10-25.md`. A fail is fixed in the design source,
   never by weakening the check.
10. **Document.** Add the row to `CATALOG.md` and the cultural checklist, then run
    `python3 build.py all --check` and the pack tests
    (`pytest tests/test_template_pack.py tests/template_pack_gallery_test.py tests/template_pack_loader_test.py -q`).

## B. Hand-edit route (no generator)

1. Copy `template-pack/templates/<nearest>.json` to `<id>.json` and add the catalogue
   entry as above.
2. Adjust layer numbers (spacing, size, wrap) directly in the copy. Do not recolour
   and do not re-compose; the design review's fix budget is spacing, size, wrap and
   collisions only.
3. Convert with `tools/build-template-pack.py`, then follow steps 7–10.
4. Add a line to `OWNER-QUEUE` titled `TODO: regenerate <id>` so the generator can be
   re-synced later, and mark the template `hand-edited` in the deviation log.

## Rules that the converter enforces

- `--check` fails when any built file is stale; CI runs it.
- No Khmer in `tools/build-template-pack.py`; it only copies strings.
- Ornaments are sanitised: no `!important`, no `<script>`, no `on*=` handlers, no
  external URL, ≤ 12 KB each.
- Colour is never hex in the pack source; the converter maps palette roles to hex.
- The built document uses the same schema as every other invitation, so exported
  files and the guest page need no pack-specific code.

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `--check` fails after a `git checkout` | mirror or built output is older than the source | rebuild; the checks compare content, not timestamps |
| Gallery card shows no thumbnail | WebP missing or over 40 KB | rerun `render-template-thumbs.py --only <id>` |
| Khmer clipped in a text box | line-height raised after the design was measured | enlarge the box or reduce `size` in the layer file, rebuild |
| Export shows objects in the wrong box | stale served JS after editing `src/js` | `python3 build.py mirror` |
| Picker does not list the template | `catalog.js` count/entry mismatch | run `tools/build-template-pack.py`, check `catalog.js` |
