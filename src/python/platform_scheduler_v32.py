"""Provider-ready local scheduler role for V32 development deployments."""
from __future__ import annotations
import signal,threading,time,json
from server import connect,process_due_studio_backups,process_scheduled_publications,process_scheduled_campaigns,cleanup_expired_security_rows,cleanup_upload_sessions,process_storage_delete_jobs,get_platform_v32_service
stop=threading.Event()
def request_stop(*_):stop.set()
for sig in (getattr(signal,'SIGTERM',None),getattr(signal,'SIGINT',None),getattr(signal,'SIGBREAK',None)):
    if sig is not None:
        try:signal.signal(sig,request_stop)
        except (ValueError,OSError):pass
service=get_platform_v32_service();interval=max(30,int(__import__('os').environ.get('EINVITE_SCHEDULER_INTERVAL_SECONDS','60')))
print(f'EInvite V32 scheduler started; interval={interval}s.',flush=True)
while not stop.is_set():
    try:
        process_due_studio_backups(limit=10);process_scheduled_publications();process_scheduled_campaigns();cleanup_expired_security_rows();cleanup_upload_sessions();process_storage_delete_jobs(limit=100)
        with connect() as db:
            now=int(time.time()*1000);db.execute("DELETE FROM idempotency_records WHERE expires_at<?",(now,));db.execute("UPDATE upload_sessions_v32 SET status='expired',updated_at=? WHERE expires_at<? AND status IN ('pending','uploading')",(now,now))
    except Exception as exc:print(json.dumps({'level':'warning','event':'scheduler_iteration_failed','message':str(exc)}),flush=True)
    stop.wait(interval)
service.jobs.shutdown(timeout=5)
