from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_HISTORY = ROOT / "VERSION_HISTORY.md"


def test_legacy_version_history_link_exists():
    """The legacy-history link must point to the real file from repo root."""
    content = VERSION_HISTORY.read_text(encoding="utf-8")
    match = re.search(
        r"\[`docs/LEGACY-VERSION-HISTORY\.md`\]\(([^)]+)\)",
        content,
    )

    assert match, "Expected a Markdown link to docs/LEGACY-VERSION-HISTORY.md"
    target = (VERSION_HISTORY.parent / match.group(1)).resolve()
    assert target.is_file(), f"Legacy version history link is broken: {target}"
