"""Canvas motion contracts; no browser or new runtime dependency required."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_built_editor_suite_contains_motion_core():
    suite = (ROOT / 'src/js/editor-suite.js').read_text(encoding='utf-8')
    for symbol in ('createFrameBatcher', 'EInviteMotion', 'TWEEN_MAX_MS',
                   'WHEEL_REARM_MS', 'WHEEL_SETTLE_MS', 'ZOOM_COMMIT_MS',
                   'FLICK_LOCK_MS', 'LONG_PRESS_MS', 'TRANSITION_MAX_MS'):
        assert symbol in suite, f'Missing motion contract in built suite: {symbol}'


def test_batcher_merges_flushes_and_cancels_stale_frames():
    # Load the real source with a minimal DOM: the shared core must initialize
    # before the editor-only guard. Queued callbacks model a hidden/throttled tab.
    script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let serial = 0;
const queue = new Map(), listeners = new Map(), commits = [];
const sandbox = {
  window: {}, document: {
    querySelector: () => null,
    addEventListener: (name, fn) => listeners.set(name, fn)
  },
  requestAnimationFrame: fn => { queue.set(++serial, fn); return serial; },
  cancelAnimationFrame: id => queue.delete(id),
  setTimeout, clearTimeout
};
vm.runInNewContext(fs.readFileSync('src/js/editor-pro.js', 'utf8'), sandbox);
const motion = sandbox.window.EInviteMotion;
assert.ok(motion, 'Motion core must exist before editor DOM initialization');
const b = motion.createFrameBatcher(
  (a, b) => ({ delta: a.delta + b.delta, center: b.center }),
  value => commits.push(value)
);
for (let i = 0; i < 30; i++) b.accumulate({delta: 1, center: i});
assert.equal(queue.size, 1);
assert.equal(commits.length, 0);
const tick = () => { const jobs = [...queue.values()]; queue.clear(); jobs.forEach(fn => fn()); };
tick();
assert.equal(commits.length, 1);
assert.equal(commits[0].delta, 30);
assert.equal(commits[0].center, 29);
b.accumulate({delta: 2, center: 30});
b.flush();
assert.equal(queue.size, 0, 'flush must cancel its old frame');
b.accumulate({delta: 3, center: 31});
tick();
assert.equal(commits.length, 3);
assert.equal(commits[2].delta, 3);
b.accumulate({delta: 4, center: 32});
listeners.get('visibilitychange')();
assert.equal(commits.at(-1).delta, 4, 'visibility change must flush pending input');
assert.equal(queue.size, 0);
b.destroy();
b.accumulate({delta: 99, center: 33});
tick();
assert.equal(commits.length, 4, 'destroyed batcher must not commit');
assert.equal(motion.MOTION.TWEEN_MAX_MS, 150);
assert.equal(motion.MOTION.WHEEL_REARM_MS, 80);
assert.equal(motion.MOTION.WHEEL_SETTLE_MS, 140);
assert.equal(motion.MOTION.ZOOM_COMMIT_MS, 200);
assert.equal(motion.MOTION.FLICK_LOCK_MS, 250);
assert.equal(motion.MOTION.LONG_PRESS_MS, 251);
assert.equal(motion.MOTION.TRANSITION_MAX_MS, 400);
"""
    result = subprocess.run(['node', '-e', script], cwd=ROOT,
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
