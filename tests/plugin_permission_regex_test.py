#!/usr/bin/env python3
"""Regression checks for the plugin sandbox permission matcher.

The matcher accepts exact grants and colon-boundary wildcards. These cases
prove that the wildcard is anchored and cannot be widened by prefix/suffix
confusion, case differences, or a colon inside the resource segment.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

JS = r"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('src/js/plugin_sandbox_host.js', 'utf8');
const ctx = {
  window: {},
  navigator: {},
  performance: {},
  document: {},
  fetch: function () {},
  MessageChannel: function () {},
};
vm.createContext(ctx);
vm.runInContext(source, ctx);
const isGranted = ctx.window.EInvitePluginSandboxHost.isGranted;
const cases = [
  {name: 'exact match', requested: 'invitation:read', approved: ['invitation:read'], want: true},
  {name: 'wildcard match', requested: 'invitation:123:read', approved: ['invitation:*:read'], want: true},
  {name: 'wrong action', requested: 'invitation:123:write', approved: ['invitation:*:read'], want: false},
  {name: 'prefix confusion', requested: 'xinvitation:123:read', approved: ['invitation:*:read'], want: false},
  {name: 'suffix confusion', requested: 'invitation:123:readx', approved: ['invitation:*:read'], want: false},
  {name: 'extra colon', requested: 'invitation:123:extra:read', approved: ['invitation:*:read'], want: false},
  {name: 'case sensitive', requested: 'Invitation:123:read', approved: ['invitation:*:read'], want: false},
  {name: 'empty approval', requested: 'invitation:read', approved: [], want: false},
  {name: 'non-array approval', requested: 'invitation:read', approved: null, want: false},
];
const out = cases.map(function (c) {
  return {name: c.name, got: isGranted(c.requested, c.approved), want: c.want};
});
console.log(JSON.stringify(out));
"""


def main() -> int:
    completed = subprocess.run(
        ["node", "-e", JS],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    results = json.loads(completed.stdout)
    failures = [row for row in results if row["got"] != row["want"]]
    for row in results:
        print(f"[{'OK' if row['got'] == row['want'] else 'FAIL'}] {row['name']}: {row['got']}")
    if failures:
        print(f"FAIL: {len(failures)} permission matcher case(s) failed")
        return 1
    print("PLUGIN_PERMISSION_MATCHER_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
