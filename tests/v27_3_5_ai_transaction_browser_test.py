#!/usr/bin/env python3
"""Atomic AI document actions and exact one-step history coverage."""
from __future__ import annotations
from browser_runtime import launch_chromium,skipped
from v27_3_5_ai_test_support import ready
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V27_3_5_AI_TRANSACTION_BROWSER',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V27_3_5_AI_TRANSACTION_BROWSER',exc)
  page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));ready(page)
  result=page.evaluate("""async()=>{
    const S=EInviteAIActionService,B=EInviteEditorBridge;B.select(['title']);const context=S.captureContext(),before=S.fingerprint(B.getState()),beforeText=B.getState().objects.title.text;
    const preview=await S.preview([{type:'replaceText',targetIds:['title'],text:'A single reversible title',mode:'preserve'}],{context});if(!preview.ok)throw Error(JSON.stringify(preview));
    S.commit([{type:'replaceText',targetIds:['title'],text:'A single reversible title',mode:'preserve'}],{context,label:'AI title'});const after=S.fingerprint(B.getState()),afterText=B.getState().objects.title.text;await new Promise(resolve=>requestAnimationFrame(resolve));const selectionAfterReplace=B.getSelectedIds();B.undo();const undo=S.fingerprint(B.getState()),undoText=B.getState().objects.title.text;B.redo();const redo=S.fingerprint(B.getState()),redoText=B.getState().objects.title.text;
    const batchContext=S.captureContext(),batchBefore=S.fingerprint(B.getState());S.commit([{type:'updateMessage',field:'message',text:'Batch message'},{type:'addText',text:'Batch text'},{type:'applyPalette',colors:['#112233','#445566','#778899']}],{context:batchContext,label:'AI batch'});const batchAfter=S.fingerprint(B.getState()),created=Object.keys(B.getState().objects).length;B.undo();const batchUndo=S.fingerprint(B.getState());B.redo();const batchRedo=S.fingerprint(B.getState());
    const failBefore=S.fingerprint(B.getState());let failed=false;try{S.commit([{type:'updateMessage',text:'partial'},{type:'unknownAction'}],{context:S.captureContext(),label:'Fail batch'})}catch(e){failed=true}const failAfter=S.fingerprint(B.getState());
    const clone=B.cloneState(),runtime={canvasId:'hero',targetIds:['title','subtitle'],createdIds:[],createdGroupIds:[],createdPageIds:[]};S.applyActions(clone,[{type:'createObject',objectType:'shape',object:{left:'5%',top:'5%',width:'12%',height:'12%',fill:'#123456'}},{type:'duplicateObjects',targetIds:['title']},{type:'groupObjects',targetIds:['title','subtitle']},{type:'arrange',targetIds:['title'],position:'front'},{type:'resize',targetIds:['title'],patch:{width:'80%',height:'130px'}},{type:'ungroupObjects',targetIds:['title','subtitle']},{type:'photoPreset',targetIds:['hero'],preset:'enhance'},{type:'updateMessage',field:'messageKm',locale:'km',text:'សារសាកល្បង'},{type:'applySchedule',schedule:[{time:'4:00 PM',title:'Arrival',titleKm:'មកដល់'}]},{type:'deleteObjects',targetIds:['details']}],runtime);const roundTrip=S.fingerprint(JSON.parse(JSON.stringify(B.getState())))===S.fingerprint(B.getState());
    return{before,after,undo,redo,selectionAfterReplace,beforeText,afterText,undoText,redoText,batchBefore,batchAfter,batchUndo,batchRedo,created,failed,failBefore,failAfter,roundTrip,ops:{detailsGone:!clone.objects.details,photo:clone.objects.hero.imageContrast,width:clone.objects.title.width,groups:Object.keys(clone.sceneGraph?.groups||{}).length,shapeCreated:runtime.createdIds.some(id=>clone.objects[id]?.type==='shape'),messageKm:clone.fields.messageKm,schedule:clone.schedule}};
  }""")
  assert result['after']!=result['before'] and result['undo']==result['before'] and result['redo']==result['after'],result
  assert result['selectionAfterReplace']==['title'],result
  assert result['undoText']==result['beforeText'] and result['redoText']==result['afterText'],result
  assert result['batchAfter']!=result['batchBefore'] and result['batchUndo']==result['batchBefore'] and result['batchRedo']==result['batchAfter'],result
  assert result['failed'] and result['failBefore']==result['failAfter'],result
  assert result['roundTrip'] and result['ops']['detailsGone'] and result['ops']['width']=='80%' and result['ops']['photo']>100,result
  assert result['ops']['shapeCreated'] and result['ops']['messageKm']=='សារសាកល្បង' and result['ops']['schedule'][0]['titleKm']=='មកដល់',result
  assert not errors,errors;browser.close()
 print('V27_3_5_AI_TRANSACTION_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
