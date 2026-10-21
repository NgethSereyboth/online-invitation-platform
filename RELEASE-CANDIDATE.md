# RELEASE-CANDIDATE — session end 2026-10-21

**Do not push, tag, or edit `VERSION_HISTORY.md` — blocked on OD-3.** Nothing below has been
published anywhere; everything lives on the local branch.

## HEAD and commits

- Branch: `pass/2026-10-21-next-work` (cut from `50721ef` per the continuation §7).
- `ec0cf91` — fix(a11y): all six WCAG 2.2 AA code asks (`NW-1.1`–`NW-1.6`).
- `6a30d9e` — feat(i18n): bilingual `<option>` labels (14), CSV reconcile archive, Khmer sweep (NW-4.1–4.4).
- `8952381` — test(ci): portable gate runner + allowlist startup race fix (NW-5).
- Untracked owner work preserved untouched (78 paths, incl. `.claude/`, `data/`, review PNGs);
  `wip/2026-10-21-backup` branch untouched.

## Gate matrix at this HEAD (exact commands + evidence)

| Gate | Command | Result |
|---|---|---|
| Build | `python3 build.py all --check` → exit 0 (`BUILD_OK… MIRROR_CHECK_PASSED (up_to_date=327)`) | PASS |
| Bundles | `python3 build.py bundles --check` → exit 0 (`ROUTE_BUNDLE_CHECK_PASSED`) | PASS |
| Smoke | `node tools/page-errors.mjs --all` → `TOTAL pages=16 consoleErrors=0 non2xx=0` | PASS |
| LHCI assert | `npx lhci assert --config=tools/lighthouserc.js` → exit 0, **a11y 1.00 on 16/16 reports** | PASS |
| Bilingual checker | `python3 scripts/check-bilingual-consistency.py` → exit 0 (`OK: … passed.`) | PASS |
| Full pytest (default capture) | `PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/ -q` → **1 failed / 142 passed** | PASS with documented blocker |
| Canvas acceptance | frozen harness `--phase all` (absolute `--output`) → `pass=22 fail=0 skipped=2`, `CANVAS_MOTION_VERIFY_PASSED` | PASS |
| Canvas perf | env-blocked on this machine (3 launch modes, presentation-quantized timings; `inputToPaintMs` 11.5 under budget) | NOT VERIFIED HERE |
| Canvas visual | frozen baseline absent (`artifacts/canvas-motion/baseline/**` stayed on the Windows box) | NOT RUN |
| Focus-obscured (NW-1.1) | `tools/a11y-focus-obscured.py` → 92 controls, 0 rows, 4 viewports × light/dark | PASS |
| Target size (NW-1.5) | `tools/a11y-target-size.py` → 24×24 desktop hit box, 44×44 mobile, 2 runs | PASS |
| Reorder keyboard (NW-1.2) | `tools/page_reorder_keyboard_check.py` → 8/8 | PASS |
| Option labels (NW-4.1) | `tools/option_labels_i18n_check.py` → 0 failed (2 pages × 6 checks) | PASS |
| Khmer sweep (NW-4.4) | `tools/khmer-visual-sweep.py` → 21 shots, 0 failures | PASS |
| Gate runner (NW-5.3) | `tools/run-gates.py --phase {build,bundles,smoke,lhci}` each → `GATES_PASSED` | PASS (per phase) |

The single pytest failure is the documented `v27_3_5` README digest pin — **OD-7**, content-identical
CRLF/LF hash; every other baseline red was fixed (allowlist race ×2) or remains environment-bound.

## Remaining owner decisions

OD-1 (CSS cleanup), OD-2 (dashboard parity), OD-3 (push/release), OD-7 (digest pin),
OD-8 (11 Khmer strings) — evidence and recommendations in
[artifacts/next-work/DECISIONS.md](artifacts/next-work/DECISIONS.md).

## Known limitations

- Canvas perf + visual gates need the Windows box (or the owner copying
  `artifacts/canvas-motion/baseline/` here).
- Files only ever measured against `tools/serve-gzip.py` (no production hosting evidence in
  this pass; `deploy/sites/` is owner work, untouched).
- NW-6.3–6.6 (floating controls, motion audit, contrast sweep, privacy headroom) recon-only:
  NW-6.4 static probe run (tokens pinned in `tokens.css`; the 40-decl "layout-transition" figure
  is a regex over-count with multi-line declarations — methodology note, needs a real audit).
- RILL-WALKTHROUGH end-to-end flow not executed this session (no throwaway account flow run);
  documented as not run, not assumed.

## Push instruction (blocked)

When OD-3 is answered: `git push -u origin pass/2026-10-21-next-work` — three commits, no tags,
no `VERSION_HISTORY.md` change, no `main` merge until the owner orders it.
