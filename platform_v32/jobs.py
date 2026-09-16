from __future__ import annotations
import json,time,uuid,threading,queue

class JobQueue:
    def __init__(self,connect,workers=2,audit=None,poll_interval=.75):
        self.connect=connect;self.workers=max(0,min(32,int(workers)));self.audit=audit;self.handlers={};self.queue=queue.Queue(maxsize=10000);self.threads=[];self.stopping=False;self.poll_interval=max(.1,min(10,float(poll_interval)));self._start()
    def _start(self):
        for index in range(self.workers):
            thread=threading.Thread(target=self._worker,name=f'einvite-worker-{index+1}',daemon=True);thread.start();self.threads.append(thread)
    def register(self,kind,handler):self.handlers[str(kind)]=handler
    def submit(self,workspace_id,owner_id,kind,payload,invitation_id='',idempotency_key='',max_retries=3):
        encoded=json.dumps(payload or {},ensure_ascii=False,separators=(',',':'))
        if len(encoded.encode())>1_000_000:raise ValueError('Job payload exceeds 1 MB')
        now=int(time.time()*1000)
        with self.connect() as db:
            if idempotency_key:
                row=db.execute("SELECT id,status FROM platform_jobs WHERE workspace_id=? AND idempotency_key=?",(workspace_id,idempotency_key[:160])).fetchone()
                if row:return {'id':row['id'],'status':row['status'],'idempotent':True}
            job_id=str(uuid.uuid4());db.execute("INSERT INTO platform_jobs(id,workspace_id,invitation_id,owner_id,kind,status,progress,payload_json,result_json,idempotency_key,retry_count,max_retries,cancellation_requested,error_text,created_at,updated_at) VALUES(?,?,?,?,?,'queued',0,?,'{}',?,0,?,0,'',?,?)",(job_id,workspace_id,invitation_id,owner_id,kind[:80],encoded,idempotency_key[:160],max(0,min(10,int(max_retries))),now,now))
        try:self.queue.put_nowait(job_id)
        except queue.Full:pass
        return {'id':job_id,'status':'queued','idempotent':False}
    def cancel(self,job_id,owner_id):
        with self.connect() as db:return bool(db.execute("UPDATE platform_jobs SET cancellation_requested=1,status=CASE WHEN status IN ('queued','claimed') THEN 'cancelled' ELSE status END,updated_at=? WHERE id=? AND owner_id=?",(int(time.time()*1000),job_id,owner_id)).rowcount)
    def list(self,workspace_id,limit=50):
        with self.connect() as db:rows=db.execute("SELECT id,kind,status,progress,retry_count,max_retries,error_text,created_at,updated_at,started_at,completed_at FROM platform_jobs WHERE workspace_id=? ORDER BY created_at DESC LIMIT ?",(workspace_id,max(1,min(200,int(limit))))).fetchall()
        return [dict(row) for row in rows]
    def _worker(self):
        while not self.stopping:
            job_id=None
            try:job_id=self.queue.get(timeout=self.poll_interval)
            except queue.Empty:job_id=self._claim_pending()
            if not job_id:continue
            try:self._run(job_id)
            finally:
                try:self.queue.task_done()
                except ValueError:pass
    def _claim_pending(self):
        with self.connect() as db:
            row=db.execute("SELECT id FROM platform_jobs WHERE status='queued' AND cancellation_requested=0 ORDER BY created_at LIMIT 1").fetchone()
            if not row:return None
            now=int(time.time()*1000);changed=db.execute("UPDATE platform_jobs SET status='claimed',updated_at=? WHERE id=? AND status='queued'",(now,row['id'])).rowcount
            return row['id'] if changed else None
    def _run(self,job_id):
        with self.connect() as db:
            row=db.execute("SELECT * FROM platform_jobs WHERE id=?",(job_id,)).fetchone()
            if not row or row['status']=='cancelled':return
            if row['status']=='queued':
                changed=db.execute("UPDATE platform_jobs SET status='claimed',updated_at=? WHERE id=? AND status='queued'",(int(time.time()*1000),job_id)).rowcount
                if not changed:return
            now=int(time.time()*1000);db.execute("UPDATE platform_jobs SET status='running',started_at=COALESCE(started_at,?),updated_at=? WHERE id=? AND status='claimed'",(now,now,job_id));row=db.execute("SELECT * FROM platform_jobs WHERE id=?",(job_id,)).fetchone()
        handler=self.handlers.get(row['kind'])
        if not handler:self._finish(job_id,'failed',{},f"No handler registered for {row['kind']}");return
        try:
            payload=json.loads(row['payload_json'] or '{}');result=handler(payload,lambda progress:self._progress(job_id,progress),lambda:self._cancelled(job_id));self._finish(job_id,'completed',result or {},'')
        except Exception as exc:
            retry=int(row['retry_count'] or 0)+1
            if retry<=int(row['max_retries'] or 0) and not self._cancelled(job_id):
                with self.connect() as db:db.execute("UPDATE platform_jobs SET status='queued',retry_count=?,error_text=?,updated_at=? WHERE id=?",(retry,str(exc)[:1000],int(time.time()*1000),job_id))
                time.sleep(min(5,2**retry))
                try:self.queue.put_nowait(job_id)
                except queue.Full:pass
            else:self._finish(job_id,'cancelled' if self._cancelled(job_id) else 'failed',{},str(exc))
    def _progress(self,job_id,value):
        with self.connect() as db:db.execute("UPDATE platform_jobs SET progress=?,updated_at=? WHERE id=?",(max(0,min(1,float(value))),int(time.time()*1000),job_id))
    def _cancelled(self,job_id):
        with self.connect() as db:row=db.execute("SELECT cancellation_requested,status FROM platform_jobs WHERE id=?",(job_id,)).fetchone();return not row or bool(row['cancellation_requested']) or row['status']=='cancelled'
    def _finish(self,job_id,status,result,error):
        now=int(time.time()*1000)
        with self.connect() as db:db.execute("UPDATE platform_jobs SET status=?,progress=?,result_json=?,error_text=?,completed_at=?,updated_at=? WHERE id=?",(status,1 if status=='completed' else 0,json.dumps(result,ensure_ascii=False,separators=(',',':'))[:1_000_000],str(error)[:2000],now,now,job_id))
    def shutdown(self,timeout=10):
        self.stopping=True;deadline=time.time()+max(0,float(timeout))
        while self.queue.unfinished_tasks and time.time()<deadline:time.sleep(.05)
        for thread in self.threads:thread.join(max(0,deadline-time.time()))
        return not any(thread.is_alive() for thread in self.threads)
