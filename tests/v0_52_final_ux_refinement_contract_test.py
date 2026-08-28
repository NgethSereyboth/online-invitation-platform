#!/usr/bin/env python3
"""Static release contracts for the final editor and account UX refinement."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

workspace = (ROOT / "workspace-experience-v24.js").read_text(encoding="utf-8")
styles = (ROOT / "workspace-experience-v24.css").read_text(encoding="utf-8")
canvas_styles = (ROOT / "canvas-plus.css").read_text(encoding="utf-8")
loader = (ROOT / "performance-loader-v22.js").read_text(encoding="utf-8")

for token in (
    "v24-inspector-empty",
    "organizeHeader",
    "organizeFooter",
    "v24-footer-tools-menu",
    "contextButtons(){const bar",
    "!node.classList.contains('v24-context-menu')",
    "target?.closest?.('.v24-context-menu')",
    "controller.fit()",
):
    assert token in workspace, token

for token in (
    "height:58px!important",
    "grid-template-columns:repeat(5,minmax(0,1fr))",
    "not(.v24-has-selection)",
    "v24-footer-tools-menu",
    "einvite-layout-mobile aside.left",
    "display:none!important",
):
    assert token in styles, token

assert "workspace-experience-v24.js?ux=final6" in loader
assert "workspace-experience-v24.css?ux=final6" in workspace
assert "body[data-page=\"account\"] .account-grid>.account-card:nth-child(3)" in canvas_styles
assert "grid-column:1!important" in canvas_styles

editor_bytes = (ROOT / "bundle-index-v15.js").stat().st_size + (ROOT / "bundle-index-v15.css").stat().st_size
assert editor_bytes <= 1_420_000, editor_bytes

print("V0_52_FINAL_UX_REFINEMENT_CONTRACT_TEST_PASSED")
