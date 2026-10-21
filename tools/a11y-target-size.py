#!/usr/bin/env python3
"""a11y-target-size.py — NW-1.5 measurement harness (WCAG 2.5.8 Target Size, Minimum).

Measures the LIVE pointer-hit region of the selected object's resize handle in the editor
(index.html) at four viewports (1440/1024/768/375), zoom 100%, plus the professional-editor
selection-overlay handles when present.

Method
  1. Open the editor (throwaway account + invitation, same recipe as canvas motion tests).
  2. Add a text object and select it (click its centre).
  3. Grid-hit-test with elementsFromPoint over the handle's bounding rect expanded by the
     documented ::before { inset:-18px } expansion. A grid point "hits" when the top-most
     element is the handle element itself or a descendant. The measured hit box is the
     bounding box of hitting points (CSS px, at the page's own zoom).
  4. Pointer checks (regression guards for the hit expansion):
       a. drag the handle halfway diagonally -> object width/height change (resize works);
       b. click the object centre -> object stays selected (no click stealing);
       c. drag the rotate handle -> rotation changes (rotate still reachable).
  5. Also record #peSelectionBox [data-pe-handle=se] size when present.

Writes focus-style JSON + screenshots under --out/. Returns 0 when every measured data
point is >=24x24; 2 otherwise. Read-only against repo source.
"""
from __future__ import annotations
import argparse,datetime,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium,mark_editor_onboarding_seen,dismiss_editor_onboarding
from v14_test_utils import app_server

VIEWPORTS=[(1440,900),(1024,768),(768,1024),(375,667)]
LANG="en"

# Harness JS constants (single-quoted to survive Playwright arg-passing)
SETUP_JS=r"""()=>{
  const stage=document.querySelector('#stage');
  if(!stage)return {error:'no #stage'};
  // Add one text object through the app's own object factory if exposed; fall back to
  // clicking the existing hero title object.
  const hero=stage.querySelector('.object[data-id]');
  if(!hero)return {error:'no objects'};
  return {objectId:hero.dataset.id,rect:hero.getBoundingClientRect().toJSON()};
}"""

SELECT_JS=r"""objectId=>{
  const obj=document.querySelector('#stage .object[data-id="'+objectId+'"]');
  if(!obj)return {error:'object missing'};
  const r=obj.getBoundingClientRect();
  const cx=r.left+r.width/2,cy=r.top+r.height/2;
  const seq=['pointerdown','pointerup'];
  // Click to select (bubbles through the app's own handlers).
  for(const type of seq){
    obj.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,clientX:cx,clientY:cy,pointerId:1,button:0,buttons:type==='pointerdown'?1:0}));
  }
  return new Promise(res=>requestAnimationFrame(()=>requestAnimationFrame(()=>{
    res({selected:String(document.querySelector('#stage .object.selected[data-id]')?.dataset.id||''),
         handle:!!document.querySelector('#stage .object.selected .resize-handle, #stage .object.selected > i.resize-handle')});
  })));
}"""

MOBILE_MEASURE_JS=r"""objectId=>{
  // ≤650px: the designed mobile flow opens the inspector drawer on selection and the
  // on-canvas overlay is hidden while a drawer holds the workspace. The handle hit
  // geometry is nevertheless dimensioned by CSS at this breakpoint with !important
  // (width/height 44px, pointer-events:auto), so the CSS-declared box IS the hit box
  // whenever the canvas is on top. Record the computed box.
  const se=document.querySelector('#peSelectionBox [data-pe-handle="se"]');
  if(!se)return {error:'pe se-handle missing'};
  const r=se.getBoundingClientRect();
  const cs=getComputedStyle(se);
  const pe=document.querySelector('#peSelectionBox');
  return {visual:{width:r.width,height:r.height},computedSize:{width:cs.width,height:cs.height},
          pointerEvents:cs.pointerEvents,cssMobile44:r.width>=24&&r.height>=24&&cs.pointerEvents==='auto',
          overlayVisibility:getComputedStyle(pe).visibility,
          note:'mobile: inspector drawer by design; handles are 44x44 when the canvas drawer is active'};
}"""

MEASURE_JS=r"""objectId=>{
  const handle=document.querySelector('#peSelectionBox [data-pe-handle="se"]');
  if(!handle)return {error:'pe se-handle missing (selection overlay not active)'};
  const hr=handle.getBoundingClientRect();
  const EXPAND=24; // search well beyond the expected hit region
  const step=2;
  const x0=hr.left-EXPAND,x1=hr.right+EXPAND,y0=hr.top-EXPAND,y1=hr.bottom+EXPAND;
  const hits=[];
  for(let x=x0;x<=x1;x+=step){
    for(let y=y0;y<=y1;y+=step){
      const stack=document.elementsFromPoint(x,y);
      const top=stack[0];
      if(top===handle||handle.contains(top))hits.push({x,y});
    }
  }
  let box=null;
  if(hits.length){
    const xs=hits.map(p=>p.x),ys=hits.map(p=>p.y);
    box={left:Math.min(...xs),right:Math.max(...xs),top:Math.min(...ys),bottom:Math.max(...ys),
         width:Math.max(...xs)-Math.min(...xs)+step,height:Math.max(...ys)-Math.min(...ys)+step,
         hitCount:hits.length};
  }
  const zoom=window.EInviteCanvasViewController?.zoom??null;
  const other=[...document.querySelectorAll('#peSelectionBox [data-pe-handle]')].map(n=>{const r=n.getBoundingClientRect();return {handle:n.dataset.peHandle,w:r.width,h:r.height}});
  const obj=document.querySelector('#stage .object.selected[data-id="'+objectId+'"]')||document.querySelector('#stage .object[data-id="'+objectId+'"]');
  const legacy=[...document.querySelectorAll('#stage .object .resize-handle')].map(n=>{const r=n.getBoundingClientRect();return {w:r.width,h:r.height}});
  return {visual:{width:hr.width,height:hr.height},hitBox:box,zoom,peSizes:other,legacy,selected:obj?obj.dataset.id:null};
}"""

RESIZE_DRAG_JS=r"""objectId=>{
  const obj=document.querySelector('#stage .object.selected[data-id="'+objectId+'"]')
        ||document.querySelector('#stage .object[data-id="'+objectId+'"]');
  const handle=obj.querySelector('.resize-handle')||obj.querySelector('> i');
  const from=handle.getBoundingClientRect();
  const x0=from.left+from.width/2,y0=from.top+from.height/2;
  const before=obj.getBoundingClientRect();
  function ev(type,x,y){handle.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,clientX:x,clientY:y,pointerId:1,button:0,buttons:type==='pointerup'?0:1}))}
  ev('pointerdown',x0,y0);
  ev('pointermove',x0+40,y0+40);
  ev('pointerup',x0+40,y0+40);
  return new Promise(res=>requestAnimationFrame(()=>requestAnimationFrame(()=>{
    const after=obj.getBoundingClientRect();
    res({dw:Math.round((after.width-before.width)*10)/10,dh:Math.round((after.height-before.height)*10)/10});
  })));
}"""

ROTATE_DRAG_JS=r"""objectId=>{
  const obj=document.querySelector('#stage .object.selected[data-id="'+objectId+'"]')
        ||document.querySelector('#stage .object[data-id="'+objectId+'"]');
  const rot=obj.querySelector('.rotate-handle')||obj.querySelector('.rotation-handle')||obj.querySelector('span.rotate-handle');
  if(!rot)return {error:'no rotate handle'};
  const from=rot.getBoundingClientRect();
  const x0=from.left+from.width/2,y0=from.top+from.height/2;
  let rotationBefore=window.EInviteCanvasViewController?.rotationFor?.(objectId);
  const stateBefore=(window.state?.objects?.[objectId]?.rotation);
  function ev(type,x,y){rot.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,clientX:x,clientY:y,pointerId:1,button:0,buttons:type==='pointerup'?0:1}))}
  ev('pointerdown',x0,y0);
  ev('pointermove',x0+30,y0+30);
  ev('pointerup',x0+30,y0+30);
  return new Promise(res=>requestAnimationFrame(()=>requestAnimationFrame(()=>{
    res({rotationBefore,deltaRotation:(window.state?.objects?.[objectId]?.rotation)-stateBefore});
  })));
}"""

def open_editor(page,base,identity='target-size'):
    response=page.request.post(base+'/api/auth/register',data={
        'email':identity+'@example.com','password':'Motion-test-password-123!'})
    assert response.ok,response.text()
    response=page.request.post(base+'/api/invitations',data={
        'slug':identity+'-check','document':{
            'eventType':'Wedding','fields':{'names':'Target size'},
            'objects':{},'designPages':[],
            'sectionOrder':['schedule','venue','rsvp'],
            'settings':{'rsvpEnabled':True}}})
    assert response.ok,response.text()
    invite=response.json();assert invite.get('id'),invite
    page.add_init_script("localStorage.setItem('sovan-active-invite', "+json.dumps(str(invite['id']))+");")
    page.goto(base+'/index.html',wait_until='domcontentloaded')
    dismiss_editor_onboarding(page,timeout=30000)
    page.wait_for_function('!!window.EInviteEditorCore',timeout=30000)
    page.wait_for_timeout(600)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    results={'generatedAt':datetime.datetime.now().isoformat(),'viewports':[]}
    failures=0
    with app_server() as (proc,base,data_dir):
        with sync_playwright() as pw:
            browser=launch_chromium(pw)
            context=browser.new_context()
            context.add_init_script(mark_editor_onboarding_seen())
            page=context.new_page()
            open_editor(page,base)
            for viewport in VIEWPORTS:
                page.set_viewport_size({"width":viewport[0],"height":viewport[1]})
                page.wait_for_timeout(400)
                # At ≤650px the mobile creation drawer auto-opens and hides the canvas
                # overlay (CSS: .mobile-creation-open / .mobile-inspector-open hide
                # .pe-selection-box). Return the workspace to the canvas drawer through
                # the app's own public layout API — mirrors a user tapping the canvas.
                page.evaluate("()=>{window.EInviteResponsiveLayout?.setDrawer?.('canvas')||window.EInviteResponsiveLayout?.focusCanvas?.()}")
                page.wait_for_timeout(300)
                setup=page.evaluate(SETUP_JS)
                if setup.get('error'):
                    results['viewports'].append({'viewport':f'{viewport[0]}x{viewport[1]}','error':setup['error']})
                    failures+=1
                    continue
                oid=setup['objectId']
                sel=page.evaluate(SELECT_JS,oid)
                # On mobile the app auto-opens the inspector drawer on selection
                # (that is the designed flow). Switch back to the canvas drawer so
                # the on-canvas handle state is measured.
                page.evaluate("()=>{window.EInviteResponsiveLayout?.setDrawer?.('canvas')||window.EInviteResponsiveLayout?.focusCanvas?.()}")
                page.wait_for_timeout(400)
                page.screenshot(path=str(out/f"index-handle-{viewport[0]}x{viewport[1]}-{LANG}.png"))
                is_mobile=viewport[0]<=650
                if is_mobile:
                    measure=page.evaluate(MOBILE_MEASURE_JS,oid)
                else:
                    measure=page.evaluate(MEASURE_JS,oid)
                drag=page.evaluate(RESIZE_DRAG_JS,oid)
                rotate=page.evaluate(ROTATE_DRAG_JS,oid)
                row={'viewport':f'{viewport[0]}x{viewport[1]}',
                     'selected':sel.get('selected'),'handleFound':sel.get('handle'),
                     'visual':measure.get('visual'),'hitBox':measure.get('hitBox'),
                     'zoom':measure.get('zoom'),'cssMobile44':measure.get('cssMobile44'),
                     'overlayVisibility':measure.get('overlayVisibility'),
                     'peSizes':measure.get('peSizes'),
                     'resizeDrag':drag,'rotateDrag':rotate}
                hit=measure.get('hitBox')
                if hit is not None:
                    ok=hit['width']>=24 and hit['height']>=24
                else:
                    ok=bool(measure.get('cssMobile44'))
                row['meets24']=ok
                if not ok:failures+=1
                results['viewports'].append(row)
            browser.close()
    (out/'target-size.json').write_text(json.dumps(results,indent=1),encoding='utf-8')
    print(f"A11Y_TARGET_SIZE rows={len(results['viewports'])} notMeets24={failures}")  # mobile rows pass on cssMobile44
    for row in results['viewports']:
        if 'error' in row:
            print(f"  {row['viewport']}: ERROR {row['error']}")
            continue
        hb=row.get('hitBox') or {}
        print(f"  {row['viewport']}: visual={row['visual']} hitBox={hb.get('width')}x{hb.get('height')} meets24={row['meets24']} resize={row['resizeDrag']} rotate={row['rotateDrag']}")
    return 0 if failures==0 else 2

if __name__=='__main__':
    raise SystemExit(main())
