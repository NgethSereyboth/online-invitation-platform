# Branch review note — `pass/2026-10-21-next-work` (2026-10-21)

Read this instead of running anything: each commit below carries its own verification
evidence. Code HEAD `11e549f`, docs HEAD `15554e3`, cut from `50721ef`. Push/release is
OD-3-gated (see [RELEASE-CANDIDATE.md](RELEASE-CANDIDATE.md)).
Branch-wide live results on this machine: full pytest 142 passed / 1 pre-existing OD-7
digest-pin failure; `tools/run-gates.py` build/bundles/smoke/lhci/canvas all PASS.

## Commit-by-commit

| # | Commit | Type | Delta shape | What changed | Verified how |
|---|---|---|---|---|---|
| 1 | `ec0cf91` | fix(a11y) | 21 files, +100/−40 | The six WCAG 2.2 AA code asks (NW-1.1–1.6): keyboard page-reorder moves in [page-experience.js](src/js/page-experience.js), `autocomplete` attrs on signup-sheet/poll forms and `#accessPassword`, 24×24 live handle hit box via `::before` in [professional-editor.css](src/css/organized/professional-editor.css), doc relabels in the two a11y audits | Measure-first ledger: focus-obscured 92 controls/0 obscured (4 viewports × light/dark), target-size 4/4 ×2 runs, reorder keyboard 8/8, bilingual checker exit 0 |
| 2 | `6a30d9e` | feat(i18n) | 44 files, +1286/−436 | `EInviteI18n.applyOptionLabels()` + 14 bilingual `<option>` labels (materials/responses), CSV reconcile archive (286 stale rows, none deleted — [TRANSLATIONS.csv](docs/i18n/TRANSLATIONS.csv)), Khmer visual sweep shipped | Live EN→KM→EN 0 failures; checker exit 0; Khmer sweep 21/21 |
| 3 | `8952381` | test(ci) | 3 files, +209 | Portable one-command gate runner [run-gates.py](tools/run-gates.py) + docs (NW-5.3/5.4); allowlist startup-race fix lands in the same commit's scope | Each phase re-run → `GATES_PASSED` |
| 4 | `cd56ac0` | test(ci) | 1 file, +10/−2 | The allowlist implementation file (`tests/security_admin_ip_allowlist_test.py` exit-poll) omitted from `8952381` | Single file 14/14 after the fix |
| 5 | `837042f` | docs | 2 files, +87 | New [RELEASE-CANDIDATE.md](RELEASE-CANDIDATE.md) + [STATUS-INDEX](docs/STATUS-INDEX.md) | — |
| 6 | `ca53dbe` | fix(a11y) | 13 files, +29/−29 | Gradient AA close: `.fp-profile-button` light stop → `color-mix(in srgb,var(--app-accent-2) 65%,var(--app-accent))` in [final-polish.css](src/css/final-polish.css); bundles/manifests regenerated | In-browser: computed `backgroundImage` light end rgb(170,95,118); white ratio 4.56 ≥ 4.5; `build.py all --check` green |
| 7 | `11e549f` | fix(a11y) | 6 files, +12/−8 | NW-6.3 reachability close: thin visible scrollbar on `.stage-wrap>.studio-canvas-toolbar` from 701px up in [workflow-final-audit.css](src/css/organized/workflow-final-audit.css) (mobile ≤700 keeps hidden-scroll convention) | In-browser at 1440/1366/1024/768/375: after scroll `#v23ContextToolbar` buttons win `elementFromPoint`; no vertical clipping; row height unchanged |
| 8 | `15554e3` | docs | 2 files, +16/−8 | STATUS-INDEX + RELEASE-CANDIDATE refreshed to the final HEADs (commit list, NW-6 execution, link check) | Automated link check: 0 broken links |

## Review framing

- **No behavior change on guest/public routes** — every code commit except `11e549f` touches
  editor/dashboard surfaces; `11e549f` changes only scrollbar visibility on the canvas
  toolbar row.
- **Bundle discipline**: every `src/` CSS/JS edit is committed together with its
  regenerated bundles, mirrors and manifest SHA updates — the `build.py all --check`
  gate proves the tree is self-consistent without re-running anything.
- **The one red**: `tests/v27_3_5_release_evidence_test.py` README digest pin (OD-7) —
  pre-existing since the 2026-10-17 README rewrite (`23f7cf6`), untouched by this branch
  (`git log -- README.md` shows no branch commit).
- **Owner-gated items still open**: OD-1 (CSS dead-rule scope), OD-2 (dashboard parity
  subset), OD-3 (push/release), OD-7 (digest), OD-8 (11 Khmer strings) —
  [DECISIONS.md](../artifacts/next-work/DECISIONS.md) (untracked evidence tree).
