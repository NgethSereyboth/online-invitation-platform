from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from ai_agent.capabilities import TOOL_BINDINGS
from ai_agent.jit_elevation import AUTO_APPROVED_TOOLS, JIT_ELIGIBLE_TOOLS
from ai_agent.tools import TOOLS
from scripts.generate_attack_stories import THREATS, story_text

ROOT = Path(__file__).resolve().parents[1]
STORIES = ROOT / "docs" / "ai" / "attack-stories"
INDEX = STORIES / "README.md"
REQUIRED_SECTIONS = (
    "What it touches",
    "Worst case if malicious",
    "Containment",
    "Reversible",
    "Test coverage",
    "AISVS cross-reference",
)


def _field(content: str, name: str) -> str:
    match = re.search(
        rf"(?m)^\| \*\*{re.escape(name)}\*\* \| (.*?) \|$",
        content,
    )
    assert match, f"Missing `{name}` metadata field"
    return match.group(1)


def test_every_registered_tool_has_a_full_attack_story():
    """All registered tool IDs must have an individual threat-model document."""
    story_ids = {
        path.stem
        for path in STORIES.glob("*.md")
        if path.name not in {"README.md", "_TEMPLATE.md"}
    }
    assert set(TOOLS) == story_ids, {
        "missing": sorted(set(TOOLS) - story_ids),
        "unregistered": sorted(story_ids - set(TOOLS)),
    }


def test_attack_story_metadata_and_sections_match_registry():
    """Every story identifies the real tool policy and includes its threat model."""
    for tool_id, tool in TOOLS.items():
        path = STORIES / f"{tool_id}.md"
        content = path.read_text(encoding="utf-8")
        binding = TOOL_BINDINGS[tool_id]
        assert content == story_text(tool_id), path
        assert f"# Attack Story: `{tool_id}`" in content, path
        assert _field(content, "Tool ID") == f"`{tool_id}`", path
        assert f"`{tool.risk}`" in _field(content, "Risk tier"), path
        assert f"`{tool.permission}`" in _field(content, "Permission tier"), path
        assert _field(content, "Executor") == f"`{tool.executor}`", path
        assert binding["binding"] in _field(content, "Binding"), path
        assert binding["type"] in _field(content, "Binding"), path
        assert str(tool.reversible) in _field(content, "Reversible"), path
        assert str(tool.confirmation) in _field(content, "Confirmation required"), path
        headings = set(re.findall(r"(?m)^### \d+\. (.+)$", content))
        for section in REQUIRED_SECTIONS:
            assert section in headings, (path, section)
        assert "<tool_id>" not in content, path


def test_each_tool_has_a_reviewed_scenario_and_generated_story():
    assert set(TOOL_BINDINGS) == set(TOOLS)
    assert set(THREATS) == set(TOOLS)
    for tool_id, (touches, worst_case) in THREATS.items():
        assert len(touches) >= 30, tool_id
        assert len(worst_case) >= 80, tool_id
        assert worst_case != "a malicious action", tool_id
        content = (STORIES / f"{tool_id}.md").read_text(encoding="utf-8")
        assert touches in content, tool_id
        assert worst_case in content, tool_id
        if tool_id in JIT_ELIGIBLE_TOOLS:
            assert "JIT elevation" in content, tool_id
        else:
            assert "not in `JIT_ELIGIBLE_TOOLS`" in content, tool_id
        if tool_id in AUTO_APPROVED_TOOLS:
            assert "auto-approved by current policy" in content, tool_id


def test_attack_story_index_reports_complete_individual_coverage():
    content = INDEX.read_text(encoding="utf-8")
    assert "80 registered tools; 80 full per-tool stories; zero index-only entries" in content
    assert "| Individually documented registered tools | 80 |" in content
    assert "| Index-only or missing story entries | 0 |" in content
    for tool_id, tool in TOOLS.items():
        assert f"[`{tool_id}.md`]({tool_id}.md)" in content, tool_id
        assert f"| `{tool_id}` | {tool.risk} | {tool.permission} |" in content, tool_id


def test_attack_story_generator_check_mode_detects_stale_output():
    result = subprocess.run(
        [sys.executable, "scripts/generate_attack_stories.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VERIFIED 80 attack stories" in result.stdout
