#!/usr/bin/env python3
"""Generated results remain bound to invitation, page, targets, and compatible revision."""
from __future__ import annotations
from browser_runtime import launch_chromium,skipped
from v27_3_5_ai_test_support import ready
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V27_3_5_AI_TARGET_REVISION',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V27_3_5_AI_TARGET_REVISION',exc)
  page=browser.new_page();ready(page)
  out=page.evaluate("""()=>{const B=EInviteEditorBridge,S=EInviteAIActionService;B.select(['title']);const context=S.captureContext({providerMode:'offline'});B.select(['subtitle']);const selectionChanged=S.validateContext(context);B.transact('external change',d=>{d.objects.title.color='#123456';d.objects.title.colorToken='text'});const revisionChanged=S.validateContext(context);let rejected='';try{S.commit([{type:'replaceText',targetIds:['title'],text:'Must not apply'}],{context})}catch(e){rejected=e.code}document.body.dataset.collaborationRole='viewer';const permission=S.validateContext(S.captureContext());delete document.body.dataset.collaborationRole;delete B.getState().objects.title;const missing=S.validateContext({...S.captureContext(),targetObjectIds:['title'],targetFingerprint:context.targetFingerprint});return{context,selectionChanged,revisionChanged,rejected,permission,missing,current:B.getSelectedIds()}}""")
  assert out['context']['invitationId'] and out['context']['canvasId']=='hero' and out['context']['targetObjectIds']==['title'],out
  assert out['selectionChanged']['ok'] is True,out
  assert out['revisionChanged']['ok'] is False and out['rejected'] in {'STALE_REVISION','TARGET_CHANGED'},out
  assert out['permission']['ok'] is False and out['permission']['code']=='PERMISSION',out
  assert out['missing']['ok'] is False,out
  browser.close()
 print('V27_3_5_AI_TARGET_REVISION_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
