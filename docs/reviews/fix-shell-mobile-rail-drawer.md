# The shell below 1025px: a sticky rail starved the page, and four controls that did nothing

Scope: `src/css/app-shell-v55.css` (Skeleton A) on the 12 pages that carry a rail, measured
at 390, 768, 1024, 1366 and 1920. Five defects, all of them cascade or ownership mistakes
rather than missing styles:

1. the phone layout lost 240px to a rail that was never supposed to be in the flow;
2. a persisted `rail-collapsed` shrank the mobile drawer to 64px;
3. the ☰ drawer control was visible on desktop, where `body.rail-open` means nothing;
4. the « collapse control was visible on phones, where its only effect was defect 2;
5. the 64px icon rail clipped its link labels mid-word at every width that used it.

Every block that carries a `$ ` command re-runs with
`node tools/report-verify.mjs docs/reviews/fix-shell-mobile-rail-drawer.md` (9 blocks, 0
mismatches). The two output-only blocks — the sweep rows and the drawer-rows — are printed
by `artifacts/verify_shell_responsive.mjs`, which needs the dev server and a browser, so the
gate reports them as uncheckable rather than pretending to verify them; the paragraphs
around them name the tool, the run and what it asserted.

## 1. What a phone saw

390px, `materials.html`, before: `body` resolved `grid-template-columns: 150px 0px 240px`
against a 390px viewport, so the topbar and `main` were **150px wide**, and the rail — which
should have been an off-canvas drawer — was a `position: sticky` grid item sitting at
x −90…150, painting 150px of itself over the page. `document.scrollingElement.scrollWidth`
was 390 throughout, so the page looked "fine" to any check that only watches for horizontal
scroll.

| 390px, `materials.html` | before | after |
| --- | --- | --- |
| body `grid-template-columns` | `150px 0px 240px` | `390px` |
| topbar width | 150 | 390 |
| `main` width (scroll width) | 150 (212) | 390 (390) |
| rail | `sticky`, 240px box at −90…150 — 150px visible | `fixed`, off-canvas, 0px visible |
| rail opened with ☰ | no such control reached the drawer | 240px, label text 72px wide |
| `main` width with a stored `rail-collapsed` + drawer open | 64px drawer, text spilling out | 240px drawer, labels intact |

Screenshots: [`mobile-shell-390-before.png`](mobile-shell-390-before.png) — the rail slab
over a 150px column; [`mobile-shell-390-after.png`](mobile-shell-390-after.png) — the same
page after; [`mobile-drawer-open-390.png`](mobile-drawer-open-390.png) — the drawer as it
now opens; [`mobile-390-persisted-collapse.png`](mobile-390-persisted-collapse.png) — the
64px drawer a stored collapse used to produce.

## 2. Root cause A — the rail's sticky column was declared twice

`§4 .app-rail` already declares `position: sticky; top: var(--app-topbar-h); align-self:
start; max-height: calc(100vh - var(--app-topbar-h))`. A second rule restated three of those
declarations at higher specificity:

```
$ git show HEAD:src/css/app-shell-v55.css | grep -n "sticky; top: var(--app-topbar-h); max-height"
572:body[data-shell="a"] > .app-rail { position: sticky; top: var(--app-topbar-h); max-height: calc(100vh - var(--app-topbar-h)); }
```

Specificity: `body[data-shell="a"] > .app-rail` is (0,2,1); the ≤768 drawer is written as a
bare `.app-rail`, (0,1,0). The drawer therefore **lost**, the rail stayed in the flow, and an
in-flow grid item whose `grid-area: rail` names an area the ≤768 template no longer defines
closes over two implicit columns — `0px 240px` — which starved the single explicit
`minmax(0, 1fr)` column down to 150px.

Both rules live in the same layer (`app-shell-v55.css` opens `@layer components` on line 1
and never closes it), so specificity and source order decided it, not layering. Deleting the
duplicate is the whole fix: §4 already gives the same values, so nothing changes at ≥769px
while the drawer wins on source order — the file's own "cascade fix, not a specificity arms
race" reasoning, used in §14 for the same kind of duplicate.

```
$ grep -c "sticky; top: var(--app-topbar-h); max-height" src/css/app-shell-v55.css || true
0
```

## 3. Root cause B — the collapse token leaked into the drawer

`--app-rail-w` is 240px and `--app-rail-w-collapsed` is 64px, both in `src/css/tokens.css`.
Two rules reassign the first to the second: `body[data-shell="a"].rail-collapsed` (on the
body — this feeds the ≥769 grid track, and is now gated to ≥769) and, inside the ≤1024 block,
`body.rail-collapsed .app-rail` (on the rail element itself). The only consumer of the
variable **on the rail element** is the drawer's `width`, one media query away:

```css
@media (max-width: 768px) { .app-rail { width: var(--app-rail-w); … } }
```

So the ≤1024 rule could only ever do one thing — open the phone drawer 64px wide. Measured at
390px with `einvite-rail-collapsed=1` stored: drawer 240 → 64px, its 72px link labels spilling
out of it, and no control left on the page to undo it (`rail-collapsed` is persisted, and the
collapse button is hidden below 768 for exactly this reason). The rule is gone; the ≥769 rule
on the body keeps desktop collapse working.

## 4. Root cause C — two navigation controls, each in the wrong place

The rail pages ship both a `«` collapse button and a `☰` drawer button, inside
`.app-topbar-left` / `.app-topbar-right` — **not** direct children of `<header>`. Three
consequences, all measured:

- The bare `.app-rail-toggle { display: inline-flex }` in the ≤768 block was inert: it is
  (0,1,0) and the buttons' `display` is set by (0,1,3) — `body:not(.guest) > header button` —
  in two editor sheets that rail pages also load:

```
$ grep -n 'body:not(.guest).\{0,3\}.header button' src/css/editor-suite.css src/css/canvas-plus.css | cut -c1-88
src/css/editor-suite.css:33:body:not(.guest) > header button{min-height:40px;padding:10p
src/css/canvas-plus.css:30:body:not(.guest) > header button{min-height:40px;padding:10px
```

- The matching desktop hide, `@media (min-width: 769px) { .app-drawer-toggle { display: none } }`,
  also (0,1,0), lost the same way. Measured at 1024px: the ☰ was visible at x 766, and
  clicking it set `body.rail-open`, which **no rule above 768 consumes** — a control in the
  desktop topbar that could not do anything.

```
$ git show HEAD:src/css/app-shell-v55.css | grep -n 'app-rail-toggle { display: inline-flex\|app-drawer-toggle { display: none'
515:  .app-rail-toggle { display: inline-flex; }
517:@media (min-width: 769px) { .app-drawer-toggle { display: none; } }
```

- The ≤768 show of the collapse button *did* take effect through the editor-sheet rule, so a
  phone got `«`, whose only effect is root cause B (a 64px drawer), and it was the first
  button in the tab order.

The fix names the shell and uses a descendant combinator: the buttons are not header
children, and (0,2,2) beats (0,1,3) on the class column. The collapse control is now offered
at ≥1025 (where the rail really is 240px or 64px; at ≤1024 the shell pins the column to 64px
itself, so it had nothing left to toggle) and the drawer control at ≤768.

## 5. Root cause D — the icon rail never hid its labels

`§11` hides `.app-rail__label` and `.app-rail__count` at ≤1024 and `body.rail-collapsed` hides
the same two classes. But `.app-rail__label` is only the "Workspace" **group heading**; each
link's own label is a bare `.i18n` span inside the anchor. So the 64px column rendered its
link text and clipped it at the rail's `overflow: hidden` edge: 17px of overflow at 1024px,
`Dashboa…` / `Templat…` cut mid-word, and the same at 1440px+ with the rail collapsed
(scrollWidth 80 against clientWidth 63).

Those spans are load-bearing for accessibility: every `.app-rail__icon` is `aria-hidden="true"`,
so the label text **is** the link's accessible name. Removing them would leave eight unnamed
links. They are therefore clipped, not hidden — the `.sr-only` declaration set from the reset,
applied to the label spans:

```css
@media (min-width: 769px) and (max-width: 1024px) {
  .app-rail a .i18n { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
                      overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
}
@media (min-width: 769px) {
  body.rail-collapsed .app-rail a .i18n { /* identical declaration set */ }
}
```

Both are gated to ≥769: below that the rail is the 240px ☰ drawer, where the labels are the
point. Measured after: rail scrollWidth − clientWidth = 0 at 1024 and at 1366-collapsed, 8/8
labels visible in the drawer, and the browser's own accessibility tree still reports nine
named rail links at every width (see §7).

## 6. The fix

`src/css/app-shell-v55.css` only — four deletions/replacements and two additions, all inside
the existing media blocks:

- delete `body[data-shell="a"] > .app-rail { position: sticky; … }` from §13, leaving a note
  where it stood (§2);
- wrap the body-level collapse reassignment in `@media (min-width: 769px)`, and delete the
  ≤1024 rule that reassigned it on the rail element (§3);
- `body:not(.guest) > header .app-rail-toggle { display: none }` in the ≤1024 block and in the
  ≤768 block, and `body:not(.guest) > header .app-drawer-toggle { display: none }` at ≥769 (§4);
- clip `.app-rail a .i18n` in the 64px states (§5).

No `!important`, no new files, no markup changes, and no generated artifact hand-edited.

## 7. Verification

`artifacts/verify_shell_responsive.mjs` — 40 rows (6 rail pages × 390/768/1024/1366, plus all
16 routes at 390) asserting: no implicit body tracks, no document overflow, no painted escape
past the viewport edge, `main`/topbar full width below 768, the closed drawer off-canvas, the
64px rail free of text overflow, and every rail link keeping label text. Output ends
`SUMMARY failures=0`. Representative rows (`materials.html`, the page the defect was found
on):

```
sweep         materials.html   390 tracks=1 390px                    main=390 rail=fixed/0 railScroll=0 labels=8/8 esc=0 ok
sweep         materials.html   768 tracks=1 768px                    main=768 rail=fixed/0 railScroll=0 labels=8/8 esc=0 ok
sweep         materials.html  1024 tracks=2 64px 960px               main=960 rail=sticky/64 railScroll=0 labels=0/8 esc=0 ok
sweep         materials.html  1366 tracks=2 240px 1126px             main=1126 rail=sticky/240 railScroll=0 labels=8/8 esc=0 ok
```

`labels=0/8` at 1024 is the icon rail doing what it says: text in the DOM and in the
accessibility tree, zero visible glyphs.

The drawer and accessibility checks in the same run:

```
DRAWER @390: pos=fixed visible=240 width=240 labels=8/8 main=390
A11Y @390: 9 named rail links -> ["Templates","Dashboard","Templates","Materials"]
A11Y @1024: 9 named rail links -> ["Templates","Dashboard","Templates","Materials"]
A11Y @1366: 9 named rail links -> ["Templates","Dashboard","Templates","Materials"]
SUMMARY failures=0
```

<!-- report-verify: measurement same run as above -->

Collapse still works where it is offered, and never overflows (measured by
`artifacts/probe_desktop_toggle.mjs`, which clears the stored flag, reloads, reads the rail,
clicks the real button and reads again):

| viewport | `«` visible | rail before | rail after | rail content overflow | labels after |
| --- | --- | --- | --- | --- | --- |
| 1025 | yes | 240px | 64px | 0px | 0 |
| 1280 | yes | 240px | 64px | 0px | 0 |
| 1366 | yes | 240px | 64px | 0px | 0 |

Screenshots for the three states the fix defines:
[`mobile-rail-1366.png`](mobile-rail-1366.png) (240px rail, labels),
[`mobile-rail-1366-collapsed.png`](mobile-rail-1366-collapsed.png) (64px icon rail, no
clipped words), [`mobile-rail-1024.png`](mobile-rail-1024.png) (the same icon rail at the
tablet breakpoint), [`mobile-drawer-open-390.png`](mobile-drawer-open-390.png) (the phone
drawer, 240px with labels).

The build gate, with every generated artifact re-derived from its sources:

```
$ python3 build.py all --check | tail -4
css: drifted=0 up_to_date=88
organized: drifted=0 up_to_date=15
MIRROR_CHECK_PASSED (up_to_date=323)
BUILD_OK editor bundles manifests mirror (check)
```

## 8. Left alone, and residual risk

- **`body:not(.guest) > header button` still styles the two toggles.** That (0,1,3) rule gives
  every topbar button `min-height: 40px; padding: 10px 14px; border-radius: 12px` — the toggles
  wear it (44px tall) even though it was written for the editor's header actions. It is what
  made the two visibility rules lose, but it is not itself wrong, and narrowing it would
  restyle the editor topbar on 12 pages; the visibility rules now out-rank it by selector
  instead. Reported, not changed.
- **The editor (`index.html`) keeps its off-canvas panes.** At 390px `div.toolbar[-216..20]`,
  `div#v23ContextToolbar[-95..15]` and similar sit at negative x. The sweep's classifier
  checks ancestors for `overflow-x != visible` and for hidden/transparent ancestors, and
  classifies all of them as clipped inside their own pane — `esc=0` at 390, 768 and 1366 (see
  [`mobile-editor-390.png`](mobile-editor-390.png)). They are pre-existing, unrelated to the
  shell, and not reported as defects here.
- **Shell B pages inset `main` by 16px** (`privacy.html` at 390px: topbar 390, `main` 358 at
  x 16). That is the skeleton's own padding box, not a symptom; the sweep asserts full width
  only on shell A pages with a rail.
- **The rail's `--app-rail-w` has no consumer above 768 any more** other than the grid track
  on the body. If a future sheet reads it from the rail element, the ≤1024 collapse rule this
  pass deleted will not be there to set it.
