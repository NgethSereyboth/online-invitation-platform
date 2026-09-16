#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(900)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  for name in ('studio-governance-v25.css','studio-operations-v26.css'):page.add_style_tag(path=str(ROOT/name))
  page.evaluate("""()=>{localStorage.setItem('einvite-v25-studio-resources',JSON.stringify([{id:'brand-v26',kind:'brand',name:'Official Brand',category:'Government',payload:{primary:'#183a64'},governance:{locked:false,allowedOverrides:['content']},status:'approved',version:2,createdAt:Date.now(),updatedAt:Date.now()}]));window.EInviteFeedback=window.EInviteFeedback||{toast:()=>{}};window.__prompts=['August 2026 Release','Controlled government invitation rollout'];window.uiPrompt=async()=>window.__prompts.shift()||'';window.uiConfirm=async()=>true}""")
  page.add_script_tag(path=str(ROOT/'studio-governance-v25.js'));page.wait_for_timeout(120)
  page.add_script_tag(path=str(ROOT/'studio-operations-v26.js'));page.wait_for_timeout(180)
  versions=page.evaluate("()=>({governance:EInviteStudioGovernance.version,operations:EInviteStudioOperations.version,conflicts:EInviteCommandRegistry.conflicts.length})")
  assert versions=={'governance':25.1,'operations':26,'conflicts':0},versions
  created=page.evaluate("()=>EInviteStudioOperations.createRelease()");assert created['status']=='draft' and len(created['manifest'])==1,created
  rid=created['id'];page.evaluate("id=>EInviteStudioOperations.activateRelease(id)",rid);page.wait_for_timeout(120)
  releases=page.evaluate("()=>EInviteStudioOperations.releases()");assert releases[0]['status']=='active',releases
  page.evaluate("()=>{window.__prompts=['August 2026 Release — next']}");cloned=page.evaluate("id=>EInviteStudioOperations.cloneRelease(id)",rid);assert cloned['status']=='draft' and cloned['manifest']==created['manifest'],cloned
  page.evaluate("id=>EInviteStudioOperations.pinRelease(id)",rid);page.wait_for_timeout(80)
  assert page.evaluate("()=>EInviteStudioOperations.pin().release_id") == rid
  page.evaluate("()=>EInviteStudioOperations.open('releases')");page.wait_for_timeout(80)
  assert page.locator('.v26-operations-dialog').is_visible();assert page.locator('.v26-release-card.active').count()==1
  page.locator('.v26-operations-dialog [data-tab="deployment"]').click();page.wait_for_timeout(50);assert page.locator('.v26-health').is_visible()
  page.locator('.v26-operations-dialog [data-close]').first.click()
  compliance=page.evaluate("()=>{localStorage.setItem('einvite-v25-studio-policy',JSON.stringify({requireStudioRelease:true}));return EInviteStudioGovernance.load().then(()=>EInviteStudioGovernance.compliance().map(x=>x.code))}")
  assert 'studio-release-required' not in compliance,compliance
  assert not errors,errors
  browser.close()
 print('V26_STUDIO_OPERATIONS_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
