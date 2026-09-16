#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

from browser_runtime import launch_chromium, skipped

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
        return skipped('V22_2_PAGE_REFINEMENT', exc)

    with sync_playwright() as p:
        try:
            browser = launch_chromium(p)
        except Exception as exc:
            return skipped('V22_2_PAGE_REFINEMENT', exc)
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.set_default_timeout(60_000)
            errors: list[str] = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
            page.set_content(build(), wait_until='load')
            page.wait_for_timeout(1200)
            if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():
                page.locator('#finalTourDismiss').click()
            page.add_style_tag(content=(ROOT / 'page-experience-v22.css').read_text(encoding='utf-8'))
            page.add_script_tag(content=(ROOT / 'page-experience-v22.js').read_text(encoding='utf-8'))
            page.wait_for_function("()=>EInvitePageExperience?.version==='22.2.8'")
            page.evaluate("()=>{window.uiConfirm=async()=>true}")

            created = page.evaluate("""()=>{
              const a=EInvitePageExperience.addPage({mode:'free-design'});
              const b=EInvitePageExperience.addPage({mode:'event-template',role:'details'});
              const c=EInvitePageExperience.addPage({mode:'free-design'});
              return {a:a.id,b:b.id,c:c.id};
            }""")
            page.wait_for_timeout(550)
            page.locator('[data-studio-tab="pages"]').click()
            page.wait_for_timeout(250)

            # The main Add Page action inserts after the active page instead of always appending.
            page.evaluate("id=>{const p=EInviteEditorBridge.getState().designPages.find(x=>x.id===id);switchCanvas(`page:${p.id}`)}", created['b'])
            page.wait_for_timeout(180)
            before_order = page.evaluate("()=>EInviteEditorBridge.getState().designPages.map(p=>p.id)")
            add_anchor = page.locator('.v22-page-manager [data-add-page]')
            add_anchor.click()
            dialog = page.locator('.v22-page-menu')
            assert dialog.get_attribute('role') == 'dialog'
            assert add_anchor.get_attribute('aria-expanded') == 'true'
            dialog.locator('[data-add-mode="free-design"]').click()
            page.wait_for_timeout(420)
            inserted = page.evaluate("""b=>{
              const list=EInviteEditorBridge.getState().designPages;
              const at=list.findIndex(p=>p.id===b);
              return {id:list[at+1]?.id,mode:list[at+1]?.editMode,order:list.map(p=>p.id),active:EInviteEditorBridge.getActiveCanvasId()};
            }""", created['b'])
            assert inserted['mode'] == 'free-design', inserted
            assert inserted['order'].index(inserted['id']) == before_order.index(created['b']) + 1, inserted
            assert inserted['active'] == f"page:{inserted['id']}", inserted

            # Escape closes menus and restores focus.
            add_anchor.click()
            page.keyboard.press('Escape')
            page.wait_for_timeout(80)
            assert page.locator('.v22-page-menu').count() == 0
            assert page.evaluate("()=>document.activeElement===document.querySelector('.v22-page-manager [data-add-page]')")

            # Deleting the active page selects the nearest surviving page, not the hero canvas.
            next_id = page.evaluate("""id=>{const list=EInviteEditorBridge.getState().designPages;const at=list.findIndex(p=>p.id===id);return list[at+1]?.id||list[at-1]?.id||''}""", inserted['id'])
            page.evaluate("id=>EInvitePageExperience.deletePage(id)", inserted['id'])
            page.wait_for_timeout(480)
            assert page.evaluate("()=>EInviteEditorBridge.getActiveCanvasId()") == (f"page:{next_id}" if next_id else 'hero')

            # Changing an event role preserves the design. Applying the layout is explicit.
            event_before = page.evaluate("""id=>{const p=EInviteEditorBridge.getState().designPages.find(x=>x.id===id);return {count:Object.keys(p.objects||{}).length,first:Object.keys(p.objects||{})[0]}}""", created['b'])
            page.evaluate("id=>EInvitePageExperience.setPageMode(id,'event-template','story')", created['b'])
            page.wait_for_timeout(260)
            preserved = page.evaluate("""id=>{const p=EInviteEditorBridge.getState().designPages.find(x=>x.id===id);return {count:Object.keys(p.objects||{}).length,first:Object.keys(p.objects||{})[0],role:p.eventRole}}""", created['b'])
            assert preserved['count'] == event_before['count'] and preserved['first'] == event_before['first'], (event_before, preserved)
            assert preserved['role'] == 'story', preserved
            page.evaluate("id=>EInvitePageExperience.applyEventPreset(id,'story')", created['b'])
            page.wait_for_timeout(420)
            replaced = page.evaluate("""id=>{const p=EInviteEditorBridge.getState().designPages.find(x=>x.id===id);return {count:Object.keys(p.objects||{}).length,first:Object.keys(p.objects||{})[0],role:p.eventRole}}""", created['b'])
            assert replaced['role'] == 'story' and replaced['first'] != event_before['first'], replaced

            # Missing structured fields are created safely when the user types into them.
            page.evaluate("id=>EInvitePageExperience.applyEventPreset(id,'details')", created['b'])
            page.wait_for_timeout(360)
            page.evaluate("""id=>EInviteCommands.execute('Remove test event venue',doc=>{const p=doc.designPages.find(x=>x.id===id);for(const key of Object.keys(p.objects||{}))if(key.endsWith('-venue')||key.includes('event-venue'))delete p.objects[key]},{render:false})""", created['b'])
            page.evaluate("()=>EInvitePageExperience.render({force:true})")
            page.wait_for_timeout(260)
            venue = page.locator('[data-event-fields] label').filter(has_text='Venue text').locator('input')
            venue.fill('New event venue')
            page.wait_for_timeout(620)
            created_field = page.evaluate("""id=>{const p=EInviteEditorBridge.getState().designPages.find(x=>x.id===id);const e=Object.entries(p.objects||{}).find(([k,o])=>k.includes('event-venue')&&o.html==='New event venue');return e?{id:e[0],type:e[1].type,width:e[1].width}:null}""", created['b'])
            assert created_field and created_field['type'] == 'text', created_field

            # Reconciliation preserves the existing card node, scroll position, and keyboard focus.
            identity = page.evaluate("""id=>{
              const grid=document.querySelector('.v22-page-grid');
              const card=grid.querySelector(`[data-page-id="${CSS.escape(id)}"]`);
              window.__v22CardIdentity=card;grid.scrollTop=31;card.focus({preventScroll:true});
              return {ok:true,scroll:grid.scrollTop,sequence:EInvitePageExperience.renderSequence};
            }""", created['b'])
            assert identity['ok']
            page.evaluate("id=>EInvitePageExperience.reorderPage(id,0)", created['b'])
            page.wait_for_function("""({id,sequence})=>{
              const grid=document.querySelector('.v22-page-grid'),card=grid?.querySelector(`[data-page-id="${CSS.escape(id)}"]`);
              return EInvitePageExperience.renderSequence>sequence&&card===window.__v22CardIdentity&&document.activeElement===card&&EInviteEditorBridge.getState().designPages[0].id===id;
            }""", arg={'id':created['b'],'sequence':identity['sequence']})
            retained = page.evaluate("""({id,scroll})=>{const grid=document.querySelector('.v22-page-grid'),card=grid.querySelector(`[data-page-id="${CSS.escape(id)}"]`);return {same:card===window.__v22CardIdentity,scroll:grid.scrollTop,scrollPreserved:grid.scrollTop===scroll,focus:document.activeElement===card,first:EInviteEditorBridge.getState().designPages[0].id,sequence:EInvitePageExperience.renderSequence}}""", {'id':created['b'],'scroll':identity['scroll']})
            assert retained['same'] and retained['focus'] and retained['scrollPreserved'] and retained['first'] == created['b'], retained

            # Pointer/touch-compatible drag handle reorders using one page command.
            cards = page.locator('.v22-page-card[data-page-id]')
            assert cards.count() >= 3
            cards.nth(0).scroll_into_view_if_needed()
            cards.nth(1).scroll_into_view_if_needed()
            moving_id = cards.nth(0).get_attribute('data-page-id')
            handle_box = cards.nth(0).locator('.v22-page-drag-handle').bounding_box()
            target_box = cards.nth(1).bounding_box()
            assert handle_box and target_box
            page.mouse.move(handle_box['x'] + handle_box['width']/2, handle_box['y'] + handle_box['height']/2)
            page.mouse.down()
            page.mouse.move(target_box['x'] + target_box['width']*.9, target_box['y'] + target_box['height']*.9, steps=8)
            page.mouse.up()
            page.wait_for_timeout(460)
            pointer_order = page.evaluate("()=>EInviteEditorBridge.getState().designPages.map(p=>p.id)")
            assert pointer_order.index(moving_id) >= 1, pointer_order

            assert page.evaluate("()=>EInvitePageExperience.pendingThumbnailJobs") >= 0
            assert not errors, errors[:20]
        finally:
            browser.close()
    print('V22_2_PAGE_REFINEMENT_TEST_PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
