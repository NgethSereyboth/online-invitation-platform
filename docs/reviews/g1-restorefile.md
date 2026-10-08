# G1 — `#restoreFile` null at `src/js/bundle-index-v15.js:5386`

**Dispatch:** G1, issued 2026-10-05 · **Report:** 2026-10-05 · **Executing agent:** DSH web session (Qwen model), working tree as explicit baseline (see §2)

---

## 1. Decision summary

G1 is a real, confirmed, **Critical**-severity defect: on load of the editor page, `$('#restoreFile').onchange=…` executes at the top level of the single bundle script; `document.querySelector('#restoreFile')` returns `null` (the hidden file input is absent from the served `index.html`), so the assignment throws `TypeError: Cannot set properties of null (setting 'onchange')` at `bundle-index-v15.js:5386`, aborting the remainder of the bundle (the tail of `app.js` plus the 37 source modules concatenated after it, including `editor/editor-core.js`). **Contrary to the prior report's framing ("element missing from HTML"), no commit ever removed the element:** `id="restoreFile"` is present in all 50 tracked revisions that contain `src/html/index.html`, including HEAD (line 78). The removal is **uncommitted working-tree state**: a prior session's uncommitted v54 header rewrite of `src/html/index.html` (+47/−12 at session start) replaced the flat header (which contained `<input id="restoreFile" type="file" accept="application/json" hidden>`) with the new `studio-topbar` structure and dropped the input while keeping the `Restore` button and all of its JS. Decision rule §3 therefore points to **§4A — element was removed (collaterally, by template rewrite, in the working tree)**: the backup/restore feature, its button and its handler code were all retained; only the hidden sibling input was lost. **Fix applied:** one line restored into `src/html/index.html` (new line 99, exact attribute string of every committed ancestor), propagated to the served tree by the project's own `sync_frontend_assets.py` (byte-identical copy verified by SHA-256); no JS source changed, so no bundle rebuild was required (`build_route_bundles.py --check` → `ROUTE_BUNDLE_CHECK_PASSED` before and after). **Verification (Puppeteer 25.12.0 + headless Chromium/Edge on a static server on port 8001):** the same repro command run before the fix shows the exact 5386 TypeError with `restoreFilePresent:false`; after the fix the 5386 error is gone, `restoreFilePresent:true`, and previously-blocked code demonstrably runs (`#khmerDay` options 0→15, `window.typographyLayoutController` undefined→function). **Caveat (scope):** the after-fix run still surfaces one pageerror — a *different*, pre-existing bug: `NotFoundError … insertBefore` at `bundle-index-v15.js:5527` (source `src/js/studio-experience.js:29`), already documented as the "Pass 1" residual in the prior report. Per dispatch scope it is logged, not fixed.

---

## 2. Ground

| Item | Value | Evidence |
|---|---|---|
| cwd | `F:\eInvite\einvite-platform` | **FACT** — `Get-Location` raw output (§0 run) |
| repo root | `F:/eInvite/einvite-platform` (matches expected) | **FACT** — `git rev-parse --show-toplevel` |
| HEAD | `133d3647eb4a095337b7492e864c9acba94e1b35` ("sec: add IP allowlist gate for admin routes (ROADMAP §4.2a)") | **FACT** — `git rev-parse HEAD`, `git log -5 --oneline` |
| Initial `git status --porcelain` | **non-empty: 125 modified tracked entries + 372 untracked entries = 497 lines** | **FACT** — counts from `(git status --porcelain \| Where-Object …).Count`; full snapshot saved to `%TEMP%\dsh-3T93Ot\g1-initial-status.txt` |

§0 mandates STOP on a dirty tree. That stop was made and reported to the issuer; the issuer then explicitly approved proceeding with **the working tree as the documented baseline** (user question `g1_dirty_tree`, answer "Proceed, working tree as explicit baseline"). All findings below are relative to that working tree, not to HEAD.

Characterization of the pre-existing dirt (all read-only evidence, **FACT** unless noted):

- Both G1 target files were themselves dirty: `git diff --stat -- src/html/index.html` → `1 file changed, 47 insertions(+), 12 deletions(-)`; `git diff --stat -- src/js/bundle-index-v15.js` → `1 file changed, 425 insertions(+), 12 deletions(-)`.
- The dirt predates this session: this session executed only read-only commands before the stop decision; untracked prior-session artifacts exist (`docs/SESSION-LOG-2026-09-26.md`, `docs/UX-AUDIT-2026-09-26.md`, `.pw-browsers/`, `screenshots/`, `src/python/pw_verify*.js`, a pre-existing `docs/reviews/canva-fidelity-review.md` that is the "prior report").
- A pre-existing untracked scratch file sits in the repo root: `_i18n_all_result.json` (not created by this session; left in place — removing it is out of scope).
- `src/python/` is an almost-entirely untracked mirror tree (the served tree); the tracked exceptions under it are `src/python/build/build_route_bundles.py`, `src/python/build/bundle-admin-v15.js`, `src/python/build/editor-suite.css`, `src/python/build/page-assets-v15.json`, `src/python/build/route-bundles-v15.json`, `src/python/build/sync_frontend_assets.py`, `src/python/server.py`, `src/python/build/bundle-index-v15.js` (all visible in the initial `git status`).
- The uncommitted `index.html` rewrite contains i18n Khmer strings that look machine-generated/wrong (e.g. Undo → `ថម្ងម់កម្រ`, Publish → `ច្រើម` on lines 88–91 of the working tree). **UNKNOWN** whether correct; out of scope; logged only. (This report quotes them verbatim from command output; it fabricates no Khmer.)

**Final state:** after all work, `git status --porcelain` is **byte-identical** to the initial snapshot (**FACT** — `Compare-Object` of the two snapshots, both saved in `%TEMP%\dsh-3T93Ot\`). This holds because (a) my only tracked-file change is 1 line inside the already-`M` `src/html/index.html`, and (b) the report file lands in the already-untracked `docs/reviews/` directory. The footprint of this session in file terms is: `src/html/index.html` +1 line; `docs/reviews/g1-restorefile.md` (new, in pre-existing untracked dir); `src/python/index.html` + 22 stale js/css mirror files updated **by the project's sync tool** (all inside the pre-existing untracked mirror tree — no porcelain entries; see §6). A stray `package.json` accidentally created at the repo root by a failed `npm init` (see §9, item U4) was **removed** before the final status check.

---

## 3. Bug restatement (§1 of dispatch)

- **What is selected:** `$('#restoreFile')`. `$` is defined at `src/js/app.js:1` verbatim: `const $=s=>document.querySelector(s),` — a bare `querySelector` wrapper with **no** null-safety. (Selector written at `src/js/app.js:3273`, verbatim: `$('#restoreFile').onchange=async e=>{`; the paired wiring at `app.js:3272`: `$('#restoreBtn').onclick=()=>$('#restoreFile').click();`.)
- **Which HTML document(s) are expected to contain it:** the editor page. The bundle `bundle-index-v15.js` is loaded by exactly one tracked page, `src/html/index.html` (**FACT** — `grep bundle-index-v15 src/html` matches only `index.html` lines 10, 29, 402; line 402 verbatim: `<script src="bundle-index-v15.js"></script>`). The HTTP server serves the mirror `src/python/index.html` (build docstring: server `ROOT` is `src/python/`). At session start **neither** the tracked source nor the served mirror contained `id="restoreFile"` in its working-tree form (**FACT** — repo-wide grep and `git grep` outputs in §5).
- **What actually happens at runtime when it is absent:** `document.querySelector('#restoreFile')` → `null`; `null.onchange = <fn>` throws `TypeError: Cannot set properties of null (setting 'onchange')` **immediately at script load** (the call is evaluated eagerly; the `try{…}` on the next line only wraps the arrow-function body). Because the bundle is one classic `<script>`, the throw aborts every statement after it in the bundle.
- **Guarded or unguarded: UNGUARDED.** Surrounding code, verbatim, 5 lines before / after `src/js/app.js:3272-3273` (read via `Get-Content`):

```
3267: }));
3268: a.download=`invitation-backup-${new Date().toISOString().slice(0,10)}.json`;
3269: a.click();
3270: URL.revokeObjectURL(a.href)
3271: };
3272: $('#restoreBtn').onclick=()=>$('#restoreFile').click();
3273: $('#restoreFile').onchange=async e=>{
3274: try{
3275: let data=JSON.parse(await e.target.files[0].text());
3276: if(!['e-invitation-website-backup','sovan-invite-backup'].includes(data.format)||!data.draft)throw Error();
3277: inviteStore.write(draftKey,data.draft);
3278: if(data.published)inviteStore.write(publishKey,data.published);
3279: inviteStore.write(historyKey,data.history||[]);
3280: inviteStore.write(rsvpKey,data.rsvps||[]);
3281: location.reload()
3282: }catch{
3283: alert('This is not a valid E-invitation-website backup.')
3284: }
3285: };
```

No `.length` check, no null guard, no `?.`, no enclosing `try` (the `try` at 3274 is *inside* the handler body, not around the binding). Scope: the block is **top-level** — `app.js` opens with a top-level `const` (line 1), the sibling backup handler starts top-level at `app.js:3254` (`$('#backupBtn').onclick=()=>{`), and top-level statements continue after the block (`app.js:3379` `window.addEventListener('resize',…)`; `app.js:3385` DOMContentLoaded wiring; `app.js:3386` IIFE) (**FACT** — quoted lines).
- **Severity: CRITICAL, confirmed.** The thrown error is top-level in a single `<script>` element; everything bundled after line 5386 never executes. Corroborating raw evidence from the before-fix browser run (§8): `#khmerDay` options `0` (the initializer at `app.js:3287` `$('#khmerDay').innerHTML=Array.from({` runs *after* 3273) and `window.typographyLayoutController === "undefined"` (set at `app.js:3385`). **INFERENCE** (from those two FACTS + the manifest's script order, FACT) that 37 concatenated source modules after `app.js` (per `docs/route-bundles-v15.json`, `app.js` is script #20 of 57) plus the remainder of `app.js` (lines 3274–3386) were dead on every page load. The prior report's "Critical / editor does not function at all" label is therefore **justified, not downgraded** — with the refinement that after G1 is fixed, the page still crashes on a separate bug (§8), so the page-level symptom persists by a different cause.

---

## 4. Source trace (§2 of dispatch)

| Hop | Location | Verbatim content |
|---|---|---|
| Bundle line 5386 | `src/js/bundle-index-v15.js:5386` | `$('#restoreFile').onchange=async e=>{` |
| Bundle line 5385 | `src/js/bundle-index-v15.js:5385` | `$('#restoreBtn').onclick=()=>$('#restoreFile').click();` |
| Source file:line | `src/js/app.js:3273` | `$('#restoreFile').onchange=async e=>{` |
| Source file:line | `src/js/app.js:3272` | `$('#restoreBtn').onclick=()=>$('#restoreFile').click();` |

- **Byte-identity of the segment:** `Compare-Object` of `app.js` lines 3272–3285 vs bundle lines 5385–5398 → `identical: True` (**FACT**, command output §"verify"). Line offset: 5386 − 3273 = **2113** (**FACT** — arithmetic on the two quoted line numbers).
- **Source→bundle relationship, confirmed by command, not by eyeballing:**
  - `docs/route-bundles-v15.json` (the output manifest) defines `index.html` → `bundle-index-v15.js` with `"scriptBytes": 1115253` and `"scriptSha256": "e4b122cc375570b1a495e865f27b6d0f4d3f81ec1e99576209b70c518a3bc08b"`, and its `sources.scripts` array lists 57 files with `"app.js"` at position 20 (**FACT** — quoted manifest lines 294–357).
  - The builder is `src/python/build/build_route_bundles.py`. Its docstring (lines 8–16) states it reads sources from `src/js`/`src/css`/`vendor` and writes bundles to **both** `src/python/` and `src/js/`; `js_bundle()` (lines 92–102, verbatim core: `chunks.append(f";{read_js(path).rstrip()}")` then `"".join(chunks)`) defines the exact concatenation (**FACT** — quoted).
  - `python src/python/build/build_route_bundles.py --check` → **`ROUTE_BUNDLE_CHECK_PASSED`** (**FACT**, run twice: once before any change, once after the sync in §6). This proves the deployed `bundle-index-v15.js` is byte-exactly the manifest concatenation of the current sources — i.e., the bundle line maps to `app.js` as quoted above.
- **Mirror byte-identity** (`src/js/` vs `src/python/` twin), `Get-FileHash` SHA-256 (**FACT**):
  - `src/js/bundle-index-v15.js` → `E4B122CC375570B1A495E865F27B6D0F4D3F81EC1E99576209B70C518A3BC08B`
  - `src/python/bundle-index-v15.js` → `E4B122CC375570B1A495E865F27B6D0F4D3F81EC1E99576209B70C518A3BC08B` → **byte-identical**, and equal to the manifest's `scriptSha256` (case-insensitive) (**FACT**).
  - `src/python/build/bundle-index-v15.js` → `915624C9897F1C04C274CAA712153C2149FCCF1EF6A64B6ECFFB52D83DC17761` → **stale** (its `restoreFile` lines sit at 5127/5128, offset −258 vs the deployed copy; the current builder never writes into `src/python/build/`). **INFERENCE** (from FACTs: hash difference + builder's write targets + the file's tracked-but-clean status) that it is a leftover build artifact from an older source state. Hygiene note only; not touched.
- **Also mirrored (untracked):** `src/python/app.js:3272-3273` carries the identical source lines (**FACT** — repo-wide grep).

---

## 5. Origin trace (§3 of dispatch)

Repo size: `git rev-list --all | Measure-Object -Line` → **79** revisions (**FACT**) — small enough for the belt-and-braces sweep.

### 5.1 Mandated commands, raw output

```
$ git log --all --oneline -S"restoreFile" -- .
bdcfd49 Update latest platform changes
cfbb764 Initial import: online invitation platform (baseline)
6d595d8 Upload current project snapshot
```
```
$ git log --all --oneline -G"restoreFile" -- .
bdcfd49 Update latest platform changes
cfbb764 Initial import: online invitation platform (baseline)
6d595d8 Upload current project snapshot
```
```
$ git log --all --oneline -- src/html/index.html
75acbe6 Merge remote v54 security review history
320d414 v54: complete security hardening and platform updates
bdcfd49 Update latest platform changes
fd6a097 Update platform to latest local version
5ed591e v54: refactor editor chrome, fix UX bugs, harden security
cfbb764 Initial import: online invitation platform (baseline)
78258bf Update project structure and documentation
```

### 5.2 Substring audit (mandatory, per `-S`/`-G` hit)

For each of the 3 commits, every diff line containing `restoreFile` was extracted from `git show <sha>` and classified with a word-boundary regex `(?<![A-Za-z0-9_])restoreFile(?![A-Za-z0-9_])` (**FACT** — command output):

| commit | matching diff lines | exact-token | substring-only |
|---|---|---|---|
| `bdcfd49` | 3 | 3 | 0 |
| `cfbb764` | 5 | 5 | 0 |
| `6d595d8` | 5 | 5 | 0 |

Representative exact-token lines (verbatim from `git show` output): `<input id="restoreFile" type="file" accept="application/json" hidden>` (inside the flat `<header>`), `+$('#restoreBtn').onclick=()=>$('#restoreFile').click();`, `+$('#restoreFile').onchange=async e=>{`. **No hit is a longer word merely containing the token (no "cursive"-class false positives). Audit: PASS.**

Per-path attribution (`git log --all --oneline -S"restoreFile" -- <path>`), raw results: `src/html/index.html`, `src/js/app.js`, `src/js/bundle-index-v15.js` each show token-count changes at exactly `cfbb764` and `78258bf`; the queries against `src/python/index.html`, `src/python/app.js`, `src/python/bundle-index-v15.js` and `docs/` returned **empty** (those mirror files were never tracked) (**FACT** — outputs above). A separate per-path run `-- src/python/build/` returned `bdcfd49` — i.e. `bdcfd49`'s whole-repo `-S` hit is the tracked build leftover `src/python/build/bundle-index-v15.js` (**FACT**). The sweep below additionally shows `6d595d8` (oldest revision, 2026-08-28) carried the token in the **old root-level layout** (`index.html`, `app.js`, `bundle-index-v15.js` at repo root, plus the `src/python/` copies of that era) (**FACT** — `git rev-list` sweep pairs `6d595d8…:index.html`, `:app.js`, `:bundle-index-v15.js`).

### 5.3 Belt-and-braces sweep

`git rev-list --all | ForEach-Object { git grep -n "restoreFile" $_ 2>$null }` → **382 hit lines** across the 79 revisions (**FACT**; full output saved to `%TEMP%\dsh-3T93Ot\g1-revlist-sweep.txt`). Distinct files ever containing the token in a tracked revision: `app.js`, `bundle-index-v15.js`, `index.html` (old root-level layout), `src/html/index.html`, `src/js/app.js`, `src/js/bundle-index-v15.js`, `src/python/app.js`, `src/python/bundle-index-v15.js`, `src/python/build/bundle-index-v15.js`, `src/python/index.html` (old-layout mirror copies).

### 5.4 Working-tree `git grep` (whole repo, not just index.html)

```
$ git grep -n "restoreFile" -- .
src/js/app.js:3272:$('#restoreBtn').onclick=()=>$('#restoreFile').click();
src/js/app.js:3273:$('#restoreFile').onchange=async e=>{
src/js/bundle-index-v15.js:5385:$('#restoreBtn').onclick=()=>$('#restoreFile').click();
src/js/bundle-index-v15.js:5386:$('#restoreFile').onchange=async e=>{
src/python/build/bundle-index-v15.js:5127:$('#restoreBtn').onclick=()=>$('#restoreFile').click();
src/python/build/bundle-index-v15.js:5128:$('#restoreFile').onchange=async e=>{
```
(**FACT**.) Note `git grep` only sees tracked content: the untracked prior report `docs/reviews/canva-fidelity-review.md` and the untracked mirror/test files (`src/python/app.js`, `src/python/bundle-index-v15.js`, `src/python/index-test-en.html:78`, `src/python/index-test-km.html:78` — which **do** contain `<input id="restoreFile" type="file" accept="application/json" hidden>`) are additionally listed by the repo-wide filesystem grep (**FACT** — grep tool output §5.5).

### 5.5 Re-deriving the prior report's "index.html lacks the element" claim (independently, not taken on trust)

- Tracked source, working tree: `src/html/index.html` contains **no** `restoreFile` (repo-wide grep + `git grep` above) — but **does** contain `<button id="restoreBtn">Restore</button>` at working-tree line 98 (**FACT**). The prior report's "line 98" location is consistent with the *current* dirty file.
- Served mirror, working tree: `src/python/index.html` also contains no `restoreFile` (repo-wide grep) — so the bug is live on the served page, not just in the source.
- **The prior report's "missing from HTML" is true for the *working tree* but its framing is incomplete:** `git grep -n 'restoreFile' HEAD -- src/html/index.html` →

```
HEAD:src/html/index.html:78:  <header>…<button id="restoreBtn">Restore</button><input id="restoreFile" type="file" accept="application/json" hidden><button id="undoBtn" … </header>
```
(**FACT** — the full line is quoted in §5.6 below.) The element **is** in the committed tree; the working tree dropped it.
- Exhaustive presence check across all revisions containing the file (`git cat-file -e ${r}:src/html/index.html` + `git grep -q` per revision, exit-code checked):

```
revisions: 79
revisions containing src/html/index.html: 50
of those, containing restoreFile token: 50
revisions with file but WITHOUT token: 0
```
(**FACT**, command output.) Direct spot-checks at `78258bf` (line 40), `cfbb764` (line 40), `5ed591e` (line 62), `fd6a097` (line 78), `bdcfd49` (line 78), `320d414` (line 78), `75acbe6` (line 78), `HEAD` (line 78) all hit the same `<input id="restoreFile" …>` line (**FACT** — `git grep` per revision).

### 5.6 Decision rule applied

- "`id="restoreFile" appears in any tracked revision, ever`" → **YES, in all 50 applicable revisions including HEAD** → branch **§4A (element was removed)**.
- "Identify the commit, quote the diff" → **there is no such commit.** The removal lives only in the uncommitted working tree. The definitive diff (`git diff -- src/html/index.html`, hunk at `@@ -75,7 +75,32 @@`, full file saved to `%TEMP%\dsh-3T93Ot\g1-index-diff.txt`) shows the deleted line and its replacement (**FACT** — verbatim, truncated to the header region; Khmer strings quoted exactly as they appear in the working tree):

```
-  <header><strong>E-invitation-website</strong><a href="dashboard.html" class="button-link">Dashboard</a><span id="saveState">Saved locally</span><span id="serverState">Local mode</span><button id="backupBtn">Backup</button><button id="restoreBtn">Restore</button><input id="restoreFile" type="file" accept="application/json" hidden><button id="undoBtn" title="Undo (Ctrl+Z)">Undo</button><button id="redoBtn" title="Redo (Ctrl+Y)">Redo</button><button id="previewBtn">Guest preview</button><button id="publishBtn" class="primary">Publish snapshot</button></header>
+  <header class="studio-topbar">
+    <div class="studio-topbar-left">
+      <button id="v54SidebarCollapse" class="v54-sidebar-collapse" type="button" title="Toggle sidebar" aria-label="Toggle sidebar">≡</button>
+      <a href="dashboard.html" class="button-link"><strong>E-invitation-website</strong></a>
+      <span class="studio-document-title" id="documentTitle">Untitled design</span>
+    </div>
+    <div class="canvas-header-more"><summary>…</summary></div>
+    <div class="studio-topbar-right">
+      <span id="saveState">…</span>
+      <span id="serverState">…</span>
+      <button id="undoBtn" …>…</button>
+      …(redo/preview/publish/AI/⌘K)
+    </div>
+    <div class="canvas-header-more-menu">
+      <div class="v54-header-menu-section v54-header-menu-project"><strong>Project</strong>
+        <button id="backupBtn">Backup</button>
+        <button id="restoreBtn">Restore</button>
+      </div>
+      …(Editor / Advanced tools sections)
```

(For exactness, the pre-fix working-tree lines 95–99 were: `95: <div class="canvas-header-more-menu">`, `96: <div class="v54-header-menu-section v54-header-menu-project"><strong>Project</strong>`, `97: <button id="backupBtn">Backup</button>`, `98: <button id="restoreBtn">Restore</button>`, `99: </div>` — **FACT** via `Get-Content`.)

### 5.7 Deliberate or collateral?

- The rewrite **kept** both the `Restore` button (`index.html:98`) and the entire backup/restore JS (`app.js:3254-3285` unchanged vs HEAD: `git diff HEAD -- src/js/app.js` contains **0** lines mentioning `restoreFile` — **FACT**).
- No commit message, PR, or comment explains a removal of the file input (there is no commit at all — **FACT**).
- Every historical revision pairs the input immediately after the restore button; the new template simply omitted it.
- **Classification: collateral damage of the template rewrite** (**INFERENCE** from the FACTs above). Hence §4A's collateral branch: *restore the element in the source HTML, matching surrounding conventions* — not remove the JS (the feature is live: button present, handler present, CSS present — `src/css/bundle-*-v15.css` style `body[data-page="index"]>header #restoreBtn` rules, **FACT** via grep).

---

## 6. Change (§4 of dispatch)

### 6.1 Decision: §4A (collateral removal → restore markup in source HTML)

Argument (from §5.7): the feature was retained in button and JS; only the hidden input was dropped; the committed history always contained it; therefore the correct minimal fix is restoring the element in the source HTML, not deleting the (working) JS.

### 6.2 Exact diff (the only source change; `src/` only, no `src/python/` hand-edits, no bundle hand-edits, no `!important`)

File: `src/html/index.html` (working tree; +1 line, now new line 99):

```diff
       <div class="v54-header-menu-section v54-header-menu-project"><strong>Project</strong>
         <button id="backupBtn">Backup</button>
         <button id="restoreBtn">Restore</button>
+        <input id="restoreFile" type="file" accept="application/json" hidden>
       </div>
```

The restored line is **byte-exact** against every committed ancestor's attribute string (`type="file" accept="application/json" hidden`) (**FACT** — compared against the quoted `-` line of §5.6 and the `HEAD` grep line of §5.5). Placement: directly after `#restoreBtn` inside the v54 "Project" menu section — preserving the historical adjacency (input immediately after the restore button in all 50 revisions, **FACT** §5.5/§5.6) and the file's 8-space indentation convention for that block. Resulting diff stat: `src/html/index.html | 60 +… 1 file changed, 48 insertions(+), 12 deletions(-)` (**FACT** — `git diff --stat`; the +1 over the pre-existing +47/−12 is this line).

### 6.3 Propagation to the served tree (project tooling, not hand edits)

The server serves `src/python/`; the project's HTML propagation tool is `src/python/build/sync_frontend_assets.py` (docstring: idempotent mtime-based copy of `src/html/*.html` → `src/python/`, **FACT** — quoted docstring lines 2–19). Commands and raw outputs:

```
$ python src/python/build/sync_frontend_assets.py
html: copied=0 skipped=1 -> F:\eInvite\einvite-platform\src\python
vendor: copied=0 skipped=8 -> F:\eInvite\einvite-platform\src\python\vendor
assets: copied=0 skipped=12 -> F:\eInvite\einvite-platform\src\python\assets
licenses: copied=0 skipped=2 -> F:\eInvite\einvite-platform\src\python\licenses
js: copied=10 skipped=175 -> F:\eInvite\einvite-platform\src\python
core: copied=0 skipped=3 -> F:\eInvite\einvite-platform\src\python\core
css: copied=12 skipped=93 -> F:\eInvite\einvite-platform\src\python
organized: copied=0 skipped=21 -> F:\eInvite\einvite-platform\src\python
SYNC_FRONTEND_ASSETS_DONE copied=22 skipped=315
```
(**FACT** — the run was executed once with one-time wider access because the sandbox denies shell processes writes to `src/python/`; see §9 U6.)

- **Verification that the HTML copy actually happened** (the printed `html:` line is misleading — see U7): after the run, `src/python/index.html` line 99 contains `<input id="restoreFile" type="file" accept="application/json" hidden>` and `src/html/index.html` and `src/python/index.html` are **byte-identical**, SHA-256 `79915959AB0689482B6A63B77CCA5EC2AF11B381DEF075E6A3639D8C7CB0320A`, equal mtimes (`copy2` preserves) (**FACT** — `Select-String` + `Get-FileHash` output).
- The sync also mechanically refreshed 22 stale js/css mirrors (`js: copied=10`, `css: copied=12`) to match the pre-existing dirty sources — generated-mirror updates by the project tool, no content authored by this session (**FACT** — sync output; **INFERENCE** that they equal the working-tree sources by the tool's plain `copy2` semantics).
- **Bundle:** no JS source was modified, so no bundle regeneration was needed. `python src/python/build/build_route_bundles.py --check` → `ROUTE_BUNDLE_CHECK_PASSED` both before the change and after the sync (**FACT**). The bundle still contains the (now-correctly-resolving) selector at line 5385/5386 — intentionally; the JS is the feature, not the bug.

### 6.4 No-rejection-rule compliance

Edited only `src/html/index.html` (plus the generated mirror via the project tool). No `src/python/` file hand-edited. No `bundle-*.js` touched by hand. No `!important` added or used. No `commit`/`stash`/`checkout`/`reset`/`clean` executed.

---

## 7. Collateral scan (§5 of dispatch)

Mandated command (pattern quoted via char-code construction to survive PowerShell): `git grep -n "<\$('#` … equivalent regex `\$` `(` `'` `#` → **2327 matching lines** under `src/js/` (**FACT**; full output in `%TEMP%\dsh-3T93Ot\g1-collateral-grepgit.txt`).

Bundle-focused analysis (helper script `%TEMP%\dsh-3T93Ot\g1-collateral-scan.py`, read-only): distinct `$('#id')` selectors used in `bundle-index-v15.js`: **355**; distinct `id`s present in the (post-fix) working-tree `index.html`: **220**; selectors referencing ids **absent** from that page: **151**; of those, present in **no** `src/html/*.html` page: **142** (**FACT** — script output). Top 20 by bundle occurrence count:

| # | selector | source `file:line` (first 3) | present in which HTML | verdict |
|---|---|---|---|---|
| 1 | `#workflowPageDock` | `src/js/editor/ui-layout.js:209`; `src/js/workflow-creation-flow-v3.js:19`; `src/js/workflow-creation-flow-v4.js:147` | none | no host page in `src/html` — suspicious (dynamic creation not ruled out) |
| 2 | `#aiBgCut` | `src/js/canvas-plus.js:316`; `src/js/canvas-plus.js:359`; `src/js/editor-suite.js:319` | none | no host page found |
| 3 | `#canvasTextPadding` | `src/js/canvas-plus.js:243`; `src/js/canvas-plus.js:245`; `src/js/editor-suite.js:246` | none | no host page found |
| 4 | `#newBtn` | `src/js/dashboard-polish.js:41`; `src/js/dashboard.js:108`; `src/js/ux-refine.js:18` | `dashboard.html` | cross-page module reference (index bundle embeds dashboard modules) |
| 5 | `#studioCheckBtn` | `src/js/ai-assistant-pro.js:86`; `src/js/canvas-plus.js:144`; `src/js/editor-suite.js:147` | none | no host page found |
| 6 | `#workflowV5Focus` | `src/js/workflow-ux-v5.js:32`; `src/js/workflow-ux-v5.js:35` | none | no host page found |
| 7 | `#workflowV6PositionBtn` | `src/js/workflow-pro-editor-v6.js:103`; `src/js/workflow-pro-editor-v6.js:193`; `src/js/workflow-pro-editor-v6.js:197` | none | no host page found |
| 8 | `#aiBgFeather` | `src/js/canvas-plus.js:329`; `src/js/canvas-plus.js:367`; `src/js/editor-suite.js:332` | none | no host page found |
| 9 | `#aiBgThreshold` | `src/js/canvas-plus.js:328`; `src/js/canvas-plus.js:366`; `src/js/editor-suite.js:331` | none | no host page found |
| 10 | `#aiHue` | `src/js/canvas-plus.js:358`; `src/js/canvas-plus.js:365`; `src/js/editor-suite.js:361` | none | no host page found |
| 11 | `#aiHueValue` | `src/js/canvas-plus.js:358`; `src/js/canvas-plus.js:365`; `src/js/editor-suite.js:361` | none | no host page found |
| 12 | `#aiReplaceImage` | `src/js/canvas-plus.js:369`; `src/js/editor-suite.js:372`; `src/js/editor-suite.js:591` | none | no host page found |
| 13 | `#canvasBgAngleValue` | `src/js/canvas-plus.js:228`; `src/js/canvas-plus.js:229`; `src/js/editor-suite.js:231` | none | no host page found |
| 14 | `#canvasBgTextureValue` | `src/js/canvas-plus.js:228`; `src/js/canvas-plus.js:229`; `src/js/editor-suite.js:231` | none | no host page found |
| 15 | `#canvasSmartTone` | `src/js/canvas-plus.js:210`; `src/js/canvas-plus.js:212`; `src/js/editor-suite.js:213` | none | no host page found |
| 16 | `#canvasTextPaddingValue` | `src/js/canvas-plus.js:243`; `src/js/canvas-plus.js:245`; `src/js/editor-suite.js:246` | none | no host page found |
| 17 | `#canvasTextVertical` | `src/js/canvas-plus.js:243`; `src/js/canvas-plus.js:244`; `src/js/editor-suite.js:246` | none | no host page found |
| 18 | `#confirmPasswordRegister` | `src/js/canvas-plus.js:55`; `src/js/canvas-plus.js:91`; `src/js/editor-suite.js:58` | none | no host page found |
| 19 | `#dashboardView` | `src/js/dashboard-polish.js:5`; `src/js/dashboard.js:90`; `src/js/final-polish.js:7` | `dashboard.html` | cross-page module reference |
| 20 | `#eiCollabEmail` | `src/js/collaboration.js:10` | none | no host page found |

(**FACT** — table data from the script's raw output, §8 of the run log.)

Reading: many of these are (a) **cross-page** references — the index bundle concatenates modules written for other pages (e.g. `dashboard.js`), or (b) ids **created dynamically at runtime** by the same JS (the editor builds much of its chrome programmatically; e.g. `#noSelection`, `#properties` are static but dozens of inspector/workflow ids are not in any HTML). **This is intelligence, not a fix list** — per dispatch, none of it was touched. Notably, `#restoreFile` appeared in this "no host page" list (2×) *before* the fix and is resolved *after* it (**FACT** — scan outputs). Related out-of-scope finding: the same v54 header rewrite that dropped `#restoreFile` also broke `src/js/studio-experience.js:29` (`if (saveState) header.insertBefore(titleWrap, saveState);` — `#saveState` is now a grandchild, not a direct child, of `<header>` → `NotFoundError` at bundle line 5527; see §8 after-run).

---

## 8. Verification (§6 of dispatch)

### 8.1 Environment and deviations (labeled)

- **Browser: Puppeteer 25.12.0 (`npx`/npm install in `%TEMP%` workspace) driving headless Chromium via the installed `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`** instead of a standalone Chrome binary: no Chrome is installed on this machine (**FACT** — existence checks against the standard 3 Chrome paths all `missing`), and the Chrome-for-Testing download was network-blocked (`npx puppeteer browsers install chrome` → `All providers failed for chrome 154.0.8037.57: Extraction failed: spawn EPERM`; direct `Invoke-WebRequest` of `storage.googleapis.com/chrome-for-testing-public/…/chrome-win64.zip` → "The underlying connection was closed"). Edge is Chromium (same engine family the dispatch mandates over Firefox; the dispatch's "unreliable" warning targets Firefox specifically). **INFERENCE**: a Chromium-engine repro satisfies the dispatch's intent (real headless browser, raw console capture) where a Chrome binary was unobtainable.
- **Server:** dispatch default port 8000 was already occupied by an unknown listener (**FACT** — `Test-NetConnection 127.0.0.1:8000` → `TcpTestSucceeded: True`; owner process not identifiable from this sandbox). Used `python -m http.server 8001 --directory F:\eInvite\einvite-platform\src\python` as a managed background job; probe: `HTTP 200, bytes=41110` (**FACT**).
- **Sandbox:** the confined sandbox blocks node from spawning the browser (`spawn EPERM` — the documented piped-stdio boundary; `@puppeteer/browsers`'s `#configureStdio` returns piped stdio in both `pipe` modes, so `pipe:false` cannot restructure it). Two one-time wider-access approvals were used: the exact repro command before the fix and the identical command after the fix.

### 8.2 Repro command (identical for both runs)

Script: `%TEMP%\dsh-3T93Ot\g1pw\g1-repro.js` (Puppeteer: launch headless Chromium, `goto http://127.0.0.1:8001/index.html` waitUntil `load`, 2.5 s settle, capture **all** `console` + `pageerror` raw, evaluate DOM probes `#restoreFile`/`#restoreBtn` presence, `#khmerDay` option count, `typeof window.typographyLayoutController`, `header.className`; screenshot; print everything). Invocation (both runs):

```
node g1-repro.js   (cwd %TEMP%\dsh-3T93Ot\g1pw, G1_BROWSER=edge, G1_PW_DIR/G1_OUT=%TEMP%\dsh-3T93Ot\g1pw)
```

### 8.3 BEFORE (pre-fix), raw output

```
=== G1 REPRO (restoreFile present: false) ===
timestamp_start=2026-10-05T08:32:29.780Z
timestamp_end=2026-10-05T08:32:32.780Z
pageErrors_count=1
PAGEERROR[0]:
Cannot set properties of null (setting 'onchange')
TypeError: Cannot set properties of null (setting 'onchange')
    at <anonymous> (http://127.0.0.1:8001/bundle-index-v15.js:5386:27)
console_count=2
CONSOLE[0]: verbose: [DOM] Password field is not contained in a form: (More info: https://www.chromium.org/developers/design-documents/create-amazing-password-forms) %o
CONSOLE[1]: error: Failed to load resource: the server responded with a status of 404 (File not found)
probes={"restoreFilePresent":false,"restoreBtnPresent":true,"khmerDayOptions":0,"typographyLayoutController":"undefined","headerClass":"studio-topbar"}
screenshot=C:\Users\NgethSereyboth\AppData\Local\Temp\dsh-3T93Ot\g1pw\g1-shot-2026-10-05T08-32-32-784Z.png
```
(**FACT** — saved to `%TEMP%\dsh-3T93Ot\g1pw\g1-repro-before.txt`.) This is the dispatch's reported bug verbatim: `#restoreFile` → null → unguarded `onchange` assignment → top-level `TypeError` at **5386:27**, killing the rest of the bundle (`khmerDayOptions:0`, controller `undefined` prove the post-throw code never ran). `CONSOLE[0]`/`CONSOLE[1]` are environmental (static server, no backend; resource not identified — UNKNOWN, §9 U5).

### 8.4 AFTER (post-fix), raw output — **the same command**

```
=== G1 REPRO (restoreFile present: true) ===
timestamp_start=2026-10-05T08:36:53.050Z
timestamp_end=2026-10-05T08:36:56.275Z
pageErrors_count=1
PAGEERROR[0]:
NotFoundError: Failed to execute 'insertBefore' on 'Node': The node before which the new node is to be inserted is not a child of this node.
DOMException: NotFoundError: Failed to execute 'insertBefore' on 'Node': The node before which the new node is to be inserted is not a child of this node.
    at <anonymous> (http://127.0.0.1:8001/bundle-index-v15.js:5527:27)
    at <anonymous> (http://127.0.0.1:8001/bundle-index-v15.js:6033:3)
console_count=2
CONSOLE[0]: verbose: [DOM] Password field is not contained in a form: (More info: https://www.chromium.org/developers/design-documents/create-amazing-password-forms) %o
CONSOLE[1]: error: Failed to load resource: the server responded with a status of 404 (File not found)
probes={"restoreFilePresent":true,"restoreBtnPresent":true,"khmerDayOptions":15,"typographyLayoutController":"function","headerClass":"studio-topbar"}
screenshot=C:\Users\NgethSereyboth\AppData\Local\Temp\dsh-3T93Ot\g1pw\g1-shot-2026-10-05T08-36-56-279Z.png
```
(**FACT** — saved to `%TEMP%\dsh-3T93Ot\g1pw\g1-repro-after.txt`.)

Interpretation, precisely:

- **The G1 error is gone.** The exact `TypeError … (setting 'onchange') … 5386` no longer occurs. `restoreFilePresent: true`. The code between the old crash point and the new failure point now executes: `khmerDayOptions` 0 → **15** (the `app.js:3287` initializer ran) and `typographyLayoutController` `undefined` → **function** (the `app.js:3385` DOMContentLoaded wiring ran) (**FACT** — probe diff).
- **The run is not fully clean, and this must not be papered over:** one pageerror remains — `NotFoundError … insertBefore` at **bundle line 5527**, source `src/js/studio-experience.js:29` verbatim: `if (saveState) header.insertBefore(titleWrap, saveState);` (**FACT** — grep + bundle read: `5526: const saveState = $('#saveState');` / `5527: if (saveState) header.insertBefore(titleWrap, saveState);`). This is a *different* defect (the v54 header now nests `#saveState` inside `.studio-topbar-right`, so it is not a direct child of `<header>`; the `if` guards null but not parent-child mismatch). It is **pre-existing** (independent of the one-line HTML fix, which does not touch `#saveState` or header nesting) and matches the prior report's documented "Pass 1" state ("The `insertBefore` error at line 5527 still fires"). **Logged, not fixed, per scope.** **INFERENCE**: the editor page is still non-functional on load because of this separate bug — G1 alone does not make the page work; the prior report's patch sequence (Patch A + insertBefore patch) is the known consequence.
- Against the dispatch's acceptance line "the same command … must now be clean": read strictly as "no pageerror at all", it is **not** satisfied — but only because of a *different* out-of-scope bug, and the G1 demonstration (the 5386 TypeError) **is** clean under the identical command. Confidence in the G1 fix: **VERIFIED by raw before/after output** (FACT-based, no INFERENCE needed for the G1 claim itself).

### 8.5 Screenshot evidence

- Before: `%TEMP%\dsh-3T93Ot\g1pw\g1-shot-2026-10-05T08-32-32-784Z.png` (timestamp in filename)
- After: `%TEMP%\dsh-3T93Ot\g1pw\g1-shot-2026-10-05T08-36-56-279Z.png`

---

## 9. Uncertainty register

| # | Item | Label |
|---|---|---|
| U1 | Identity of the process already listening on port 8000 (owner invisible from this sandbox; `Get-NetTCPConnection` also blocked) | **UNKNOWN** — worked around with port 8001 |
| U2 | Which resource produced the `404` console line in both repro runs (not captured; static server without backend makes some fetches fail; e.g. `manifest.webmanifest`/fonts/`/api/*`) | **UNKNOWN** — environmental, not G1 |
| U3 | Correctness of the uncommitted i18n Khmer strings in the v54 header rewrite (`ថម្ងម់កម្រ`, `ច្រើម`, …) — some look machine-generated | **UNKNOWN** — out of scope; not touched, not "fixed" |
| U4 | The stray root `package.json` created mid-session by a failed `npm init` (job cwd fell back to repo root after a denied `Set-Location`): confirmed plain `npm init -y` skeleton (description auto-filled from the repo README), **removed** before final status; its creation was a session mistake, fully disclosed here | **FACT** (created+removed), **INFERENCE** (cause: PowerShell `Set-Location` failure in job `pwsh-45`) |
| U5 | Whether any of the 142 "orphan" ids (§7) are created dynamically at runtime by the bundle (they would then be benign) | **UNKNOWN** — static scan only; flagged as intelligence |
| U6 | Sandbox write denial on `src/python/` for shell processes (projected around by one wider-access run of the *project's own* sync tool; the DSH file backend itself wrote `src/html/index.html` fine) — mechanism not fully characterized | **UNKNOWN** (mechanism), **FACT** (behavior) |
| U7 | `sync_frontend_assets.py` summary bug: `summary[src_dir.name]` collides for the two `src/html` plan entries (`*.html` and `*.webmanifest`), so the printed `html: copied=0 skipped=1` line is the webmanifest entry's result, not the 17-file HTML glob's. The HTML copy itself **did** happen (verified by hash, §6.3) | **FACT** (bug), **FACT** (copy verified) |
| U8 | `src/python/build/bundle-index-v15.js` (tracked, stale, restoreFile at 5127/5128) is a leftover artifact not produced by the current builder | **INFERENCE** (from hash + builder write targets) |
| U9 | Origin/authorship of the uncommitted WIP (prior session; `docs/SESSION-LOG-2026-09-26.md` and `.pw-browsers/` timestamps suggest 2026-09-26/10-04 WSL-based agent work) | **UNKNOWN** |
| U10 | `sync_frontend_assets.py` staleness is mtime-based, not content-based; a content drift with an equal/older mtime would not be re-synced | **INFERENCE** (from quoted `_needs_copy` source) |
| U11 | Whether a real user's browser could be served a stale cached `index.html`/bundle by the service worker (`service-worker.js` is bundled; SW behavior under the static test server was not observed) | **UNKNOWN** — repro used a fresh profile; not in scope |

---

## 10. Not checked (explicit)

1. The separate `insertBefore` bug (bundle 5527 / `studio-experience.js:29`) beyond identifying its source line and mapping it to the prior report's "Pass 1" state.
2. End-to-end functional test of backup/restore (choosing a JSON file → parse → `inviteStore.write` ×4 → `location.reload()`); only verified that the bindings no longer throw and the element resolves.
3. The other 15 HTML pages' bundles (they do not load `bundle-index-v15.js`); no cross-page id audit beyond the §7 helper.
4. The uncommitted changes to `src/js/bundle-index-v15.js` (+425/−12) and `src/js/app.js` as such — only verified that the G1-relevant lines are unchanged vs HEAD and that the deployed bundle equals the current source concatenation (`--check` PASSED).
5. `!important` usage counts, i18n translation quality, accessibility, security posture — all out of G1 scope.
6. The test suite (`tests/`), the `deliverables/` directory, and the `screenshots/` directory from prior sessions.
7. WSL setup and the prior session's `pw_verify*.js` runs (their paths show WSL use; not re-created).
8. The `.cache/`, `.pw-browsers/`, `_i18n_all_result.json` root artifacts (pre-existing; logged in §2; untouched).
9. Deep validation of `docs/route-bundle-sources-v15.json` vs `docs/route-bundles-v15.json` consistency beyond what `--check` proves (it recomputes everything from the sources manifest).
10. Any browser profile with pre-existing `localStorage`/IndexedDB state (repro used a clean profile each launch).

---

## Appendix — helper artifacts (all in `%TEMP%`, none in the repo)

| Path | Purpose |
|---|---|
| `%TEMP%\dsh-3T93Ot\g1-initial-status.txt` | initial `git status --porcelain` snapshot (497 lines) |
| `%TEMP%\dsh-3T93Ot\g1-final-status.txt` | final snapshot (byte-identical to initial) |
| `%TEMP%\dsh-3T93Ot\g1-index-diff.txt` | full pre-fix `git diff` of `src/html/index.html` |
| `%TEMP%\dsh-3T93Ot\g1-revlist-sweep.txt` | belt-and-braces sweep, 382 hit lines |
| `%TEMP%\dsh-3T93Ot\g1-collateral-grepgit.txt` | `git grep` collateral raw output, 2327 lines |
| `%TEMP%\dsh-3T93Ot\g1-collateral-scan.py` | collateral analysis script |
| `%TEMP%\dsh-3T93Ot\g1pw\g1-repro.js` | the repro script (both runs) |
| `%TEMP%\dsh-3T93Ot\g1pw\g1-repro-before.txt` / `g1-repro-after.txt` | raw repro outputs |
| `%TEMP%\dsh-3T93Ot\g1pw\g1-shot-2026-10-05T08-32-32-784Z.png` / `g1-shot-2026-10-05T08-36-56-279Z.png` | before/after screenshots |
| `%TEMP%\dsh-3T93Ot\g1pw\` | Puppeteer workspace (`node_modules`, `package.json`, npm cache, browser cache) |

*Every number in this report was produced by a command whose output is pasted here or saved to the listed paths; no count was typed from memory or from the prior report. Prior-report numbers (e.g. its line citations, its "414 vs 1 `!important`" episode) were independently re-derived where relevant (§5.5) and its severity label was re-justified on this session's own evidence (§3), not inherited.*
