/**
 * report-verify.mjs — re-run the read-only commands a report quotes, and diff the
 * recorded output against what the command actually prints now.
 *
 * Why this exists
 * ---------------
 * This report's standard is that a number is only believable if the command that
 * produced it is printed next to it. That standard has a hole: nothing checked that
 * the printed block was the command's *actual* output. During the final check one
 * block in §1.2 was found to be re-typed from memory — nine evidence files
 * condensed into one row labelled "(8 files, 780 lines)" and the trailing
 * `27 files changed, 3514 insertions(+)` line dropped. Every command in that block
 * was successful and the numbers were close; only a diff catches it.
 *
 * What it does
 * ------------
 * Extracts ```-fenced blocks from a markdown file. For each block shaped as
 *
 *     $ <command>
 *     <recorded output...>
 *
 * (exactly one `$` command line, no further `$` lines) it runs the command and
 * byte-compares the output, after stripping each line's trailing whitespace.
 *
 * Safety: only explicitly allow-listed read-only command prefixes run. Anything
 * else — servers, builds, `make`, `npx`, redirections, writes — is reported as
 * skipped, never executed.
 *
 * Usage
 * -----
 *   node tools/report-verify.mjs docs/reviews/reproducibility-and-performance-report.md
 *   node tools/report-verify.mjs <file> --all      # also show passing blocks
 *   node tools/report-verify.mjs <file> --json     # machine-readable summary
 *
 * Exit status: 0 when no block mismatched, 1 when at least one did, 2 on bad input.
 */
import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { REPO_ROOT, argValue, hasFlag } from './lib/repo.mjs';

/**
 * Read-only command prefixes that are safe to re-run. Deliberately narrow: an
 * allow-list, not a deny-list, because this tool executes text lifted out of a
 * document. Anything absent here is skipped and said so.
 */
const ALLOWED = [
  'git show',
  'git log',
  'git ls-tree',
  'git ls-files',
  'git status',
  'git cat-file',
  'git rev-parse',
  'git diff',
  'git merge-base',
  'git for-each-ref',
  'git --version',
  'python3 -c',
  'python3 - <<',
  'python3 -m json.tool',
  'python3 tools/budget-audit.py',
  'python3 tools/font-payload.py',
  'python3 tools/subset-fonts.py inventory',
  'python3 tools/subset-fonts.py codepoints',
  // Reads artifacts/font-codepoints.json, which the codepoints block above
  // regenerates earlier in the same document order. Standalone on a clean clone
  // it reports the missing artifact instead of passing, which is the right
  // failure: it must not silently verify nothing.
  'python3 tools/subset-fonts.py verify',
  'grep',
  'cat',
  'find',
  'wc',
  'ls',
  'du',
  'sed',
  'awk',
  'cut',
  'sort',
  'uniq',
  'head',
  'tail',
  'node --version',
  'npm ls',
];

/** Fragments that veto a command even if the prefix is allow-listed. */
const VETO = [
  /(^|[^0-9&])>{1,2}\s*[^\s|&]/, // redirection to a file (but not 2>/dev/null)
  /\bmake\b/,
  /\bnpx\b/,
  /\brm\b/,
  /\bmv\b/,
  /\bcp\b/,
  /\bcurl\b/,
  /\bkill\b/,
  /\bserve\b/,
  /--port/,
  /\bpytest\b/,
  /^python3\s+tests\//, // a test suite, not an evidence command
];

const strip = (s) => s.replace(/[ \t]+$/g, '');

/**
 * A command printed with an ellipsis was not printed at all: nobody can re-run
 * `python3 -c "…network-requests…"`. Treated as a failure of the standard this
 * tool exists to enforce, not as a formatting nit — the whole point of quoting
 * the command is that it can be run.
 */
const ELIDED = /…|\.\.\./;

/**
 * A block that records a state the tree has since left — a pre-subset size list, a
 * measurement taken with a tool before that tool grew an extra section. Those
 * cannot reproduce, and the alternative to saying so is deleting the history.
 *
 * The declaration lives in an HTML comment on the line before the fence, so it is
 * invisible when the markdown is rendered but explicit in the source and always
 * printed by this tool. Declaring a block historical is a decision a reader can
 * audit; it is never silent, and it never turns a MISMATCH into a pass.
 */
const HISTORICAL = /^<!--\s*report-verify:\s*historical\s*(?:[-—:]\s*)?(.*?)\s*-->$/;

/** Pull ```-fenced blocks with their starting line number. */
function fencedBlocks(text) {
  const lines = text.split('\n');
  const blocks = [];
  let start = -1;
  let buf = [];
  let pending = null;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('```')) {
      if (start === -1) {
        start = i + 1;
        buf = [];
        pending = null;
        // Look at the nearest non-blank line above the opening fence.
        for (let j = i - 1; j >= 0; j--) {
          if (!lines[j].trim()) continue;
          const hit = HISTORICAL.exec(lines[j].trim());
          if (hit) pending = hit[1] || '(no reason given)';
          break;
        }
      } else {
        blocks.push({ line: start + 1, body: buf, historical: pending });
        start = -1;
        pending = null;
      }
      continue;
    }
    if (start !== -1) buf.push(line);
  }
  return blocks;
}

const file = process.argv[2];
if (!file) {
  console.error('usage: node tools/report-verify.mjs <markdown-file> [--all|--json]');
  process.exit(2);
}
const abs = resolve(REPO_ROOT, file);
if (!existsSync(abs)) {
  console.error(`report-verify: not found: ${abs}`);
  process.exit(2);
}

const showAll = hasFlag(process.argv, 'all');
const asJson = !!argValue(process.argv, 'json', false);
const text = readFileSync(abs, 'utf8');
const blocks = fencedBlocks(text);

const results = [];
for (const block of blocks) {
  const dollar = block.body.map((l, i) => [l, i]).filter(([l]) => l.startsWith('$ '));
  // Only the "one command, then its output" shape is mechanically checkable.
  if (dollar.length !== 1 || dollar[0][1] !== 0) continue;

  const command = block.body[0].slice(2).trim();
  const recorded = block.body.slice(1).map(strip);

  if (block.historical) {
    results.push({
      line: block.line,
      command,
      status: 'historical',
      why: block.historical,
      diffs: [],
    });
    continue;
  }

  if (ELIDED.test(command)) {
    results.push({
      line: block.line,
      command,
      status: 'ELIDED',
      why: 'the printed command contains an ellipsis, so it cannot be re-run as written',
      diffs: [],
    });
    continue;
  }

  const vetoed = VETO.find((re) => re.test(command));
  const allowed = ALLOWED.some((p) => command === p || command.startsWith(`${p} `));
  if (vetoed || !allowed) {
    results.push({
      line: block.line,
      command,
      status: 'skipped',
      why: vetoed ? `vetoed by ${vetoed}` : 'command not on the read-only allow-list',
      diffs: [],
    });
    continue;
  }

  let actual;
  let failure = null;
  try {
    actual = execFileSync('bash', ['-c', command], {
      cwd: REPO_ROOT,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 60_000,
    });
  } catch (err) {
    failure = `command failed (exit ${err.status ?? 'signal'}): ${String(err.stderr || err.message).split('\n')[0]}`;
    actual = err.stdout ?? '';
  }

  const actualLines = actual.split('\n');
  if (actualLines.length && actualLines[actualLines.length - 1] === '') actualLines.pop();
  const got = actualLines.map(strip);

  const diffs = [];
  const n = Math.max(recorded.length, got.length);
  for (let i = 0; i < n; i++) {
    const want = recorded[i];
    const have = got[i];
    if (want === have) continue;
    // Tolerate the report's deliberate elisions and hand-marked highlights.
    if (want !== undefined && (/…|\.\.\.|\(truncated\)|\*\*/.test(want))) continue;
    diffs.push({ at: i + 1, recorded: want ?? '(missing)', actual: have ?? '(missing line)' });
  }

  results.push({
    line: block.line,
    command,
    status: failure || diffs.length ? 'MISMATCH' : 'match',
    why: failure ?? undefined,
    diffs,
    recordedLines: recorded.length,
    actualLines: got.length,
  });
}

const mismatches = results.filter((r) => r.status === 'MISMATCH');
const elided = results.filter((r) => r.status === 'ELIDED');
const historical = results.filter((r) => r.status === 'historical');
const matched = results.filter((r) => r.status === 'match');
const skipped = results.filter((r) => r.status === 'skipped');

if (asJson) {
  console.log(JSON.stringify({ file, checked: results.length, matched: matched.length, mismatches: mismatches.length, elided: elided.length, historical: historical.length, skipped: skipped.length, results }, null, 2));
} else {
  console.log(`report-verify: ${file}`);
  console.log(`  blocks checked ${results.length} — match ${matched.length}, MISMATCH ${mismatches.length}, ELIDED ${elided.length}, historical ${historical.length}, skipped ${skipped.length}\n`);
  for (const r of elided) console.log(`  ELIDED    line ${r.line}: ${r.command}\n            ${r.why}\n`);
  // Always printed, even without --all: a declared-historical block is a claim
  // about the report that a reader should see, not a detail behind a flag.
  for (const r of historical) console.log(`  historical line ${r.line}: ${r.command}\n            declared reason: ${r.why}\n`);
  for (const r of mismatches) {
    console.log(`  MISMATCH  line ${r.line}: ${r.command}`);
    if (r.why) console.log(`            ${r.why}`);
    for (const d of r.diffs.slice(0, 40)) {
      console.log(`            line ${d.at}  recorded: ${JSON.stringify(d.recorded)}`);
      console.log(`            ${' '.repeat(String(d.at).length)}        actual:   ${JSON.stringify(d.actual)}`);
    }
    if (r.diffs.length > 40) console.log(`            … ${r.diffs.length - 40} more differing lines`);
    console.log('');
  }
  if (showAll) {
    for (const r of matched) console.log(`  match     line ${r.line}: ${r.command}`);
    console.log('');
  }
  for (const r of skipped) if (showAll) console.log(`  skipped   line ${r.line}: ${r.command}  [${r.why}]`);
  if (showAll) console.log('');
}

process.exit(mismatches.length || elided.length ? 1 : 0);
