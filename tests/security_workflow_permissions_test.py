"""CI security and performance workflows must not grant write-all tokens."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_workflows_declare_contents_read_permission():
    for name in ("security.yml", "lighthouse.yml"):
        text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "permissions:\n  contents: read" in text, name
