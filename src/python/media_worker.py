#!/usr/bin/env python3
"""Small background worker for media derivatives and social-card cache warming.

Local development remains synchronous by default. Set EINVITE_BACKGROUND_MEDIA=1 and
run this worker in production to move expensive media work out of request threads.
"""
from __future__ import annotations
import argparse, json, os, signal, time
import server

STOP=False

def _stop(*_):
    global STOP; STOP=True

def run_job(job):
    kind=job['kind']; payload=job.get('payload') or {}
    if kind=='image.derivatives':
        server.pre_generate_common_derivatives(payload['path'],payload.get('mime',''),payload.get('sha256',''))
    elif kind=='social.warm':
        server.warm_social_card_cache(payload['invitationId'],payload.get('accessMode','unlisted'),int(payload.get('version') or 0),payload.get('document') or {})
    elif kind=='social.guest_warm':
        # Goal 5c (research §5.4): one card per guest. The document and version
        # are read at run time rather than carried in the payload, so a job that
        # waited in the queue still warms the newest publication.
        published=server.latest_published_document(payload['invitationId'])
        if published:server.warm_guest_social_cards(payload['invitationId'],published['accessMode'],published['version'],published['document'])
    elif kind=='maintenance.cleanup':
        server.cleanup_expired_security_rows()
    elif kind=='storage.delete':
        server.delete_stored_asset(payload.get('path',''),payload.get('sha256',''))
    elif kind.startswith('admin.bulk_'):
        # ROADMAP Part 5 §5.7 — queued admin bulk operations (email/suspend/
        # export/prune) run out of the request thread like every other job.
        server.process_admin_bulk_job(kind,payload)
    else:
        raise ValueError(f'Unsupported background job kind: {kind}')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');parser.add_argument('--poll',type=float,default=1.5);args=parser.parse_args()
    signal.signal(signal.SIGINT,_stop);signal.signal(signal.SIGTERM,_stop)
    while not STOP:
        job=server.claim_background_job()
        if not job:
            if args.once:return 0
            time.sleep(max(.2,args.poll));continue
        try:
            run_job(job);server.complete_background_job(job['id'])
            print(json.dumps({'job':job['id'],'kind':job['kind'],'status':'done'}),flush=True)
        except Exception as exc:
            server.fail_background_job(job['id'],exc,retry=True)
            print(json.dumps({'job':job['id'],'kind':job['kind'],'status':'failed','error':str(exc)}),flush=True)
        if args.once:return 0
    return 0

if __name__=='__main__':raise SystemExit(main())
