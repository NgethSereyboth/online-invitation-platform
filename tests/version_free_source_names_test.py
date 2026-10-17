"""Source files under ``src/js`` and ``src/css`` must not carry version-shaped names.

Why this exists
---------------
The version-label removal plan
(``docs/superpowers/plans/2026-10-15-eliminate-version-labeling.md``) removes
version suffixes from hand-authored module and stylesheet file names. That work
is staged and slow, so without a guard the tree would keep growing new
``something-v56.js`` files while the old ones were being renamed -- the backlog
would never actually close.

This module is the ratchet. ``tests/versioned_name_allowlist.json`` lists the
files that still carry a version-shaped name; the list only ever shrinks as
Stages 1-3 rename them. Two properties:

  * a file under ``src/js``/``src/css`` with a version-shaped name that is not
    listed fails -- no new version suffix may be introduced;
  * an allowlist entry that no longer exists on disk fails -- a rename must
    remove its entry in the same change, so the list cannot rot or silently
    stop covering a file that came back.

``src/html`` is not scanned: no HTML page ever carried a version-shaped name,
and page names are route contract, not module naming.

Stage 4 empties the allowlist file and deletes it. The tests then run with an
empty allowlist and enforce a permanent zero-suffix rule, which is why the
file's absence is treated as "no exemptions" rather than an error.

Deliberately NOT covered: version *identifiers* that are semantic contracts --
DB columns such as ``token_version``, ``schemaVersion``/``modelVersion``,
migration numbers, the plugin manifest ``version`` field, protocol route
segments (``/api/platform/v32/``), and the numeric ``version:`` properties on
frozen JS module exports. The plan excludes those, and this guard only looks at
file names, so it cannot accidentally drive a change to any of them.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = Path(__file__).resolve().parent / "versioned_name_allowlist.json"
SCANNED_ROOTS = (REPO_ROOT / "src" / "js", REPO_ROOT / "src" / "css")

# `foo-v15.js`, `foo-v0_52.js` (underscore form used by compact-theme), `foo-v24.4.js`.
VERSIONED_NAME = re.compile(r"-v\d+(?:[._]\d+)?\.(?:js|css)$", re.IGNORECASE)


def _allowlisted() -> set[str]:
    """Load the shrinking allowlist; a missing file means 'no exemptions left'."""
    if not ALLOWLIST.is_file():
        return set()
    payload = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    return set(payload["files"])


def _actual() -> set[str]:
    """Every version-shaped source file name currently on disk."""
    found: set[str] = set()
    for root in SCANNED_ROOTS:
        for path in root.rglob("*"):
            if path.is_file() and VERSIONED_NAME.search(path.name):
                found.add(path.relative_to(REPO_ROOT).as_posix())
    return found


def test_guard_pattern_recognises_version_suffixes() -> None:
    """The pattern must actually match, or both ratchet tests pass vacuously."""
    assert VERSIONED_NAME.search("command-palette-v23.js")
    assert VERSIONED_NAME.search("yjs-bridge-v54.js")
    assert VERSIONED_NAME.search("compact-theme-v0_52.css")
    assert VERSIONED_NAME.search("scene-model-v22.css")
    # Names that must NOT be treated as versioned.
    assert not VERSIONED_NAME.search("app-shell.js")
    assert not VERSIONED_NAME.search("i18n.js")
    assert not VERSIONED_NAME.search("editor-core.js")
    assert not VERSIONED_NAME.search("vault.js")


def test_no_new_versioned_source_names() -> None:
    """No file may be added under src/js or src/css with a version-shaped name."""
    unexpected = sorted(_actual() - _allowlisted())
    assert not unexpected, (
        "new version-shaped source file name(s) under src/js or src/css:\n  "
        + "\n  ".join(unexpected)
        + "\n\nName the module without a version suffix. If a version suffix is a "
        "genuine compatibility contract, it belongs in the data, not the file name. "
        "See tests/versioned_name_allowlist.json for the backlog being burned down."
    )


def test_allowlist_has_no_stale_entries() -> None:
    """A rename must drop its allowlist entry, so the list tracks the real backlog."""
    stale = sorted(_allowlisted() - _actual())
    assert not stale, (
        "allowlist entries no longer on disk (remove them when you rename a file):\n  "
        + "\n  ".join(stale)
    )


@pytest.mark.parametrize("root", [p.name for p in SCANNED_ROOTS])
def test_scanned_root_exists(root: str) -> None:
    """A renamed or moved source root must fail loudly, not scan nothing."""
    assert (REPO_ROOT / "src" / root).is_dir()
