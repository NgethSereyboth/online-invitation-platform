#!/usr/bin/env python3
"""a11y-focus-obscured.py — NW-1.1 measurement harness (WCAG 2.4.11 Focus Not Obscured, Minimum).

For each keyboard-focusable control on index.html (top-bar buttons, rail buttons, context
toolbar controls, inspector tabs/inputs, #saveState, canvas-viewport controls) at four
viewports (1440x900, 1024x768, 768x1024, 375x667):

  1. `el.focus()` — the browser scrolls the control into view honouring any
     scroll-padding/scroll-margin (the CSS surface the NW-1.1 fix may adjust).
  2. Sample three points of the focused box (top/centre/bottom) via elementsFromPoint.
  3. A point is COVERED when the top-most element is neither the control nor a descendant
     of it, and an ancestor of the covering element is position:fixed/sticky.
     FULLY OBSCURED = every in-viewport sample point is covered.

Writes JSON + failure screenshots under --out/. Read-only against the page (focus changes
only), so the same harness is the before/after regression check.

Run through the repo venv: .venv/bin/python tools/a11y-focus-obscured.py --out ...
The dev server comes from tests/v14_test_utils.app_server (real backend, throwaway data dir).
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
MAX_CONTROLS=80
LANG="en"

TARGET_CONTAINERS=[
    'header button','header input','header select',
    '#saveState',
    'aside.rail button','aside.left button','aside.left input','aside.left select',
    'aside.right button','aside.right input','aside.right select',
    '#canvasViewport .v20-context-toolbar button','#canvasViewport .v20-context-toolbar input','#canvasViewport .v20-context-toolbar select',
    '#typographyControls button','#typographyControls input','#typographyControls select',
    '#advancedTextLayout button','#advancedTextLayout input','#advancedTextLayout select',
    '.v22-rail button','.v20-zoom-cluster button','.zoom-cluster button',
]

TARGET_COLLECTION_JS=r"""containers=>{
 const seen=[],controls=[];
 let marker=0;
 for(const container of document.querySelectorAll(containers)){
  let el=container;
  if(!el.matches('button,input,select,textarea,a[href],[tabindex]'))
   el=container.querySelector('button,input,select,textarea,a[href],[tabindex]');
  if(!el||el.disabled)continue;
  const r=el.getBoundingClientRect();
  if(!(r.width>0&&r.height>0))continue;
  const id='fp'+(++marker);el.dataset.focusProbe=id;
  el.dataset.focusProbe=id;
  const path=[];let node=el;
  while(node&&node!==document.body){
   let name=String(node.tagName).toLowerCase();
   if(node.id)name+='#'+node.id;
   else if(typeof node.className==='string'&&node.className.trim())name+='.'+node.className.trim().split(/\s+/).slice(0,2).join('.');
   path.push(name);node=node.parentElement;
  }
  const key=path.slice(0,3).join('>');
  if(seen.includes(key))continue;seen.push(key);
  if(controls.length>=%d)break;
  controls.push({slot:id,css:path});
 }
 return controls}"""%MAX_CONTROLS

PROBE_JS=r"""ctl=>{
  const el=document.querySelector('[data-focus-probe="'+ctl.slot+'"]');
  if(!el)return null;
  el.focus({preventScroll:false});
  return new Promise(resolve=>{
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      // NW-1.1 artifact guard: a control that cannot actually receive focus
      // (display:none / collapsed drawer / zero-size at this viewport) must NOT be
      // counted as obscured — browsers do not scroll to it and focus() is a no-op.
      if(document.activeElement!==el)return resolve({focusLost:true,visible:false});
      const r=el.getBoundingClientRect();
      if(!(r.width>=4&&r.height>=4))return resolve({zeroSize:true,visible:false});
      const cs=getComputedStyle(el);
      const points=[
        {label:'top',x:r.left+r.width/2,y:r.top+1},
        {label:'center',x:r.left+r.width/2,y:r.top+r.height/2},
        {label:'bottom',x:r.left+r.width/2,y:r.bottom-1}];
      const classify=p=>{
        if(p.x<0||p.y<0||p.x>=innerWidth||p.y>=innerHeight)
          return {label:p.label,x:p.x,y:p.y,state:'offscreen'};
        const stack=document.elementsFromPoint(p.x,p.y);
        const top=stack[0]||null;
        let hit=top&&(top===el||el.contains(top));
        if(!hit&&top&&el.contains(top)&&getComputedStyle(top).pointerEvents==='none')hit=true;
        let cover=null;
        const topName=top?String(top.tagName).toLowerCase()+(top.id?'#'+top.id:''):null;
        if(!hit&&top){
          let node=top;
          while(node&&node!==document.documentElement){
            const pos=getComputedStyle(node).position;
            if(pos==='fixed'||pos==='sticky'){
              cover=String(node.tagName).toLowerCase()+(node.id?'#'+node.id:'')+'('+pos+')';
              break;
            }
            node=node.parentElement;
          }
        }
        return {label:p.label,x:p.x,y:p.y,state:hit?'visible':'covered',top:topName,cover};
      };
      const samples=points.map(classify);
      const inViewport=samples.filter(s=>s.state==='covered'||s.state==='visible');
      const coveredCount=inViewport.filter(s=>s.state==='covered').length;
      const fullyObscured=inViewport.length>0&&coveredCount===inViewport.length&&inViewport.length>=2;
      const visible=!el.hidden&&cs.visibility!=='hidden'&&cs.display!=='none';
      resolve({visible,fullyObscured,coveredTopCount:coveredCount,samples});
    }));
  });
}"""

def open_editor(page, base, identity='focus-a11y'):
    """Register a throwaway account + invitation and land in the editor.
    Mirrors tests/canvas_motion_playwright.open_editor so the editor boots the full stack."""
    response=page.request.post(base+'/api/auth/register',data={
        'email':identity+'@example.com','password':'Motion-test-password-123!'})
    assert response.ok,response.text()
    response=page.request.post(base+'/api/invitations',data={
        'slug':identity+'-check','document':{
            'eventType':'Wedding','fields':{'names':'Focus a11y'},
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
    ap.add_argument('--themes',default='light,dark')
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    themes=[t.strip() for t in args.themes.split(',') if t.strip()]
    results={'generatedAt':datetime.datetime.now().isoformat(),'viewports':[]}
    with app_server() as (process,base,data_dir):
        with sync_playwright() as pw:
            browser=launch_chromium(pw)
            context=browser.new_context()
            context.add_init_script(mark_editor_onboarding_seen())
            page=context.new_page()
            open_editor(page,base)
            for viewport in VIEWPORTS:
                for theme in themes:
                    page.set_viewport_size({"width":viewport[0],"height":viewport[1]})
                    page.emulate_media(color_scheme=theme)
                    page.wait_for_timeout(400)
                    controls=page.evaluate(TARGET_COLLECTION_JS,TARGET_CONTAINERS)
                    rows=[];shots=0
                    for ctl in controls:
                        probe=page.evaluate(PROBE_JS,ctl)
                        if probe is None:
                            rows.append({'selector':' > '.join(ctl['css']),'viewport':f"{viewport[0]}x{viewport[1]}",'theme':theme,'skipped':'missing'})
                            continue
                        if not probe.get('visible'):
                            reason='focus-lost (not actually focusable here)' if probe.get('focusLost') else 'zero-size/hidden at probe time'
                            rows.append({'selector':' > '.join(ctl['css']),'viewport':f"{viewport[0]}x{viewport[1]}",'theme':theme,'skipped':reason})
                            continue
                        row={'selector':' > '.join(ctl['css']),
                             'viewport':f"{viewport[0]}x{viewport[1]}",'theme':theme,
                             'fullyObscured':probe['fullyObscured'],
                             'coveredTopCount':probe['coveredTopCount'],
                             'samples':probe['samples']}
                        rows.append(row)
                        if probe['fullyObscured'] and shots<8:
                            page.screenshot(path=str(out/f"index-focus-{viewport[0]}x{viewport[1]}-{theme}-{LANG}-{shots:02d}.png"))
                            shots+=1
                    obscured=[r for r in rows if r.get('fullyObscured')]
                    results['viewports'].append({'viewport':f"{viewport[0]}x{viewport[1]}",'theme':theme,
                                                 'controls':sum(1 for r in rows if 'fullyObscured' in r),
                                                 'fullyObscured':len(obscured),'rows':rows,'screenshots':shots})
            browser.close()
    (out/'focus.json').write_text(json.dumps(results,indent=1),encoding='utf-8')
    total=sum(v['fullyObscured'] for v in results['viewports'])
    print(f"A11Y_FOCUS_OBSCURED controls_scanned={sum(v['controls'] for v in results['viewports'])} fullyObscuredRows={total}")
    for v in results['viewports']:
        print(f"  {v['viewport']} {v['theme']}: controls={v['controls']} fullyObscured={v['fullyObscured']}")
    return 0 if total==0 else 2

if __name__=='__main__':
    raise SystemExit(main())
