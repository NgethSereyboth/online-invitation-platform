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
        return skipped('V22_2_PAGE_PERFORMANCE', exc)
    with sync_playwright() as p:
        try:
            browser = launch_chromium(p)
        except Exception as exc:
            return skipped('V22_2_PAGE_PERFORMANCE', exc)
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.set_default_timeout(60_000)
            errors: list[str] = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.set_content(build(), wait_until='load')
            page.wait_for_timeout(1200)
            if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():
                page.locator('#finalTourDismiss').click()
            page.add_style_tag(content=(ROOT / 'page-experience-v22.css').read_text(encoding='utf-8'))
            page.add_script_tag(content=(ROOT / 'page-experience-v22.js').read_text(encoding='utf-8'))
            page.wait_for_function("()=>window.EInvitePageExperience?.version==='22.2.8'")
            page.locator('[data-studio-tab="pages"]').click()
            page.wait_for_timeout(180)

            result = page.evaluate("""async()=>{
              const next=EInviteEditorBridge.cloneState();
              next.designPages=Array.from({length:120},(_,i)=>({
                id:`perf-page-${i}`,name:`Performance page ${i+1}`,preset:'blank',editMode:i%3===0?'event-template':'free-design',
                eventRole:i%3===0?'details':'',enabled:true,background:i%2?'#fffaf6':'#f6f8ff',backgroundImage:'',backgroundSize:'cover',
                backgroundOverlay:0,useMasterBackground:false,animation:{preset:'fade-up',duration:900},transition:{preset:'soft',duration:600},
                objects:{[`perf-object-${i}`]:{type:'text',left:'10%',top:'18%',width:'80%',height:'16%',html:`Page ${i+1}`,fontSize:32,color:'#222'}}
              }));
              next.sectionOrder=[...(next.sectionOrder||[]).filter(x=>!String(x).startsWith('page:')),...next.designPages.map(p=>`page:${p.id}`)];
              const start=performance.now();
              EInviteEditorBridge.replaceState(next,{render:false,history:false,save:false,reason:'page-performance'});
              EInvitePageExperience.render();
              await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
              const initialMs=performance.now()-start;
              const cards=document.querySelectorAll('.v22-page-grid .v22-page-card[data-page-id]').length;
              const chips=[...document.querySelectorAll('#workflowPageDock .workflow-page-chip[data-page-id]')].filter(n=>n.dataset.pageId).length;
              const hydratedNow=[...document.querySelectorAll('.v22-page-grid [data-page-thumb-id]')].filter(n=>n.dataset.hydrated==='true').length;
              await new Promise(r=>setTimeout(r,650));
              const hydratedIdle=[...document.querySelectorAll('.v22-page-grid [data-page-thumb-id]')].filter(n=>n.dataset.hydrated==='true').length;
              return {initialMs,cards,chips,hydratedNow,hydratedIdle,cache:EInvitePageExperience.cacheSize};
            }""")
            assert result['cards'] == 120, result
            assert result['chips'] == 120, result
            assert result['hydratedNow'] < 40, result
            assert result['hydratedIdle'] < 80, result
            assert result['cache'] <= 72, result
            # A generous browser-container ceiling; the architectural invariant is bounded hydration.
            assert result['initialMs'] < 650, result
            assert not errors, errors[:20]
            print('V22_2_PAGE_PERFORMANCE_RESULT', result)
        finally:
            browser.close()
    print('V22_2_PAGE_PERFORMANCE_TEST_PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
