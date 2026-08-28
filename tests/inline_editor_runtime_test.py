#!/usr/bin/env python3
"""Real Chromium DOM/runtime smoke for the editor without network navigation.

The normal environment blocks browser navigation to localhost, so this test
inlines the app's local CSS/JS and executes the real editor in Chromium via
page.set_content(). It catches runtime races that static tests cannot.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from browser_runtime import launch_chromium,wait_for_reachable_control,skipped

ROOT = Path(__file__).resolve().parents[1]


def build_inline_editor() -> str:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    prelude = r"""<script>
const __local=new Map(),__session=new Map();
function __store(map){return {getItem:k=>map.has(String(k))?map.get(String(k)):null,setItem:(k,v)=>map.set(String(k),String(v)),removeItem:k=>map.delete(String(k)),clear:()=>map.clear(),key:i=>[...map.keys()][i]||null,get length(){return map.size}}}
const localStorage=__store(__local),sessionStorage=__store(__session);
window.alert=()=>{};window.confirm=()=>true;window.prompt=()=>'';
window.fetch=async()=>({ok:false,status:404,statusText:'Not Found',json:async()=>({}),text:async()=>'',headers:new Headers()});
</script>"""
    html = html.replace(
        '<head><script src="theme-init.js"></script>',
        '<head>' + prelude + '<script src="theme-init.js"></script>',
    )

    link_pattern = re.compile(r'<link\s+rel="stylesheet"\s+href="([^"]+)"\s*/?>')

    def inline_css(match: re.Match[str]) -> str:
        path = ROOT / match.group(1)
        if not path.exists():
            return match.group(0)
        return f'<style data-src="{match.group(1)}">{path.read_text(encoding="utf-8")}</style>'

    html = link_pattern.sub(inline_css, html)

    script_pattern = re.compile(r'<script src="([^"]+)"></script>')

    def inline_js(match: re.Match[str]) -> str:
        path = ROOT / match.group(1)
        if not path.exists():
            return match.group(0)
        text = path.read_text(encoding="utf-8").replace("</script>", "<\\/script>")
        extra = ""
        if match.group(1) == "storage.js":
            extra = r"""
window.__assetMem=[];
window.assetStore={
  put:async a=>{window.__assetMem=window.__assetMem.filter(x=>x.id!==a.id);window.__assetMem.push(a);return a.id},
  list:async()=>window.__assetMem.slice(),
  delete:async id=>{window.__assetMem=window.__assetMem.filter(x=>x.id!==id)}
};
"""
        # page.set_content() runs at about:blank; the real app runs at index.html.
        # Preserve the real editor page identity after legacy scripts infer it
        # from location.pathname so responsive page-specific CSS is exercised.
        extra += "\nif(document.body)document.body.dataset.page='index';"
        return f'<script data-src="{match.group(1)}">{text}{extra}</script>'

    html = script_pattern.sub(inline_js, html)
    extras=[]
    for name in ("rich-text-renderer-v21.css","rich-text-editing-v21.css","workspace-v21.css"):
        path=ROOT/name
        if path.exists(): extras.append(f'<style data-v21="{name}">{path.read_text(encoding="utf-8")}</style>')
    for name in ("rich-text-contract.js","rich-text-document-model.js","rich-text-renderer-v21.js","rich-text-editing-v21.js","workspace-v21.js"):
        path=ROOT/name
        if path.exists(): extras.append(f'<script data-v21="{name}">{path.read_text(encoding="utf-8").replace("</script>","<\\/script>")}</script>')
    return html.replace("</body>","".join(extras)+"</body>")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"INLINE_EDITOR_RUNTIME_SKIPPED_NO_PLAYWRIGHT: {exc}")
        return 0

    html = build_inline_editor()
    with sync_playwright() as p:
        try:
            browser = launch_chromium(p)
        except Exception as exc:  # pragma: no cover - environment dependent
            print(f"INLINE_EDITOR_RUNTIME_SKIPPED_NO_CHROMIUM: {exc}")
            return 0

        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(f"PAGE: {error}"))
        page.on(
            "console",
            lambda message: errors.append(f"CONSOLE: {message.text}")
            if message.type == "error"
            else None,
        )
        page.set_content(html, wait_until="load", timeout=30_000)
        page.wait_for_timeout(1_800)

        if page.locator("#finalTourDismiss").count() and page.locator("#finalTourDismiss").is_visible():
            page.locator("#finalTourDismiss").click()
            page.wait_for_timeout(100)

        assert not errors, f"Runtime errors during boot: {errors[:10]}"
        assert page.locator("#stage .object").count() >= 4
        assert page.locator('[data-studio-tab="text"]').count() == 1, "Text tab missing"
        assert page.locator('[data-studio-pane="text"]').count() == 1, "Text pane missing"
        assert page.locator(".workflow-v7-text-pane").count() == 1

        # Design-tool navigation must preserve the user's zoom.
        page.select_option("#zoomLevel", "1.25")
        for section in ("elements", "text", "media", "pages", "design", "text"):
            page.locator(f'[data-studio-tab="{section}"]').click()
            page.wait_for_timeout(80)
            assert page.locator("#zoomLevel").input_value() == "1.25", f"Zoom changed in {section}"

        # Content mode must be genuinely scrollable and hide the artboard.
        page.locator('[data-studio-tab="event"]').click()
        page.wait_for_timeout(120)
        scroll_info = page.evaluate(
            """()=>{const pane=document.querySelector('.studio-pane.active');pane.scrollTop=700;return {
              section:pane.dataset.studioPane,scrollTop:pane.scrollTop,scrollHeight:pane.scrollHeight,
              clientHeight:pane.clientHeight,stageHidden:document.querySelector('.stage-wrap').hidden,
              overflowY:getComputedStyle(pane).overflowY,scrollBehavior:getComputedStyle(pane).scrollBehavior
            }}"""
        )
        assert scroll_info["section"] == "event"
        assert scroll_info["scrollHeight"] > scroll_info["clientHeight"]
        assert scroll_info["scrollTop"] > 100, f"Event pane did not scroll: {scroll_info}"
        assert scroll_info["stageHidden"] is True
        assert scroll_info["overflowY"] == "auto"
        assert scroll_info["scrollBehavior"] == "auto"

        # Back-to-canvas returns to the last design tool, not to an unrelated pane.
        page.locator(".studio-pane.active .workflow-v7-back-canvas").click()
        page.wait_for_timeout(120)
        assert page.locator(".studio-pane.active").get_attribute("data-studio-pane") == "text"
        assert page.locator(".stage-wrap").get_attribute("hidden") is None

        # Keyboard routing must not collide between persistent drawing tools
        # and workflow shortcuts. These checks exercise the final event order
        # rather than only looking for shortcut strings statically.
        page.keyboard.press("Shift+E")
        page.wait_for_timeout(80)
        assert page.locator(".studio-pane.active").get_attribute("data-studio-pane") == "elements"
        page.keyboard.press("Shift+T")
        page.wait_for_timeout(80)
        assert page.locator(".studio-pane.active").get_attribute("data-studio-pane") == "text"
        page.keyboard.press("Shift+U")
        page.wait_for_timeout(80)
        assert page.locator(".studio-pane.active").get_attribute("data-studio-pane") == "media"
        page.keyboard.press("Shift+F")
        page.wait_for_timeout(80)
        assert "workflow-focus-canvas" in (page.locator("body").get_attribute("class") or "")
        page.keyboard.press("Shift+F")
        page.wait_for_timeout(80)
        assert "workflow-focus-canvas" not in (page.locator("body").get_attribute("class") or "")
        page.keyboard.press("p")
        page.wait_for_timeout(80)
        assert "open" in (page.locator("#workflowV6Position").get_attribute("class") or "")
        page.keyboard.press("Escape")
        page.keyboard.press("q")
        page.wait_for_timeout(80)
        assert "open" in (page.locator("#workflowV6Flow").get_attribute("class") or "")
        page.keyboard.press("Escape")
        page.locator('[data-studio-tab="text"]').click()
        page.wait_for_timeout(80)

        # Uploaded-library drag must add exactly the dragged asset and must not
        # reposition or duplicate a preexisting selected object.
        page.evaluate("""async()=>{
          await assetStore.put({id:'runtime-library-asset',name:'library-runtime.png',type:'image/png',blob:new Blob(['runtime-library-image'],{type:'image/png'}),createdAt:Date.now()});
          await renderAssets();
        }""")
        page.wait_for_timeout(160)
        assert page.locator('#assets img[data-asset-id="runtime-library-asset"]').count() == 1
        library_before = page.locator("#stage .object").count()
        page.evaluate("""()=>{
          const img=document.querySelector('#assets img[data-asset-id="runtime-library-asset"]'),stage=document.querySelector('#stage'),r=stage.getBoundingClientRect(),dt=new DataTransfer();
          img.dispatchEvent(new DragEvent('dragstart',{bubbles:true,cancelable:true,dataTransfer:dt}));
          stage.dispatchEvent(new DragEvent('dragover',{bubbles:true,cancelable:true,dataTransfer:dt,clientX:r.left+r.width*.72,clientY:r.top+r.height*.34}));
          stage.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt,clientX:r.left+r.width*.72,clientY:r.top+r.height*.34}));
        }""")
        page.wait_for_timeout(500)
        assert page.locator("#stage .object").count() == library_before + 1
        assert page.locator('#stage .object[data-alt="library-runtime.png"]').count() == 1

        # Generic element drag uses object identity, not the previous selection,
        # and lands the newly-created object close to the requested drop point.
        element_before = page.locator("#stage .object").count()
        page.evaluate("""()=>{
          const source=document.querySelector('[data-add-element="rectangle"]'),stage=document.querySelector('#stage'),r=stage.getBoundingClientRect(),dt=new DataTransfer();
          source.dispatchEvent(new DragEvent('dragstart',{bubbles:true,cancelable:true,dataTransfer:dt}));
          stage.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt,clientX:r.left+r.width*.28,clientY:r.top+r.height*.72}));
        }""")
        page.wait_for_timeout(500)
        assert page.locator("#stage .object").count() == element_before + 1
        element_pos = page.evaluate("""()=>{const s=document.querySelector('#stage').getBoundingClientRect(),o=document.querySelector('#stage .object.selected,#stage .object.multi-selected').getBoundingClientRect();return {x:(o.left+o.width/2-s.left)/s.width,y:(o.top+o.height/2-s.top)/s.height}}""")
        assert abs(element_pos["x"] - .28) < .08 and abs(element_pos["y"] - .72) < .08, element_pos

        # Visible Text workspace inserts and selects a new object.
        before = page.locator("#stage .object").count()
        page.locator(".workflow-v7-text-pane .refine-add-text").click()
        page.wait_for_timeout(220)
        after = page.locator("#stage .object").count()
        assert after == before + 1, f"Text insertion count mismatch: {before} -> {after}"
        assert page.locator("#stage .object.selected,#stage .object.multi-selected").count() >= 1

        # Stored rich text must be sanitized again when document state is applied
        # in the authenticated editor, while safe Khmer/English formatting survives.
        xss_id = page.locator("#stage .object.selected").get_attribute("data-id")
        page.evaluate(r"""id=>{
          const source='<img src=x onerror=alert(1)><script>alert(1)</script><a href="javascript:alert(1)">Test</a><strong>ខ្មែរ</strong><br><em>English</em>';
          const object=state.objects[id];
          object.richText=RichTextDocumentModel.migrateLegacy(id,{html:source,textStyleId:object.textStyleId||'body'},{styleIds:Object.keys(state.typography?.styles||{}),defaultStyleId:state.typography?.defaultStyleId||'body'});
          object.richTextModelVersion=RichTextDocumentModel.MODEL_VERSION;
          object.html=RichTextDocumentModel.exportLegacyHtml(object.richText);
          object.text=RichTextDocumentModel.exportPlainText(object.richText);
          apply();
          const o=document.querySelector(`#stage .object[data-id="${CSS.escape(id)}"]`);clearSelection();setSelection([o]);
        }""", xss_id)
        page.wait_for_timeout(80)
        sanitized = page.evaluate(r"""id=>{const c=document.querySelector(`#stage .object[data-id="${CSS.escape(id)}"] .content`);return {html:c.innerHTML,scripts:c.querySelectorAll('script').length,images:c.querySelectorAll('img').length,badLinks:[...c.querySelectorAll('a')].filter(a=>(a.getAttribute('href')||'').toLowerCase().startsWith('javascript:')).length,strong:[...c.querySelectorAll('strong')].some(x=>x.textContent.includes('ខ្មែរ')),em:[...c.querySelectorAll('em')].some(x=>x.textContent.includes('English')),paragraphs:c.querySelectorAll('.rt-paragraph').length,breaks:c.querySelectorAll('br').length}}""", xss_id)
        assert sanitized["scripts"] == 0 and sanitized["images"] == 0 and sanitized["badLinks"] == 0, sanitized
        assert sanitized["strong"] and sanitized["em"] and sanitized["breaks"] >= 1, sanitized

        # Font-picker changes must update the object, inspector, autosave history,
        # and undo/redo as one state transition.
        page.wait_for_timeout(420)
        original_font = page.locator("#stage .object.selected").get_attribute("data-font") or ""
        georgia = page.locator('.workflow-v7-text-pane .fp-inline-font').filter(has_text='Noto Serif').first
        assert georgia.count() == 1
        georgia.click()
        page.wait_for_timeout(420)
        font_after = page.evaluate("""()=>({object:document.querySelector('#stage .object.selected')?.dataset.font||'',inspector:document.querySelector('#font')?.value||'',ctx:[...document.querySelectorAll('[data-ctx="font"]')].map(x=>x.value)})""")
        assert font_after["object"] == 'noto-serif', font_after
        assert font_after["inspector"] == 'noto-serif', font_after
        assert all(v == 'noto-serif' for v in font_after["ctx"]), font_after
        resolved_font=page.evaluate("()=>getComputedStyle(document.querySelector('#stage .object.selected .content')).fontFamily")
        assert 'EInvite Noto Serif' in resolved_font and 'Khmer UI' in resolved_font,resolved_font
        page.locator("#undoBtn").click()
        page.wait_for_timeout(180)
        undone_font = page.evaluate("id=>document.querySelector(`#stage .object[data-id=\"${CSS.escape(id)}\"]`)?.dataset.font||''", xss_id)
        assert undone_font == original_font, (original_font, undone_font)
        page.locator("#redoBtn").click()
        page.wait_for_timeout(180)
        redone_font = page.evaluate("id=>document.querySelector(`#stage .object[data-id=\"${CSS.escape(id)}\"]`)?.dataset.font||''", xss_id)
        assert redone_font == 'noto-serif', redone_font
        page.evaluate("id=>{const o=document.querySelector(`#stage .object[data-id=\"${CSS.escape(id)}\"]`);clearSelection();setSelection([o])}", xss_id)
        page.wait_for_timeout(60)
        assert page.locator("#font").input_value() == 'noto-serif'

        # Khmer font stacks that are not predeclared in the inspector select must
        # be added dynamically and participate in the same undo/redo state flow.
        page.locator('[data-v7-font-cat="Khmer"]').click()
        page.wait_for_timeout(60)
        page.locator('.workflow-v7-text-pane .fp-inline-font').filter(has_text='Khmer Sans').first.click()
        page.wait_for_timeout(420)
        khmer_stack='noto-sans-khmer'
        khmer_state=page.evaluate("""()=>({object:document.querySelector('#stage .object.selected')?.dataset.font||'',inspector:document.querySelector('#font')?.value||''})""")
        assert khmer_state['object']==khmer_stack and khmer_state['inspector']==khmer_stack,khmer_state
        page.locator('#undoBtn').click();page.wait_for_timeout(180)
        assert page.evaluate("id=>document.querySelector(`#stage .object[data-id=\"${CSS.escape(id)}\"]`)?.dataset.font||''",xss_id)=='noto-serif'
        page.locator('#redoBtn').click();page.wait_for_timeout(180)
        assert page.evaluate("id=>document.querySelector(`#stage .object[data-id=\"${CSS.escape(id)}\"]`)?.dataset.font||''",xss_id)==khmer_stack
        page.evaluate("id=>{const o=document.querySelector(`#stage .object[data-id=\"${CSS.escape(id)}\"]`);clearSelection();setSelection([o])}",xss_id)
        page.wait_for_timeout(60)
        assert page.locator('#font').input_value()==khmer_stack

        # Single-object page centering is precise.
        page.evaluate("window.EInviteProEditorV6.alignToCanvas('hcenter');window.EInviteProEditorV6.alignToCanvas('vcenter')")
        centers = page.evaluate(
            """()=>{const s=document.querySelector('#stage').getBoundingClientRect(),o=document.querySelector('#stage .object.selected').getBoundingClientRect();return {dx:o.left+o.width/2-(s.left+s.width/2),dy:o.top+o.height/2-(s.top+s.height/2)}}"""
        )
        assert abs(centers["dx"]) < 1.5 and abs(centers["dy"]) < 1.5, centers

        # Multi-object page centering must preserve the group's internal spacing.
        page.evaluate(
            """()=>{const all=[...document.querySelectorAll('#stage .object')].slice(0,2);clearSelection();setSelection(all)}"""
        )
        before_group = page.evaluate(
            """()=>[...document.querySelectorAll('#stage .object.selected,#stage .object.multi-selected')].map(o=>({id:o.dataset.id,left:parseFloat(o.style.left),top:parseFloat(o.style.top)}))"""
        )
        page.evaluate("window.EInviteProEditorV6.alignToCanvas('hcenter')")
        after_group = page.evaluate(
            """()=>[...document.querySelectorAll('#stage .object.selected,#stage .object.multi-selected')].map(o=>({id:o.dataset.id,left:parseFloat(o.style.left),top:parseFloat(o.style.top)}))"""
        )
        assert len(before_group) == len(after_group) == 2
        before_dx = before_group[1]["left"] - before_group[0]["left"]
        after_dx = after_group[1]["left"] - after_group[0]["left"]
        assert abs(before_dx - after_dx) < 0.05, (before_group, after_group)

        # Add two visual pages and verify they enter published flow.
        page.locator('[data-studio-tab="pages"]').click()
        page.wait_for_timeout(80)
        page.locator('[data-add-page="title"]').first.click()
        page.wait_for_timeout(100)
        page.locator('[data-add-page="photo"]').first.click()
        page.wait_for_timeout(250)
        page_data = page.evaluate("()=>({ids:state.designPages.map(p=>p.id),order:[...state.sectionOrder]})")
        assert len(page_data["ids"]) >= 2
        for page_id in page_data["ids"][-2:]:
            assert f"page:{page_id}" in page_data["order"]

        # Flow controls must be reachable from Design and the page dock.
        assert page.locator("#workflowV7DesignFlow").count() == 1
        assert page.locator("#workflowV7DockFlow").count() == 1

        # Reordering in Flow must update both sectionOrder and designPages order.
        page.evaluate("window.EInviteProEditorV6.openFlow()")
        page.wait_for_timeout(100)
        visual_rows = page.locator('.workflow-v6-flow-item:has(small:text("Visual page"))')
        assert visual_rows.count() >= 2
        first_token = visual_rows.nth(0).get_attribute("data-token")
        second_token = visual_rows.nth(1).get_attribute("data-token")
        visual_rows.nth(0).locator('[data-move="down"]').click()
        page.wait_for_timeout(140)
        reordered = page.evaluate("()=>({order:[...state.sectionOrder],pages:state.designPages.map(p=>`page:${p.id}`)})")
        assert reordered["order"].index(second_token) < reordered["order"].index(first_token)
        page_order_in_flow = [token for token in reordered["order"] if str(token).startswith("page:")]
        assert reordered["pages"][: len(page_order_in_flow)] == page_order_in_flow

        # Dropping a local image on a visual page must create an editable object,
        # persist it in the material store, and not add it to the hero gallery.
        page.evaluate("document.querySelector('#workflowV6Flow').classList.remove('open')")
        visual_token = reordered["pages"][0]
        page.evaluate("token=>switchCanvas(token)", visual_token)
        page.wait_for_timeout(120)
        gallery_before = page.evaluate("()=>[...(state.galleryOrder||[])]")
        object_before = page.locator("#stage .object").count()
        page.evaluate(
            """()=>{const stage=document.querySelector('#stage'),r=stage.getBoundingClientRect();const dt=new DataTransfer();dt.items.add(new File(['fake-image-bytes'],'runtime-drop.png',{type:'image/png'}));const ev=new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt,clientX:r.left+r.width*.55,clientY:r.top+r.height*.5});stage.dispatchEvent(ev)}"""
        )
        page.wait_for_timeout(500)
        object_after = page.locator("#stage .object").count()
        assert object_after == object_before + 1, (object_before, object_after)
        gallery_after = page.evaluate("()=>[...(state.galleryOrder||[])]")
        assert gallery_after == gallery_before, "Visual-page drop polluted hero gallery"
        assert page.evaluate("async()=>{const rows=await window.assetStore.list();return rows.some(a=>a.name==='runtime-drop.png')}") is True
        dropped = page.locator('#stage .object[data-layer-name="runtime-drop"]')
        assert dropped.count() == 1
        assert dropped.get_attribute("data-show-in-gallery") == "false"

        assert not errors, f"Runtime errors after interactions: {errors[:20]}"

        # Phone workflow: creation panel overlays predictably, insertion returns
        # focus to the artboard, and the inspector behaves as a compact bottom
        # sheet rather than covering almost the entire screen.
        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_errors: list[str] = []
        mobile.on("pageerror", lambda error: mobile_errors.append(f"PAGE: {error}"))
        mobile.on(
            "console",
            lambda message: mobile_errors.append(f"CONSOLE: {message.text}")
            if message.type == "error"
            else None,
        )
        mobile.set_content(html, wait_until="load", timeout=30_000)
        mobile.wait_for_timeout(1_500)
        if mobile.locator("#finalTourDismiss").count() and mobile.locator("#finalTourDismiss").is_visible():
            mobile.locator("#finalTourDismiss").click()
            mobile.wait_for_timeout(80)
        assert mobile.locator("body").get_attribute("data-page") == "index"
        main_box = mobile.locator("main").bounding_box()
        assert main_box and main_box["height"] > 700, main_box
        mobile.wait_for_selector("#mobileEditorV14Bar", state="visible")
        # V14 starts canvas-first and exposes creation and quick-edit as
        # mutually exclusive, full-height drawers.
        assert mobile.locator("aside.left").get_attribute("aria-hidden") == "true"
        assert mobile.locator("aside.right").get_attribute("aria-hidden") == "true"
        mobile.locator("#mobileToolsMode").click()
        assert mobile.locator("aside.left").get_attribute("aria-hidden") == "false"
        assert mobile.locator("aside.right").get_attribute("aria-hidden") == "true"
        mobile.locator('[data-studio-tab="text"]').click()
        mobile.wait_for_timeout(100)
        assert mobile.locator(".workflow-v7-text-pane").is_visible()
        mobile.locator(".workflow-v7-text-pane .refine-add-text").click()
        mobile.wait_for_timeout(300)
        mobile.locator("#mobileCanvasMode").click()
        assert mobile.locator("#stage").is_visible()
        assert mobile.locator("aside.left").get_attribute("aria-hidden") == "true"
        assert mobile.locator("aside.right").get_attribute("aria-hidden") == "true"

        mobile.locator("#mobileQuickMode").click()
        mobile.wait_for_function("""()=>document.body.dataset.editorDrawer==='inspector'&&document.querySelector('aside.left')?.getAttribute('aria-hidden')==='true'&&document.querySelector('aside.right')?.getAttribute('aria-hidden')==='false'""",timeout=8000)
        assert mobile.locator("aside.left").get_attribute("aria-hidden") == "true"
        assert mobile.locator("aside.right").get_attribute("aria-hidden") == "false"
        assert not mobile.locator("body").evaluate("e=>e.classList.contains('mobile-creation-open')")
        assert mobile.locator("body").evaluate("e=>e.classList.contains('mobile-inspector-open')||e.classList.contains('inspector-open')")
        inspector_box = mobile.locator("aside.right").bounding_box()
        assert inspector_box and inspector_box["height"] > 600 and inspector_box["height"] <= 780, inspector_box
        assert inspector_box["y"] >= 50, inspector_box
        resizer_state = mobile.evaluate("""()=>{const r=document.querySelector('.studio-panel-resizer.r');return r?{display:getComputedStyle(r).display,visibility:getComputedStyle(r).visibility,pointer:getComputedStyle(r).pointerEvents}:null}""")
        assert resizer_state and resizer_state["display"] == "none" and resizer_state["pointer"] == "none", resizer_state
        controls = [wait_for_reachable_control(mobile,selector,timeout=8000) for selector in ("#font", "#color", "#fontSize", "#animation")]
        assert all(item["ok"] for item in controls), controls
        # Image inspector controls must also remain reachable in Quick Edit.
        mobile.evaluate("""()=>{const image=document.querySelector('#stage .image-object');clearSelection();setSelection([image])}""")
        mobile.wait_for_function("""()=>document.body.dataset.editorDrawer==='inspector'&&document.querySelector('#imageFit')&&getComputedStyle(document.querySelector('#imageFit')).display!=='none'""",timeout=8000)
        image_control = wait_for_reachable_control(mobile,"#imageFit",timeout=8000)
        assert image_control["ok"], image_control
        # Creation tools can be reopened without losing the selected object.
        selected_before = mobile.locator("#stage .object.selected,#stage .object.multi-selected").count()
        mobile.locator("#mobileToolsMode").click()
        mobile.wait_for_timeout(300)
        elements_tab = mobile.locator('[data-studio-tab="elements"]')
        elements_tab.scroll_into_view_if_needed()
        elements_tab.click()
        mobile.wait_for_timeout(120)
        assert mobile.locator("aside.left").get_attribute("aria-hidden") == "false"
        assert mobile.locator("aside.right").get_attribute("aria-hidden") == "true"
        assert mobile.locator('[data-studio-pane="elements"]').is_visible()
        assert mobile.locator("#stage").is_visible()
        assert mobile.locator("#stage .object.selected,#stage .object.multi-selected").count() == selected_before
        assert not mobile_errors, f"Mobile runtime errors: {mobile_errors[:20]}"
        mobile.close()
        page.close()
        browser.close()

    print("INLINE_EDITOR_RUNTIME_TEST_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
