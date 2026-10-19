# Agent protocol

Ported from the opencode global config (`~/.config/opencode/AGENTS.md`) and adapted for Freebuff,
which has no subagent dispatch, no MCP config, and no plugin API.

## Project memory

- Resume state: `artifacts/ui-audit/fixes/STATE.md` — read it before continuing any eInvite work
  (hard rules, current pass, open items, next move); update its Done / Active / Next Move at the
  end of a work session.
- Sessions started outside this repo can reach the same pointer via the global `einvite-project`
  skill (`~/.agents/skills/einvite-project/SKILL.md`).

## Skills-first (every task)

- Whenever the user assigns a task — any new request, or anything related to their projects — FIRST
  scan the available skills list and load every skill whose name/description matches the task's
  domain. Do this before planning and before touching files.
- Follow the skill's guidance while executing. If a step assumes tooling that does not exist here
  (see "Not portable"), do the equivalent with the tools you have and say what you substituted.
- No matching skill → proceed normally; never force-fit one.
- Match examples: documents → docx/pptx/xlsx/pdf; web/UI → frontend-design, webapp-testing,
  web-design-guidelines, playwright-expert; reverse engineering → reverse-engineer-anything;
  plans and implementation → writing-plans, subagent-driven-development; creative work →
  brainstorming, canvas-design, algorithmic-art.
- Skill locations: `~/.agents/skills/<name>/SKILL.md` (global, shared with opencode) and
  `.agents/skills/<name>/SKILL.md` (project). Install new skills there; don't invent a third location.

## Workflow: plan → execute → verify

The opencode setup delegates to `explore`/`general` subagents. Freebuff has no subagent-dispatch
tool, so:

- Do the work in this session. Never claim or imply a subagent ran it.
- Keep the discipline delegation existed to enforce: plan the work, split it into workstreams, do
  them in dependency order, and verify each result before starting the next.
- Batch genuinely independent steps (parallel tool calls, background jobs), but judge each result
  instead of accepting it.
- Verify critical claims with a cheap targeted check — read the file, run the test, inspect the
  diff — before reporting anything as done.
- Never report a check as passing unless you ran it and saw it pass. Report checks that failed or
  could not run as limitations, never as passes.
- Fix the cause of a failing check. Do not skip tests, weaken assertions, swallow errors, or add
  suppressions just to go green.
- Trivial single steps (one read, one command) are done directly; there is no delegation tier here.

## Free-quota policy (offloading to opencode only)

Applies only when work is deliberately handed to opencode/OpenRouter free models (e.g.
`opencode run ...`). It does not apply to Freebuff's own model.

- Free cap: 1000 requests/day (UTC), shared across the account.
- Read `~/.config/opencode/openrouter-quota.json` (`remaining`, `estimatedRemaining`, `updatedAt`)
  or the `[quota] ...` line opencode injects.
- N > 25 → offload freely. N ≤ 25 → essential runs only, batched. N = 0, or persistent
  quota/rate/overload errors → stop offloading, finish directly, and tell the user the cap resets
  at 00:00 UTC.
- Model fallthrough (laguna → ultra → inkling → free router) is expected load-shedding, not
  failure. Treat a task as failed only if the run itself errors.

## Subagent speed rule (offloaded runs only; user threshold 30 tok/s)

- Metric: generated tokens (output + reasoning) ÷ generation time, aggregated over the run's
  assistant messages.
- Measure: `node ~/.config/opencode/orchestrator/tps.mjs <sessionID>`. It reads opencode's local
  message store, prints per-message and aggregate tok/s, and appends the result to
  `~/.config/opencode/subagent-speed.json`.
- ≥ 30 tok/s → healthy, continue. < 30 tok/s → salvage the result and finish/verify the rest
  directly. Two consecutive slow runs → stop offloading for the session.
- If a run can't be measured (aborted, no usage recorded), judge by wall-clock: many minutes for a
  small task = slow → take over.

## Reporting

- Only the primary agent talks to the user: what's done, what's verified, what's still open.
  Don't narrate mechanics.
- Explicit user instructions always win — "do it yourself" overrides every offloading rule above.

## Keeping global skills in sync

Skills are copied one way from opencode. Nothing here edits opencode's config.

- `~/.agents/sync-opencode-skills.sh` copies `~/.config/opencode/skills/` → `~/.agents/skills/`.
  It adds new skills and missing files, never overwrites an existing file, and reports the
  Freebuff-adapted skills it left alone. `--dry-run` shows what would change.
- Adapted skills: `subagent-driven-development`, `dispatching-parallel-agents`, `code-review`,
  `requesting-code-review`, `using-superpowers`. The sync will not revert them; a manual copy
  will.

## Not portable from opencode

The `general`/`explore` subagents and their models, the `rea` MCP server, the `openrouter-quota`
plugin, and automatic tok/s tracking. Nothing here attempts to fake them.

Two workflow skills carry Freebuff adapters that override their upstream text:

- `subagent-driven-development` → "Freebuff execution mode": roles become passes, and the brief,
  report, and review-package files are the isolation boundary.
- `dispatching-parallel-agents` → "Parallel Workstreams": workstreams are parallel tool calls and
  background jobs, with disjoint file sets for edits.
- `using-superpowers/references/freebuff-tools.md` lists the remaining host differences.
