#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

from browser_runtime import launch_chromium, skipped, wait_for_reachable_control

ROOT = Path(__file__).resolve().parents[1]


def build() -> str:
    spec = importlib.util.spec_from_file_location('inline_editor', ROOT / 'tests' / 'inline_editor_runtime_test.py')
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.build_inline_editor()


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return skipped('V22_2_PAGE_EXPERIENCE', exc)

    with sync_playwright() as p:
        try:
            browser = launch_chromium(p)
        except Exception as exc:
            return skipped('V22_2_PAGE_EXPERIENCE', exc)
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.set_default_timeout(60_000)
            errors: list[str] = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
            page.set_content(build(), wait_until='load')
            page.wait_for_timeout(1300)
            if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():
                page.locator('#finalTourDismiss').click()
                page.wait_for_timeout(100)

            page.add_style_tag(content=(ROOT / 'page-experience-v22.css').read_text(encoding='utf-8'))
            page.add_script_tag(content=(ROOT / 'page-experience-v22.js').read_text(encoding='utf-8'))
            page.wait_for_function("()=>window.EInvitePageExperience?.version==='22.2.8'")
            page.wait_for_function("()=>document.querySelector('#workflowPageDock .workflow-page-dock-track')")
            page.wait_for_function("()=>document.querySelector('#designPagesManager')?.dataset.v22Managed==='true'")

            # There must be one compact page strip, not a second competing V22 dock.
            assert page.locator('#workflowPageDock').count() == 1
            assert page.locator('.v22-page-dock').count() == 0
            assert page.locator('#pageNavigator').is_hidden()
            assert page.locator('.v22-page-manager').count() == 1

            before = page.evaluate("()=>EInviteEditorBridge.getState().designPages.length")
            page.evaluate("()=>EInvitePageExperience.addPage({mode:'free-design',index:0})")
            page.wait_for_function("()=>{const p=EInviteEditorBridge.getState().designPages.length;return [...document.querySelectorAll('#workflowPageDock .workflow-page-chip[data-page-id]')].filter(n=>n.dataset.pageId).length===p&&document.querySelectorAll('#workflowPageDock .v22-workflow-insert').length===p+1}")
            state1 = page.evaluate("""()=>({
              pages:EInviteEditorBridge.getState().designPages.map(p=>({id:p.id,mode:p.editMode,name:p.name})),
              chips:[...document.querySelectorAll('#workflowPageDock .workflow-page-chip[data-page-id]')].filter(n=>n.dataset.pageId).length,
              inserts:document.querySelectorAll('#workflowPageDock .v22-workflow-insert').length
            })""")
            assert len(state1['pages']) == before + 1, state1
            assert state1['pages'][0]['mode'] == 'free-design', state1
            assert state1['chips'] == before + 1, state1
            assert state1['inserts'] == state1['chips'] + 1, state1

            page.evaluate("()=>EInvitePageExperience.addPage({mode:'event-template',role:'details',index:1})")
            page.wait_for_function("()=>{const p=EInviteEditorBridge.getState().designPages.at(1);return p&&EInviteEditorBridge.getActiveCanvasId()===`page:${p.id}`}")
            page.wait_for_timeout(120)
            state2 = page.evaluate("""()=>({
              pages:EInviteEditorBridge.getState().designPages.map(p=>({id:p.id,mode:p.editMode,role:p.eventRole,objects:Object.keys(p.objects||{}).length})),
              active:EInviteEditorBridge.getActiveCanvasId(),roleHidden:document.querySelector('[data-role-wrap]')?.hidden,
              managerCards:document.querySelectorAll('.v22-page-grid .v22-page-card[data-page-id]').length
            })""")
            assert state2['pages'][1]['mode'] == 'event-template', state2
            assert state2['pages'][1]['role'] == 'details', state2
            assert state2['pages'][1]['objects'] > 0, state2
            assert state2['roleHidden'] is False, state2
            assert state2['managerCards'] == len(state2['pages']), state2

            # Exercise the authoritative pointer-based dock reorder path and move the last page first.
            moving_id = page.evaluate("()=>EInviteEditorBridge.getState().designPages.at(-1).id")
            wait_for_reachable_control(page,f'#workflowPageDock .workflow-page-chip[data-page-id="{moving_id}"] .v22-dock-drag-handle')
            wait_for_reachable_control(page,'#workflowPageDock .v22-workflow-insert[data-insert-index="0"]')
            pointer_target = page.evaluate("""()=>{
              const initial=EInviteEditorBridge.getState().designPages.map(p=>p.id);
              const moving=initial.at(-1);
              const track=document.querySelector('#workflowPageDock .workflow-page-dock-track');
              const insert=track.querySelector('.v22-workflow-insert[data-insert-index="0"]');
              const chip=track.querySelector(`.workflow-page-chip[data-page-id="${CSS.escape(moving)}"]`);
              const handle=chip.querySelector('.v22-dock-drag-handle');
              const a=handle.getBoundingClientRect(),b=insert.getBoundingClientRect();
              return {moving,startX:a.left+a.width/2,startY:a.top+a.height/2,endX:b.left+b.width/2,endY:b.top+b.height/2};
            }""")
            page.mouse.move(pointer_target['startX'], pointer_target['startY'])
            page.mouse.down()
            page.wait_for_timeout(80)
            page.mouse.move(pointer_target['endX'], pointer_target['endY'], steps=12)
            page.wait_for_timeout(100)
            page.mouse.up()
            page.wait_for_function("moving=>EInviteEditorBridge.getState().designPages[0]?.id===moving",arg=pointer_target['moving'],timeout=5000)
            drag_result = page.evaluate("""moving=>({moving,after:EInviteEditorBridge.getState().designPages.map(p=>p.id)})""", pointer_target['moving'])
            assert drag_result['after'][0] == drag_result['moving'], drag_result

            # Keyboard reordering is an accessible alternative to drag.
            keyboard_result = page.evaluate("""async()=>{
              const state=EInviteEditorBridge.getState();
              const moving=state.designPages.at(-1).id;
              const chip=document.querySelector(`#workflowPageDock .workflow-page-chip[data-page-id="${CSS.escape(moving)}"]`);
              chip.focus();
              chip.dispatchEvent(new KeyboardEvent('keydown',{key:'Home',altKey:true,bubbles:true,cancelable:true}));
              await new Promise(r=>setTimeout(r,360));
              return {moving,order:EInviteEditorBridge.getState().designPages.map(p=>p.id)};
            }""")
            assert keyboard_result['order'][0] == keyboard_result['moving'], keyboard_result

            # Ctrl/Cmd+Enter adds a blank free-design page after the active page.
            active_before = page.evaluate("()=>EInviteEditorBridge.getState().designPages.length")
            page.keyboard.press('Control+Enter')
            page.wait_for_timeout(500)
            active_after = page.evaluate("()=>EInviteEditorBridge.getState().designPages.length")
            assert active_after == active_before + 1, (active_before, active_after)

            page.locator('[data-studio-tab="pages"]').click()
            page.wait_for_timeout(220)
            page.wait_for_function("()=>[...document.querySelectorAll('.v22-page-grid [data-page-thumb-id]')].some(n=>n.dataset.hydrated==='true')")
            perf = page.evaluate("""()=>({
              cache:EInvitePageExperience.cacheSize,
              hydrated:[...document.querySelectorAll('[data-page-thumb-id]')].filter(n=>n.dataset.hydrated==='true').length,
              manager:document.querySelector('#designPagesManager')?.dataset.v22Managed,
              version:document.documentElement.dataset.pageExperienceVersion
            })""")
            assert perf['manager'] == 'true' and perf['version'] == '22.2.8', perf
            assert perf['hydrated'] >= 1, perf
            assert not errors, errors[:20]
        finally:
            browser.close()
    print('V22_2_PAGE_EXPERIENCE_TEST_PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
