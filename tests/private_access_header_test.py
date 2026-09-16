#!/usr/bin/env python3
"""Verify private invitation credentials use headers and sensitive log paths are redacted."""
from __future__ import annotations
import os,sys,tempfile
from pathlib import Path
from route_bundle_sources import has
ROOT=Path(__file__).resolve().parents[1]
os.environ['EINVITE_DATA_DIR']=tempfile.mkdtemp(prefix='einvite-private-access-')
sys.path.insert(0,str(ROOT))
import server  # noqa:E402

def run():
    redacted=server.redact_request_path('/api/public/wedding?g=guest-secret&access=access-secret&safe=1&token=reset-secret')
    assert 'guest-secret' not in redacted and 'access-secret' not in redacted and 'reset-secret' not in redacted
    assert 'safe=1' in redacted and redacted.count('[redacted]')==3,redacted
    public_html=(ROOT/'public.html').read_text(encoding='utf-8')
    public=(ROOT/'public-page.js').read_text(encoding='utf-8')
    assert has('public.html','public-page.js')
    assert "headers['X-Invitation-Access']=accessToken" in public
    assert "headers['X-Invitation-Guest']=guestToken" in public
    assert "params.set('access'" not in public
    assert "url.searchParams.delete('g')" in public
    print('PRIVATE_ACCESS_HEADER_TEST_PASSED')

if __name__=='__main__':run()
