from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def test_readme_quickstart_commands_and_screenshot_paths_exist():
    """Commands and screenshot targets documented in README must resolve."""
    content = README.read_text(encoding="utf-8")
    assert "python3 src/python/prepare_production_env.py" not in content
    assert "python3 src/python/build/prepare_production_env.py" in content

    screenshot_paths = re.findall(r"`(docs/screenshots/[^`]+\.png)`", content)
    assert screenshot_paths, "Expected README screenshot placeholders with workspace paths"
    assert all(not (ROOT / path).exists() for path in screenshot_paths), (
        "Remove the screenshot placeholder warning once screenshot assets are committed"
    )
    assert "Screenshots coming soon" in content
