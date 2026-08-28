from __future__ import annotations
import json,time,uuid,threading

class Observability:
    def __init__(self,connect,json_logs=False):self.connect=connect;self.json_logs=json_logs;self.started=time.time();self._lock=threading.Lock();self._counters={}
    def request_id(self,value=''):return str(value or uuid.uuid4())[:100]
    def log(self,level,event,request_id='',**fields):
        safe={k:v for k,v in fields.items() if not any(token in k.lower() for token in ('password','token','secret','cookie','document','content','guest'))}
        payload={'timestamp':int(time.time()*1000),'level':level,'event':event,'requestId':request_id,**safe}
        print(json.dumps(payload,ensure_ascii=False,separators=(',',':')) if self.json_logs else f"[{level}] {event} request={request_id} {safe}",flush=True)
    def increment(self,name,value=1,tags=None,workspace_id=''):
        with self._lock:self._counters[name]=self._counters.get(name,0)+value
        try:
            with self.connect() as db:db.execute("INSERT INTO operational_metrics(id,workspace_id,name,value,tags_json,created_at) VALUES(?,?,?,?,?,?)",(str(uuid.uuid4()),workspace_id,name,float(value),json.dumps(tags or {},separators=(',',':')),int(time.time()*1000)))
        except Exception:pass
    def snapshot(self):
        with self._lock:counters=dict(self._counters)
        return {'uptimeSeconds':int(time.time()-self.started),'counters':counters}
