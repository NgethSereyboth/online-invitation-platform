#!/usr/bin/env python3
from __future__ import annotations
import sqlite3,tempfile,sys
from contextlib import contextmanager
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ai_agent.storage import ensure_agent_schema,AgentStore

def main()->int:
 with tempfile.TemporaryDirectory() as tmp:
  path=Path(tmp)/'agent.sqlite3'
  @contextmanager
  def connect():
   db=sqlite3.connect(path);db.row_factory=sqlite3.Row
   try:yield db;db.commit()
   except Exception:db.rollback();raise
   finally:db.close()
  ensure_agent_schema(connect);store=AgentStore(connect,30)
  prefs=store.update_preferences('u1',{'enabled':True,'retentionDays':7,'allowLowRiskAuto':True,'feedbackLearning':True,'memoryEnabled':True,'knowledgeEnabled':True})
  assert prefs['retentionDays']==7 and prefs['allowLowRiskAuto'] and prefs['feedbackLearning'] and prefs['memoryEnabled'] and prefs['knowledgeEnabled']
  thread=store.create_conversation('invite-1','u1','Wedding plan','fake')
  first=store.add_message(thread['id'],'user','user',{'text':'Hello'})
  second=store.add_message(thread['id'],'assistant','assistant',{'text':'Hi'})
  assert first['sequence']==1 and second['sequence']==2
  loaded=store.get_conversation(thread['id'],'invite-1','u1');assert len(loaded['messages'])==2
  plan=store.create_plan(thread['id'],'invite-1','u1',3,'abc',{'toolCalls':[]},'idem-1')
  same=store.create_plan(thread['id'],'invite-1','u1',3,'abc',{'toolCalls':[]},'idem-1')
  assert same['id']==plan['id']
  job=store.create_job(thread['id'],'invite-1','u1');assert store.cancel_job(job['id'],'invite-1','u1')
  feedback=store.record_feedback('invite-1','u1',second['id'],-1,['tone'],'Prefer concise Khmer wording.',True)
  assert feedback['memory']['kind']=='correction'
  memory=store.create_memory('u1','Use royal gold for wedding invitations.','account','','preference')
  learned=store.learning_context('u1','invite-1','gold wedding invitation')
  assert learned['enabled'] and len(learned['memories'])>=1
  source=store.create_knowledge_source('u1','Khmer ceremony protocol','Use formal Khmer honorifics and list the blessing ceremony before dinner.','invitation','invite-1','policy')
  learned=store.learning_context('u1','invite-1','Khmer blessing ceremony')
  assert learned['knowledge'][0]['title']=='Khmer ceremony protocol'
  assert store.list_knowledge_sources('u1','invite-1')[0]['contentLength']>20
  assert any(item['kind']=='correction' for item in store.learning_context('u1','invite-1','concise Khmer wording')['memories'])
  store.record_plan_outcomes('u1','invite-1',plan['id'],['style.apply_palette'],True)
  learned=store.learning_context('u1','invite-1','gold invitation');assert learned['toolReliability'][0]['toolId']=='style.apply_palette'
  assert store.delete_memory('u1',memory['id'])
  assert store.delete_knowledge_source('u1',source['id'])
 print('V28_AGENT_STORAGE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
