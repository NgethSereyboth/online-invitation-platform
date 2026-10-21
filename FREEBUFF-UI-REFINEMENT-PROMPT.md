# Freebuff prompt — eInvite visual-quality, research & testing pass

You are Freebuff, acting as a senior product designer, frontend engineer, and QA lead for this
repository. Work in `F:\Project\eInvite\online-invitation-platform` (Windows / PowerShell). Do the
work yourself in this session — this repo's `AGENTS.md` says Freebuff has no subagent dispatch; do
not claim or imply a subagent ran anything.

## Mission

The functional rebuild is done and the gates are green, but the owner still feels the **overall
look and feel is lacking**. Run a full visual-quality programme:

1. **Research** best-in-class design-tool and invitation-product UIs and compare them with ours,
   screen for screen.
2. **Audit** the real rendered UI thoroughly — every page, state, viewport, theme, and language —
   with screenshots, heuristics, Lighthouse, and human design critique.
3. **Define a direction** that is specific to this product (Cambodian wedding/event stationery and
   a professional design tool), not a generic SaaS skin.
4. **Implement** targeted refinements in small, verified batches.
5. **Prove** every claim with before/after evidence and a gate run.

Do **not** add features, rebuild the canvas, or change product behaviour. This is a look, feel,
hierarchy, polish, and perceived-quality pass.

## Read first, in this order

1. `AGENTS.md` — the repo's agent protocol and skill locations.
2. `artifacts/ui-audit/fixes/STATE.md` — hard rules, current HEAD (`1f28cbc`), gate procedure,
   evidence map. If the file is absent on this machine (`artifacts/` is git-ignored), reconstruct
   the baseline via `NEXT-WORK-TASK.md` Phase 0 first.
3. `NEXT-WORK-TASK.md` — the current work order; this prompt is an additional visual pass that
   complements its Phase 6. Do not duplicate or conflict with its Phase 1 (WCAG), Phase 2 (CSS
   cleanup), or Phase 4 (i18n) unless a visual fix directly requires it.
4. `artifacts/ui-refinement/{RESEARCH,AUDIT,DIRECTION,REPORT}.md` — the 2026-10-21 visual pass
   already exists (committed as `1cd09d2`; evidence is local-only). Read it, extend it, and do not
   restart the research or re-implement the rose-accent/paper-mat/template-filter changes.
5. `CANVA-UI-TASK.md` and `artifacts/ui-audit/fixes/canva-ui/RESULTS.md` — what the last visual
   pass actually shipped and which heuristics are known false positives.
6. `DESIGN-FIX-REPORT.md` and `artifacts/ui-audit/fixes/RESULTS.md` — poster/editor fixes and
   pass-2 evidence.
7. `UI-VISUAL-AUDIT-FIX-TASK.md` §0 and §2 — the original findings, severity legend, and the
   documented heuristic caveats.

**Current baseline:** HEAD `1f28cbc`, gates green, 143/0 pytest, canvas visual 6/6 max 0.57 %.
`1cd09d2` already unified the brand rose accent, added `--paper-mat`/`--paper-well`, and made the
Template Studio filter band one row. Treat that as the starting point, not a blank slate.

**Preserve work you did not create.** Check `git status` first; do not revert uncommitted changes
that belong to the owner or another agent, including docs (`STATE.md`, `NEXT-WORK-TASK.md`, the
status banners in the root work orders).

## Skills to load before planning (required)

Load each matching skill and follow it. They live in `~/.agents/skills/<name>/SKILL.md` and
`.agents/skills/<name>/SKILL.md`:

- `frontend-design` — distinctive visual direction, typography, palette, restraint, self-critique.
- `web-design-guidelines` — fetch the current Vercel web-interface guidelines and review against
  them.
- `playwright-expert` — reliable browser automation, page objects, screenshots, flake control.
- `webapp-testing` — interacting with and testing the local web app.
- `visual-regression` — before/after capture and diff discipline.
- `horizontal-scroll` — 320 px / 400 % zoom overflow audit.
- `text-expansion` — translatable strings, truncation, fixed dimensions.
- `flexbox-patterns` — layout review across breakpoints.
- `brainstorming` — before choosing a visual direction (this is creative work).
- `writing-plans` — if you turn the audit into a task plan.

State in your report which skills you loaded and how each changed a decision.

## Hard rules (non-negotiable)

- **Never edit frozen canvas files:** `artifacts/canvas-motion/**`, `docs/CANVAS-SMOOTHNESS-BRIEF.md`,
  `tests/canvas_motion_playwright.py`, `tools/canvas-motion-*.{mjs,py}`, or any canvas
  threshold/baseline.
- **Never weaken gates, tests, thresholds, or budgets:** `tools/lighthouserc.js` and
  `docs/perf/lighthouse-budgets.json` are read-only. Do not skip tests or loosen assertions.
- **Never run `git clean -fdx`.** Never delete anything under `artifacts/`.
- **One heavy Chrome at a time.** Restart `tools/_pin-renderer.ps1` before gate/capture runs. No
  source edits while a run is in flight.
- **After every `src/` JS/CSS/HTML edit:** `python3 build.py all` (`BUILD_OK` +
  `MIRROR_CHECK_PASSED`), then `python3 build.py bundles --check`
  (`ROUTE_BUNDLE_CHECK_PASSED`). Verify the served mirror refreshed.
- **No new `!important`**, no new external dependencies, no npm bundlers, no new `innerHTML` in
  editor JS. Use the existing token/cascade contract:
  `@layer reset, tokens, base, layout, components, utilities, overrides`.
- **Bilingual:** every new user-visible string gets `.i18n-en` + `.i18n-km` (or
  `EInviteI18n.langText`/`_txt`). Khmer line-height ≥ 1.6. Run
  `scripts/check-bilingual-consistency.py`.
- **Do not stage `src/python/data/`.** Do not push. Commit only after verification.
- **Do not edit the visual baseline.** If the editor chrome changes make the frozen visual gate
  fail, stop and report; the owner must approve a re-anchor. Never edit
  `artifacts/canvas-motion/baseline/**` yourself.

## Context that should shape the design

- The product is a **Cambodian wedding/event invitation and poster design tool**: invitations,
  RSVP/guest management, seating/check-in, templates, and a Canva-style editor.
- The **user's artwork is the hero**, not the app chrome. The shell should be quiet, precise, and
  editorial so the invitation/poster carries the emotion. Competing decoration in the chrome will
  make the product feel cheaper.
- The existing brand tone is a Khmer-rose direction (`src/css/modern-ui.css`, `tokens.css`). Refine
  it; do not rebrand from zero, and do not copy competitor pixels or assets.
- Draw the distinctive details from the subject's world — stationery, paper stock, foil, silk,
  Khmer letterforms, editorial layout — not from generic AI palettes. Avoid the three default
  AI-design looks the `frontend-design` skill warns about (cream + serif + terracotta; near-black +
  acid green; broadsheet hairline columns). They are defaults, not choices.
- The owner's complaint is qualitative. Translate it into evidence: which screens feel generic,
  flat, cramped, noisy, or inconsistent, and why. Do not assume; look at the screenshots.

---

## Phase 1 — Research and comparison (do this before designing)

Produce `artifacts/ui-refinement/RESEARCH.md`.

- Study **6–8 comparables**, at least four from the invitation/event world and at least two
  professional design tools:
  - Canva — editor and home/dashboard
  - Adobe Express — editor and template gallery
  - Framer or Webflow — dashboard/editor chrome
  - Paperless Post — invitation browse and send flow
  - Minted — invitation gallery and product detail
  - Zola or WithJoy — wedding site, RSVP, guest management
  - Evite — event page and RSVP
  - One more of your choice if it adds a distinct pattern
- For each, capture or cite the exact screen and record: URL, date accessed, screen type, 3–5
  patterns worth studying, what works and why, what would **not** fit eInvite, and the principle to
  adopt (not the pixels).
- Build a **comparison matrix** scoring our screens and the references on the same rubric (below):
  current score, reference score, gap, proposed response.
- Create side-by-side comparison boards under `artifacts/ui-refinement/research/compare-*.png`
  (current eInvite screen beside the reference screen, same viewport where possible). If you cannot
  capture a reference, use an annotated citation instead — never fabricate a screenshot.
- Do not copy proprietary layouts, illustrations, icons, or copy. Extract principles only.

**Research questions to answer explicitly:**
1. What makes the first screen of each comparable feel premium rather than templated?
2. How do they create hierarchy without adding decoration?
3. What is their spacing/type rhythm, and how does ours differ?
4. How do they treat empty states, loading, errors, and first-run guidance?
5. How do they keep the editor chrome quiet around the user's canvas?
6. What do they do on mobile that we do not?

---

## Phase 2 — Thorough UI audit (rendered, not source-only)

Produce `artifacts/ui-refinement/AUDIT.md` plus the full capture set.

### Matrix

- **Pages (16):** `index.html` (editor), `dashboard.html`, `public.html`, `templates.html`,
  `guests.html`, `responses.html`, `materials.html`, `checkin.html`, `designer.html`,
  `account.html`, `billing.html`, `analytics.html`, `admin.html`, `privacy.html`, `verify.html`,
  `reset.html`.
- **States:** signed-out and signed-in; empty and populated; dialogs open; hover/focus/pressed;
  poster doc vs invitation doc; mobile rail/drawer open and closed; first-run tour dismissed and
  present.
- **Viewports:** 320×568, 375×667, 768×1024, 1024×768, 1440×900.
- **Themes:** light and dark.
- **Languages:** EN and KM.
- **Interactions:** keyboard-only traversal, reduced motion, zoom 200 %/400 %, long translated
  strings, slow network/loading, error states.

Use the existing instruments; do not invent a parallel stack:

```powershell
$env:CHROME_PATH = "$env:LOCALAPPDATA\ms-playwright\chromium-1228\chrome-win64\chrome.exe"
powershell -ExecutionPolicy Bypass -File tools\_pin-renderer.ps1

python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- python3 tools/ui-audit-capture.py --out artifacts/ui-refinement/before

python3 tools/ui-audit-digest.py --dir artifacts/ui-refinement/before --out artifacts/ui-refinement/before-digest.txt
python3 tools/ui-audit-summary.py --section hscroll|overflow|contrast|occlusion|tiny|errors

# static server + smoke
python3 tools/serve-gzip.py --port 8124
node tools/page-errors.mjs --all

# Lighthouse
npx lhci collect --config=tools/lighthouserc.js
npx lhci assert --config=tools/lighthouserc.js
```

### Rubric (score 1–5, with evidence for every score)

1. First impression / brand distinctiveness
2. Visual hierarchy and focal point
3. Layout and spacing rhythm
4. Typography: scale, weights, line length, rhythm
5. Color and contrast (light + dark)
6. Component consistency: buttons, cards, inputs, tabs, tables
7. Iconography and alignment
8. Density vs whitespace
9. Empty / loading / error / first-run states
10. Motion and feedback (transform/opacity, reduced motion)
11. Responsive composition (320/375/768/1024/1440)
12. Localization: Khmer line-height, expansion, mixed-language dupes
13. Accessibility affordances: focus-visible, hit targets, keyboard
14. Craft details: radii, shadows, borders, dividers, alignment, optical balance

### Findings

- Produce a ranked list of the **top 25 issues**, each with: page, state, viewport, theme, selector,
  screenshot path, computed cause (which rule wins), proposed fix, effort S/M/L, expected impact
  H/M/L, and whether it is a real defect or a documented heuristic false positive.
- Include **look-and-feel issues the heuristics cannot see**: weak hierarchy, generic card grid,
  inconsistent radii/shadows, uneven baselines, icon optical misalignment, competing accents,
  noisy borders, flat dark mode, weak empty states, microcopy that sounds like a system message.
- Separate **regressions** (something the last pass broke) from **never-finished polish**.
- Do not chase the documented false positives: billing gradient rows, admin mock-403 rows,
  `designer.html` CSP `unsafe-eval`, sticky-header occlusion from scrolled rescans, icon-only
  "tiny text", and translucent `color(srgb …)` surfaces.

---

## Phase 3 — Direction (before mass edits)

Produce `artifacts/ui-refinement/DIRECTION.md`.

- Write a short **design critique** in plain language: why the current UI reads as lacking, with
  screenshots as evidence.
- Propose **2–3 directions**, each with: palette (4–6 named hex values), type roles (display, body,
  utility), layout concept, density, motion character, and one **signature element** that makes
  eInvite recognizable without decorating every screen.
- Pick one direction and justify it against the brief, the comparables, and the constraint that the
  artwork is the hero. Explain what you deliberately rejected.
- Define the **design contract**: spacing scale, type scale, radii, shadow levels, border colors,
  accent hierarchy, focus ring, dark-mode mapping, motion durations/easings. Reuse existing tokens
  where they already exist; propose token changes, not per-page literals.
- Show the direction on 2–3 representative screens (dashboard, templates, public invitation) with
  before/after mockups or a small CSS prototype. Do not mass-edit before the direction is coherent.
- If a decision is genuinely the owner's (rebrand-level palette change, removing a feature), record
  it as an owner decision and continue with the rest.

---

## Phase 4 — Implement in small, verified batches

Suggested order; keep each batch independently revertible:

- **Batch A — tokens & primitives:** spacing, type scale, radii, shadows, borders, focus ring,
  surface/elevation hierarchy. No layout changes yet.
- **Batch B — app shell:** topbar, rail, breadcrumbs, page header, tabs, statusbar; one clear
  hierarchy and one accent surface.
- **Batch C — components:** cards, lists, tables, forms, buttons, empty/loading/error states.
- **Batch D — dashboard and templates:** the "first screen" and the gallery; make the designs the
  hero, not the chrome.
- **Batch E — public invitation and guest flow:** cover → hero → schedule → RSVP → footer; preserve
  the artwork and the WYSIWYG paper.
- **Batch F — editor chrome only:** rail, inspector, toolbars, statusbar, dialogs. **Do not touch
  canvas rendering.** Run the frozen visual gate after the batch; if it fails only because of an
  intended chrome change, stop and report for owner re-anchor.
- **Batch G — polish:** microcopy, KM expansion, dark-mode details, reduced motion, focus parity,
  optical alignment.

Rules for every batch:

- Prefer a **small number of systemic rules** over page-by-page overrides. No new `!important`.
- Derive colors/spacing from tokens; do not add one-off hex values.
- Keep behavior, routes, IDs, i18n spans, and JS contracts intact.
- After edits: `python3 build.py all`, `python3 build.py bundles --check`, smoke, targeted capture.
- Compare before/after at the same viewport/state; revert the batch if an unintended diff appears.
- Commit each verified batch with a clear message; do not push.

---

## Phase 5 — Verification (thorough, evidence-first)

Run and record all of these; a claim without a command + exit code + evidence path is not a result.

- **Build:** `python3 build.py all`, `python3 build.py bundles --check`.
- **Smoke:** 16 pages, `consoleErrors=0`, `non2xx=0`.
- **Full pytest:** `python3 -m pytest tests/ -q -s`; record the exact count; no new failures.
- **LHCI:** collect + assert; 16 pages, a11y 1.00, budgets unchanged.
- **Canvas gates** if editor chrome changed:
  - acceptance `python3 tests\canvas_motion_playwright.py --phase all ...` → 22/0/2;
  - perf → exit 0, `failures: []`, no frame ≥50 ms;
  - visual → 6/6 ≤3.5 % (or stop and report an intended-diff re-anchor request).
- **Responsive:** 0 horizontal document scroll at 320/375 on every page; 400 % zoom spot-check.
- **Text:** no clipped/truncated user-facing text; KM expansion and line-height; no duplicated
  EN/KM strings.
- **A11y:** focus-visible parity, no focus traps, hit targets ≥24×24 where applicable, reduced
  motion kills tweens, contrast targets (4.5:1 body / 3:1 large).
- **Console/network:** 0 errors, 0 unexpected 404s.
- **Pixel diff:** compare the full capture set with `artifacts/ui-refinement/before`; classify
  every diff as intentional or unintended. Unintended → fix or revert.
- **Performance:** check route weight and the editor perf trace; no layout-thrashing transitions,
  no CLS regression.

Save everything under `artifacts/ui-refinement/after/` and `artifacts/ui-refinement/verify/`.

---

## Phase 6 — Report and handoff

Produce `artifacts/ui-refinement/REPORT.md` containing:

1. Executive summary: what felt lacking, what changed, what the result now feels like.
2. Research table with citations and the comparison matrix.
3. Rubric scores before/after, with the evidence for each change.
4. Top-25 issue list with status (fixed / deferred / owner decision / false positive).
5. Files changed and why; tokens introduced/changed.
6. Gate results (exact commands, exit codes, key output lines).
7. Screenshots: before/after pairs, mobile/dark/KM states.
8. Open items and owner decisions; anything you deliberately did not do.
9. A one-paragraph "next design move" if the owner wants a second pass.

Update `artifacts/ui-audit/fixes/STATE.md` (Done / Active / Next Move) with the new HEAD, the pass
summary, and the evidence paths. Update `NEXT-WORK-TASK.md` Phase 6 checkboxes only where this pass
actually closed them.

---

## Definition of done

- Research, audit, direction, implementation, verification, and report all exist as files.
- The five highest-impact "looks lacking" issues are fixed and evidenced; the rest are ranked.
- No gate was weakened; all gates pass, or the only failure is a documented intended visual diff
  awaiting owner re-anchor.
- 0 horizontal scroll at 320/375, 0 console errors, no clipped text, KM/dark/reduced-motion intact.
- The UI has a coherent hierarchy and one recognizable signature element; the chrome no longer
  competes with the artwork.
- `STATE.md` and `NEXT-WORK-TASK.md` reflect the truth; nothing pushed.

## If you get stuck

- A gate is red and the cause is not yours → stop, report command + log path, do not "fix" the gate.
- A change needs a frozen file, threshold, or baseline → stop and ask the owner.
- A visual change is intentional but the frozen editor gate flags it → stop and request a
  re-anchor; never edit the baseline.
- Two heavy Chrome runs would overlap → serialize; never run them concurrently.
- The direction starts looking like a generic template → return to the subject (Khmer stationery,
  editorial layout, the artwork as hero) and remove one accessory before adding another.
