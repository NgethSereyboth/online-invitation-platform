#!/usr/bin/env python3
"""Current V28 agent mobile dialog, focus, geometry, cancellation, and lifecycle coverage."""
from __future__ import annotations
from pathlib import Path
from browser_runtime import launch_chromium,skipped
from v27_3_5_ai_test_support import ready
ROOT=Path(__file__).resolve().parents[1]
SIZES=[(360,800),(390,844),(430,932)]
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V27_3_5_AI_ACCESSIBILITY_MOBILE',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V27_3_5_AI_ACCESSIBILITY_MOBILE',exc)
  page=browser.new_page();page.set_default_timeout(12000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));ready(page,390,844)
  page.evaluate("""()=>{const b=document.createElement('button');b.id='currentAiOpener';b.textContent='Open agent';document.body.append(b);window.EInviteContext={getInvitationId:()=> 'invite-1'};window.EInviteBackend={isAvailable:()=>false,ready:Promise.resolve()}}""")
  page.add_style_tag(content=(ROOT/'ai-creative-agent-v28.css').read_text(encoding='utf-8'))
  page.add_script_tag(content=(ROOT/'ai-agent-tool-registry-v28.js').read_text(encoding='utf-8'))
  page.add_script_tag(content=(ROOT/'ai-creative-agent-v28.js').read_text(encoding='utf-8'))
  opener=page.locator('#currentAiOpener');baseline=page.evaluate("()=>[...document.body.children].filter(e=>e.id!=='eiAgentPanel'&&e.inert).length")
  for width,height in SIZES:
   page.set_viewport_size({'width':width,'height':height});opener.focus();page.evaluate("()=>EInviteAICreativeAgent.open('write',{opener:document.querySelector('#currentAiOpener')})")
   panel=page.locator('#eiAgentPanel');panel.wait_for(state='visible');page.wait_for_timeout(80)
   data=page.evaluate("""()=>{const d=document.querySelector('#eiAgentPanel'),r=d.getBoundingClientRect(),controls=[...d.querySelectorAll('button,select,textarea')].filter(e=>e.offsetParent&&!e.disabled).map(e=>{const x=e.getBoundingClientRect();return{x:x.width,y:x.height}});return{role:d.getAttribute('role'),modal:d.getAttribute('aria-modal'),labelled:d.getAttribute('aria-labelledby'),described:d.getAttribute('aria-describedby'),left:r.left,right:r.right,overflow:document.documentElement.scrollWidth-innerWidth,controls,inert:[...document.body.children].filter(e=>e!==d&&e.inert).length,active:document.activeElement?.matches('[data-agent-input]')}}""")
   assert data['role']=='dialog' and data['modal']=='true' and data['labelled'] and data['described'],data
   assert data['overflow']<=.5 and data['left']>=-.5 and data['right']<=width+.5,data
   assert all(c['x']>=43.5 and c['y']>=43.5 for c in data['controls']),data['controls']
   assert data['inert']>0 and data['active'],data
   page.keyboard.press('Escape');page.wait_for_function("()=>document.querySelector('#eiAgentPanel')?.dataset.open==='false'");page.wait_for_function("()=>document.activeElement?.id==='currentAiOpener'")
   assert page.evaluate("()=>[...document.body.children].filter(e=>e.id!=='eiAgentPanel'&&e.inert).length")==baseline
  # A connected request is aborted by close and does not duplicate the panel.
  page.evaluate('()=>EInviteAICreativeAgent.destroy()');page.close()
  page=browser.new_page(viewport={'width':390,'height':844});page.set_default_timeout(12000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_content('<button id="currentAiOpener">Open agent</button><div id="stage" tabindex="0"></div>')
  page.evaluate("""()=>{window.__aiAborted=false;document.documentElement.dataset.serverConnected='true';window.EInviteContext={getInvitationId:()=> 'invite-1'};window.EInviteBackend={isAvailable:()=>true,ready:Promise.resolve()};window.fetch=(url,opt={})=>{if(String(url).includes('/messages'))return new Promise((resolve,reject)=>opt.signal.addEventListener('abort',()=>{window.__aiAborted=true;reject(new DOMException('Aborted','AbortError'))},{once:true}));if(String(url).includes('/ai-agent/status'))return Promise.resolve(new Response(JSON.stringify({providerMode:'fake',providerDisclosure:'Fake provider',preferences:{enabled:true,retentionDays:0}}),{status:200,headers:{'Content-Type':'application/json'}}));if(String(url).endsWith('/ai/threads'))return Promise.resolve(new Response(JSON.stringify({threads:[{id:'thread-1',title:'Test'}]}),{status:200,headers:{'Content-Type':'application/json'}}));return Promise.resolve(new Response(JSON.stringify({id:'thread-1',title:'Test',messages:[]}),{status:200,headers:{'Content-Type':'application/json'}}))}}""")
  page.add_style_tag(content=(ROOT/'ai-creative-agent-v28.css').read_text(encoding='utf-8'));page.add_script_tag(content=(ROOT/'ai-agent-tool-registry-v28.js').read_text(encoding='utf-8'));page.add_script_tag(content=(ROOT/'ai-creative-agent-v28.js').read_text(encoding='utf-8'))
  page.evaluate("()=>EInviteAICreativeAgent.open('write',{opener:document.querySelector('#currentAiOpener')})")
  page.locator('[data-agent-input]').fill('Test cancellation');page.locator('[data-agent-action=send]').click();page.wait_for_function("()=>document.querySelector('#eiAgentPanel').dataset.busy==='true'");page.evaluate('()=>EInviteAICreativeAgent.close()');page.wait_for_function('()=>window.__aiAborted===true')
  assert page.locator('#eiAgentPanel').count()==1;page.evaluate('()=>EInviteAICreativeAgent.destroy()');assert page.locator('#eiAgentPanel').count()==0
  assert not errors,errors;browser.close()
 print('V27_3_5_AI_ACCESSIBILITY_MOBILE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
