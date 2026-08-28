from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def main() -> int:
    direct = read("direct-manipulation-v24.js")
    inline_body = direct.split("function startInline", 1)[1].split("function finishInline", 1)[0]
    install_body = direct.split("function install", 1)[1].split("function destroy", 1)[0]
    assert "on(document,'dblclick',onDoubleClick,true)" in install_body
    assert "content.setAttribute('contenteditable','true')" in inline_body
    assert "ensureToolbar" not in inline_body
    assert "ensureToolbar" not in install_body
    assert "function ensureToolbar" not in direct
    assert "function positionToolbar" not in direct
    assert "function breadcrumbFor" not in direct
    assert "let toolbar=" not in direct
    assert "if(toolbar)" not in direct
    assert "toolbar?.remove()" not in direct

    editor = read("editor-pro.js")
    assert "ei-rich-toolbar" not in editor
    assert 'data-action="editText"' not in editor

    typography = read("typography-editor-v20.js")
    assert "v20ToolbarToggle" in typography
    assert "einvite-typography-toolbar-collapsed" in typography
    assert "setCollapsed(localStorage.getItem('einvite-typography-toolbar-collapsed')==='1')" in typography

    workflow = read("workflow-creation-flow-v4.js")
    assert "function placePopover" in workflow
    assert "menu.classList.add('open');menu.style.visibility='hidden'" in workflow
    assert "placePopover(menu,button,{placement:'above'})" in workflow
    assert "actionButton('Edit text','edit-text'" not in workflow
    assert "workflowQuickStrip" not in workflow

    modern = read("modern-ui.js")
    assert 'data-mode="system"' not in modern
    assert "const modes=['light','dark']" in modern
    assert "currentMode(){return localStorage.getItem('einvite-theme-mode')==='dark'?'dark':'light'}" in modern

    account = read("account.js")
    assert "installAppearanceSetting" in account
    assert 'data-account-theme="light"' in account
    assert 'data-account-theme="dark"' in account

    studio = read("studio-experience.js")
    assert 'class="studio-nav-label"' in studio
    assert "studio-canvas-hint" not in studio

    editor_css = read("editor-ux-refinement-v0_52.css")
    for selector in (".v24-inline-toolbar", ".ei-rich-toolbar", "#workflowQuickStrip", ".studio-nav-label"):
        assert selector in editor_css
    compact_css = read("compact-theme-v0_52.css")
    assert "width: 124px" in compact_css
    assert ".account-appearance-actions" in compact_css

    routes = json.loads(read("route-bundle-sources-v15.json"))["pages"]
    modern_pages = [page for page, spec in routes.items() if "modern-ui.css" in spec["styles"]]
    assert modern_pages
    assert all("compact-theme-v0_52.css" in routes[page]["styles"] for page in modern_pages)
    assert "editor-ux-refinement-v0_52.css" in routes["index.html"]["styles"]

    print("V0_52_EDITOR_INTERACTION_REFINEMENT_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
