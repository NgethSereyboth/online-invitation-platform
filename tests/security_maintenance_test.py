#!/usr/bin/env python3
"""Verify security-row cleanup and the SQLite performance indexes added for V9."""
from __future__ import annotations
import os,sys,tempfile,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['EINVITE_DATA_DIR']=tempfile.mkdtemp(prefix='einvite-maintenance-')
import server  # noqa: E402

EXPECTED_INDEXES={
    'idx_invitations_owner','idx_publications_invitation','idx_rsvps_invitation',
    'idx_assets_invitation','idx_guests_invitation','idx_templates_owner',
    'idx_page_templates_owner','idx_sessions_user','idx_sessions_expiry',
    'idx_access_tokens_invitation','idx_access_tokens_expiry','idx_auth_tokens_expiry',
    'idx_guest_messages_invitation',
}

def run():
    now=int(time.time()*1000)
    uid='u-'+uuid.uuid4().hex
    iid='i-'+uuid.uuid4().hex
    with server.connect() as db:
        db.execute('INSERT INTO users(id,email,password_hash,salt,created_at,role,email_verified,plan) VALUES(?,?,?,?,?,?,?,?)',
                   (uid,'maintenance@example.com','hash','salt',now,'customer',1,'free'))
        db.execute('INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id) VALUES(?,?,?,?,?)',
                   (iid,'maintenance','{}',now,uid))
        db.execute('INSERT INTO sessions(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)',('expired-session',uid,now-1,now-1000))
        db.execute('INSERT INTO sessions(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)',('live-session',uid,now+60_000,now))
        db.execute('INSERT INTO auth_tokens(token_hash,user_id,kind,expires_at,created_at) VALUES(?,?,?,?,?)',('expired-auth',uid,'verify',now-1,now-1000))
        db.execute('INSERT INTO auth_tokens(token_hash,user_id,kind,expires_at,created_at) VALUES(?,?,?,?,?)',('live-auth',uid,'verify',now+60_000,now))
        db.execute('INSERT INTO access_tokens(token_hash,invitation_id,expires_at,created_at) VALUES(?,?,?,?)',('expired-access',iid,now-1,now-1000))
        db.execute('INSERT INTO access_tokens(token_hash,invitation_id,expires_at,created_at) VALUES(?,?,?,?)',('live-access',iid,now+60_000,now))

    result=server.cleanup_expired_security_rows()
    assert result.get('sessions')==1 and result.get('authTokens')==1 and result.get('accessTokens')==1,result
    assert result.get('galleryAccessTokens',0)==0 and result.get('challenges',0)==0 and result.get('purgedUsers',0)==0,result
    with server.connect() as db:
        assert db.execute("SELECT 1 FROM sessions WHERE token_hash='expired-session'").fetchone() is None
        assert db.execute("SELECT 1 FROM auth_tokens WHERE token_hash='expired-auth'").fetchone() is None
        assert db.execute("SELECT 1 FROM access_tokens WHERE token_hash='expired-access'").fetchone() is None
        assert db.execute("SELECT 1 FROM sessions WHERE token_hash='live-session'").fetchone() is not None
        assert db.execute("SELECT 1 FROM auth_tokens WHERE token_hash='live-auth'").fetchone() is not None
        assert db.execute("SELECT 1 FROM access_tokens WHERE token_hash='live-access'").fetchone() is not None
        names=set()
        for table in ('invitations','publications','rsvps','assets','guests','user_templates','user_page_templates','sessions','access_tokens','auth_tokens','guest_messages'):
            names.update(row['name'] for row in db.execute(f'PRAGMA index_list({table})').fetchall())
    missing=EXPECTED_INDEXES-names
    assert not missing,f'Missing SQLite indexes: {sorted(missing)}'

    sample='"GET /i/wedding?g=secret&access=private&foo=1 HTTP/1.1" 200 -'
    redacted=server.redact_request_path(sample)
    assert 'secret' not in redacted and 'private' not in redacted
    assert 'g=[redacted]' in redacted and 'access=[redacted]' in redacted
    print('SECURITY_MAINTENANCE_TEST_PASSED')

if __name__=='__main__':run()
