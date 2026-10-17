from __future__ import annotations

from pathlib import Path

from ai_agent.capabilities import TOOL_REQUIRED_GRANTS
from ai_agent.jit_elevation import JIT_ELIGIBLE_TOOLS
from ai_agent.tools import TOOLS

ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = ROOT / "docs" / "ARCHITECTURE.md"


def _section(content: str, heading: str, next_heading: str) -> str:
    start = content.index(heading)
    end = content.index(next_heading, start)
    return content[start:end]


def test_architecture_describes_current_ai_authorization_rollout():
    """Architecture claims must match the implemented staged authorization model."""
    content = ARCHITECTURE.read_text(encoding="utf-8")
    registry = _section(content, "### 3.3 AI Agent", "### 3.4 AI Provider")
    future = _section(content, "## 9. Future Direction", "*Phase 0.2")

    assert f"**{len(TOOLS)} typed `ToolDefinition` entries**" in registry
    assert (
        f"**{len(TOOL_REQUIRED_GRANTS)} of the {len(TOOLS)} tools currently have "
        "resource-scoped grant mappings**"
    ) in registry
    assert "unmapped tools continue to use the legacy tier check" in registry
    assert f"{len(JIT_ELIGIBLE_TOOLS)} high-risk tools" in registry
    assert "JIT elevation is implemented" in registry
    assert "will replace these with resource-scoped grants" not in registry
    assert "Complete the staged resource-scoped permission rollout" in future
    assert "JIT elevation is implemented" not in future
