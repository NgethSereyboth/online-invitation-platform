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
 *   node tools/report-verify.mjs <file> --with-server --timeout=420
 *
 * Coverage, and what each non-match means
 * ---------------------------------------
 * A block that this tool reports as `skipped` is a hole: the report claims an
 * output that nothing re-derives. The previous pass left 9 of 19 blocks skipped.
 * Two changes closed most of that without weakening anything:
 *
 *   > continuations   A multi-line command printed the way a shell echoes it (`$`
 *                     on the first line, `>` on the rest) used to be read as one
 *                     command line followed by *output*, so a two-line `for` loop
 *                     could never be checked. The `> ` lines are now reassembled
 *                     into the command.
 *   --with-server     Starts tools/serve-gzip.py, then allows the blocks whose only
 *                     obstacle was a missing server. Deterministic output only:
 *                     the hover audit is byte-stable (305/305 identical rows across
 *                     two runs), while anything printing milliseconds or a
 *                     Lighthouse score is not, and is declared instead.
 *
 * Four declarations replace the rest, each printed with its reason and none of them
 * counted as a match:
 *
 *   <!-- report-verify: historical REASON -->       records a state the tree left
 *   <!-- report-verify: write REASON -->            mutates; not a read-only command
 *   <!-- report-verify: measurement REASON -->      one run's numbers; not reproducible
 *   <!-- report-verify: prefix N REASON -->         the first N lines are compared;
 *                                                   the tail is environment-dependent
 *
 * `prefix` exists so a block whose *tail* is environment-dependent still has its
 * substantive claims under test rather than being retired wholesale.
 *
 * Exit status: 0 when no block mismatched, 1 when at least one did, 2 on bad input.
 */
import { readFileSync, existsSync } from 'node:fs';
import { execFileSync, spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { PORT, REPO_ROOT, argValue, hasFlag } from './lib/repo.mjs';

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
  // Read-only with --check: it verifies every generated artifact and writes nothing.
  'python3 build.py all --check',
  'python3 tools/budget-audit.py',
  // Proves a CSS edit is exactly its !important removals, and that the manifests'
  // size/digest fields still describe the files on disk. Read-only: git show + stat.
  'python3 tools/important-removal-audit.py',
  // Compares two recorded hover sweeps row by row. Read-only, but it needs two
  // artifact snapshots, which is why the blocks using it carry a declaration.
  'python3 tools/hover-regression-diff.py',
  // Recomputes the versioned-rename surface from the tracked corpus.
  'python3 tools/versioned-rename-surface.py',
  'git check-ignore',
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
  // A read-only `for` loop over tool names. Allow-listed by its exact first line,
  // for the same reason as every other entry: this tool executes text lifted out of
  // a document, so "the loop looks read-only" is not a criterion — the command is.
  'for f in dom-timeline layout-thrash-probe style-recalc-attribution lhci-single; do',
];

/**
 * Read-only commands that need the gzip server on 127.0.0.1:PORT. Allowed only
 * with --with-server, because without one they exit 2 and would be reported as a
 * mismatch caused by the harness rather than by the report.
 */
const SERVER_ALLOWED = [
  'python3 tools/hover-verify.py --all --summary-only',
  'python3 tools/hover-verify.py --all --lift --summary-only',
  'python3 tools/hover-verify.py --cross-page',
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
/**
 * A block that only *starts* reproducibly.
 *
 * `python3 tools/subset-fonts.py codepoints --build-output-only` prints the used
 * codepoints and then a list of the sources it scanned that have no tracked
 * counterpart — a list that changes whenever a scratch file is added to or removed
 * from the tree. Its head is a real, stable claim about the shipped character set;
 * its tail is a description of the working directory. `prefix N` keeps the head
 * under test and declares the tail, instead of retiring a block whose first 21 lines
 * are exactly what the font-subsetting evidence rests on.
 */
const PREFIX = /^<!--\s*report-verify:\s*prefix\s+(\d+)\s*(?:[-—:]\s*)?(.*?)\s*-->$/;
/** Records a state the tree has left behind. */
const HISTORICAL = /^<!--\s*report-verify:\s*historical\s*(?:[-—:]\s*)?(.*?)\s*-->$/;
/** Not a read-only command: it builds, serves, or writes. Declared, never run. */
const WRITE = /^<!--\s*report-verify:\s*write\s*(?:[-—:]\s*)?(.*?)\s*-->$/;
/**
 * Non-deterministic by construction: the command prints a measurement. Re-running
 * it produces different milliseconds, a different score, or a different timestamp,
 * so byte comparison can never hold and pretending otherwise would only produce a
 * permanently red gate that people learn to ignore.
 */
const MEASUREMENT = /^<!--\s*report-verify:\s*measurement\s*(?:[-—:]\s*)?(.*?)\s*-->$/;
/**
 * Read-only but not appropriate for this tool to run: it installs nothing, writes
 * nothing, yet runs a 252-module test suite or a 250-module import probe for
 * minutes, and in some cases starts a server of its own. The declaration is not a
 * licence to skip the number — the block is still printed with its reason, and the
 * command is one a reader can run.
 */
const HEAVY = /^<!--\s*report-verify:\s*heavy\s*(?:[-—:]\s*)?(.*?)\s*-->$/;

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
          const text = lines[j].trim();
          const hit = PREFIX.exec(text);
          if (hit) {
            pending = { kind: 'prefix', prefix: Number(hit[1]), why: hit[2] || '(no reason given)' };
            break;
          }
          for (const [re, kind] of [[HISTORICAL, 'historical'], [WRITE, 'write'], [MEASUREMENT, 'measurement'], [HEAVY, 'heavy']]) {
            const m = re.exec(text);
            if (m) { pending = { kind, why: m[1] || '(no reason given)' }; break; }
          }
          break;
        }
      } else {
        blocks.push({ line: start + 1, body: buf, pending });
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
const withServer = hasFlag(process.argv, 'with-server');
const argTimeout = argValue(process.argv, 'timeout', false);
const TIMEOUT_MS = (argTimeout ? Number(argTimeout) : 60) * 1000;
const text = readFileSync(abs, 'utf8');
const blocks = fencedBlocks(text);

/**
 * --with-server: start the gzip server this repo measures against, so the blocks
 * whose only obstacle was a missing server are verified instead of skipped.
 *
 * The server is this script's child and is killed on exit and on a signal. If it
 * cannot be started, `serverUp` stays false, the server-dependent blocks remain
 * `skipped` with that reason printed, and nothing is reported as a mismatch caused
 * by the harness.
 */
let serverProc = null;
let serverUp = false;
function stopServer() {
  if (serverProc && serverProc.exitCode === null && !serverProc.killed) {
    try { serverProc.kill('SIGTERM'); } catch { /* already gone */ }
  }
  serverProc = null;
}
if (withServer) {
  // `{PORT}` here is a Python f-string field, so it must be interpolated by the JS
  // template literal — `${PORT}`. Written `{PORT}` it reaches Python verbatim and
  // raises NameError, which the readiness probe cannot tell apart from "not up yet":
  // the flag silently did nothing and the server-dependent blocks stayed skipped.
  const probe =
    'import sys,urllib.request\n' +
    'try:\n' +
    `    urllib.request.urlopen("http://127.0.0.1:${PORT}/index.html",timeout=2)\n` +
    '    sys.exit(0)\n' +
    'except Exception:\n' +
    '    sys.exit(1)\n';
  const answering = () => {
    try {
      execFileSync('python3', ['-c', probe], { stdio: 'ignore', timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  };
  if (answering()) {
    // An already-running server on this port is reused, not duplicated: a second
    // bind would fail and leave an unread stderr pipe behind.
    serverUp = true;
  } else {
    serverProc = spawn('python3', ['tools/serve-gzip.py', '--port', String(PORT)], {
      cwd: REPO_ROOT, stdio: ['ignore', 'pipe', 'pipe'],
    });
    serverProc.on('error', () => { serverProc = null; });
    for (let i = 0; i < 60 && serverProc && !serverUp; i++) {
      if (answering()) { serverUp = true; break; }
      execFileSync('sleep', ['0.5']);
    }
    process.on('exit', stopServer);
    for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => { stopServer(); process.exit(130); });
  }
}

const results = [];
for (const block of blocks) {
  const dollar = block.body.map((l, i) => [l, i]).filter(([l]) => l.startsWith('$ '));
  // Only the "one command, then its output" shape is mechanically checkable.
  if (dollar.length !== 1 || dollar[0][1] !== 0) continue;

  // A shell-echoed multi-line command continues on `> ` lines. Reading those as
  // output is what made the two-line `for` loop in §1.2 impossible to verify.
  let lastCommandLine = 0;
  for (let i = 1; i < block.body.length; i++) {
    if (!block.body[i].startsWith('> ')) break;
    lastCommandLine = i;
  }
  const command = [block.body[0].slice(2), ...block.body.slice(1, lastCommandLine + 1).map((l) => l.slice(2))]
    .join('\n')
    .trim();
  const recorded = block.body.slice(lastCommandLine + 1).map(strip);

  const declared = block.pending;
  if (declared && declared.kind !== 'prefix') {
    // historical / write / measurement: `status` carries the declaration kind, so
    // each is counted and printed under its own name rather than as a hole.
    results.push({
      line: block.line,
      command,
      status: declared.kind,
      why: declared.why,
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
  const firstLine = command.split('\n')[0];
  const allowed =
    ALLOWED.some((p) => firstLine === p || firstLine.startsWith(`${p} `)) ||
    (serverUp && SERVER_ALLOWED.some((p) => firstLine === p || firstLine.startsWith(`${p} `)));
  if (vetoed || !allowed) {
    // Naming the obstacle is the point: `skipped` must be a decision a reader can
    // see, and the two obstacles have different remedies.
    let why;
    if (vetoed) why = `vetoed by ${vetoed}`;
    else if (SERVER_ALLOWED.some((p) => firstLine === p || firstLine.startsWith(`${p} `)))
      why = serverUp
        ? 'server-dependent command that is not on the read-only allow-list'
        : 'needs the gzip server; re-run with --with-server to verify it';
    else why = 'command not on the read-only allow-list';
    results.push({ line: block.line, command, status: 'skipped', why, diffs: [] });
    continue;
  }

  let actual;
  let failure = null;
  try {
    actual = execFileSync('bash', ['-c', command], {
      cwd: REPO_ROOT,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: TIMEOUT_MS,
    });
  } catch (err) {
    failure = `command failed (exit ${err.status ?? 'signal'}): ${String(err.stderr || err.message).split('\n')[0]}`;
    actual = err.stdout ?? '';
  }

  const actualLines = actual.split('\n');
  if (actualLines.length && actualLines[actualLines.length - 1] === '') actualLines.pop();
  const got = actualLines.map(strip);

  // `prefix N`: compare the first N lines only. The tail is declared, not ignored —
  // it is printed by this tool so a reader can see what was exempted and why.
  const declaredPrefix = declared && declared.kind === 'prefix' ? declared.prefix : null;
  const wantLines = declaredPrefix ? recorded.slice(0, declaredPrefix) : recorded;
  const haveLines = declaredPrefix ? got.slice(0, declaredPrefix) : got;
  if (declaredPrefix && got.length < declaredPrefix) {
    wantLines.push(...recorded.slice(got.length).map(() => '(missing line)'));
  }

  const diffs = [];
  const n = Math.max(wantLines.length, haveLines.length);
  for (let i = 0; i < n; i++) {
    const want = wantLines[i];
    const have = haveLines[i];
    if (want === have) continue;
    // Tolerate the report's deliberate elisions and hand-marked highlights.
    if (want !== undefined && (/…|\.\.\.|\(truncated\)|\*\*/.test(want))) continue;
    diffs.push({ at: i + 1, recorded: want ?? '(missing)', actual: have ?? '(missing line)' });
  }

  results.push({
    line: block.line,
    command,
    status: failure || diffs.length ? 'MISMATCH' : 'match',
    why: declaredPrefix
      ? `compared the first ${declaredPrefix} line(s); declared tail: ${declared.why}`
      : failure ?? undefined,
    diffs,
    declaredPrefix,
    recordedLines: recorded.length,
    comparedLines: wantLines.length,
    actualLines: got.length,
  });
}

const mismatches = results.filter((r) => r.status === 'MISMATCH');
const elided = results.filter((r) => r.status === 'ELIDED');
const historical = results.filter((r) => r.status === 'historical');
const writes = results.filter((r) => r.status === 'write');
const measurements = results.filter((r) => r.status === 'measurement');
const heavy = results.filter((r) => r.status === 'heavy');
const matched = results.filter((r) => r.status === 'match');
const skipped = results.filter((r) => r.status === 'skipped');
const partiallyCompared = matched.filter((r) => r.declaredPrefix);

if (asJson) {
  console.log(JSON.stringify({
    file, checked: results.length, matched: matched.length, mismatches: mismatches.length,
    elided: elided.length, historical: historical.length, write: writes.length,
    measurement: measurements.length, heavy: heavy.length, skipped: skipped.length,
    comparedLines: matched.reduce((n, r) => n + (r.comparedLines ?? r.recordedLines ?? 0), 0),
    partialMatches: partiallyCompared.length, serverUp, results,
  }, null, 2));
} else {
  console.log(`report-verify: ${file}`);
  console.log(`  blocks checked ${results.length} — match ${matched.length}, MISMATCH ${mismatches.length}, ELIDED ${elided.length}\n`);
  console.log(`  declared, not compared  historical ${historical.length}, write ${writes.length}, measurement ${measurements.length}, heavy ${heavy.length}`);
  console.log(`  still skipped ${skipped.length}${withServer ? '' : '   (pass --with-server to verify the server-dependent ones)'}`);
  if (partiallyCompared.length) console.log(`  partially compared (declared tail) ${partiallyCompared.length}`);
  console.log('');
  for (const r of elided) console.log(`  ELIDED    line ${r.line}: ${r.command}\n            ${r.why}\n`);
  // Always printed, even without --all: every declaration is a claim about the
  // report that a reader should be able to audit, not a detail behind a flag.
  for (const r of historical) console.log(`  historical line ${r.line}: ${r.command}\n            declared reason: ${r.why}\n`);
  for (const r of writes) console.log(`  write      line ${r.line}: ${r.command}\n            declared reason: ${r.why}\n`);
  for (const r of measurements) console.log(`  measurement line ${r.line}: ${r.command}\n            declared reason: ${r.why}\n`);
  for (const r of heavy) console.log(`  heavy      line ${r.line}: ${r.command}\n            declared reason: ${r.why}\n`);
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
    for (const r of matched) {
      const partial = r.declaredPrefix ? `  [first ${r.declaredPrefix}/${r.recordedLines} lines]` : '';
      console.log(`  match     line ${r.line}: ${r.command.split('\n')[0]}${partial}`);
    }
    console.log('');
  }
  for (const r of skipped) {
    const oneLine = r.command.split('\n')[0];
    if (showAll) console.log(`  skipped   line ${r.line}: ${oneLine}  [${r.why}]`);
  }
  if (skipped.length) {
    // `skipped` is only actionable if the obstacles are separable: one of these is
    // fixed by a flag, the other by an allow-list entry.
    const byReason = new Map();
    for (const r of skipped) byReason.set(r.why, (byReason.get(r.why) || 0) + 1);
    console.log('  skipped by reason:');
    for (const [why, count] of [...byReason].sort((a, b) => b[1] - a[1])) console.log(`    ${count}  ${why}`);
    console.log('');
  }
  if (showAll) console.log('');
}

process.exit(mismatches.length || elided.length ? 1 : 0);
