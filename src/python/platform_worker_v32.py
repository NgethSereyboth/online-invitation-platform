"""Run the durable V32 platform worker role.

Set EINVITE_WORKER_CONCURRENCY to a bounded value greater than zero. The web
process may set it to zero when a separate worker service is used.
"""
from __future__ import annotations
import signal,threading,time
from server import get_platform_v32_service,ensure_platform_schema,connect

stop=threading.Event()
def request_stop(*_):stop.set()
for sig in (getattr(signal,'SIGTERM',None),getattr(signal,'SIGINT',None),getattr(signal,'SIGBREAK',None)):
    if sig is not None:
        try:signal.signal(sig,request_stop)
        except (ValueError,OSError):pass
ensure_platform_schema(connect);service=get_platform_v32_service()
if service.config.job_workers<1:raise SystemExit('Set EINVITE_WORKER_CONCURRENCY to at least 1 for the worker process.')
print(f'EInvite V32 worker started with {service.config.job_workers} bounded worker(s).',flush=True)
try:
    while not stop.wait(1):pass
finally:
    service.jobs.shutdown(timeout=30)
