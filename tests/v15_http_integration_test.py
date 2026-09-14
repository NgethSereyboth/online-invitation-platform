#!/usr/bin/env python3
"""Real-HTTP integration coverage for the V15 consolidated frontend."""
from __future__ import annotations
import json
import importlib.util
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

from v14_test_utils import app_server

ROOT=Path(__file__).resolve().parents[1]


def assert_disconnect_safe():
    sys.path.insert(0,str(ROOT))
    spec=importlib.util.spec_from_file_location('einvite_server_v18',ROOT/'server.py');assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    class BrokenWriter:
        def __init__(self,error):self.error=error
        def write(self,_body):raise self.error('client disconnected')
    for error in (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
        handler=module.Handler.__new__(module.Handler);handler.wfile=BrokenWriter(error)
        assert handler.safe_write(b'{}') is False
        handler.send_response=lambda _status,error=error:(_ for _ in ()).throw(error('cancelled before headers'))
        handler.send_header=lambda *_args,**_kwargs:None;handler.end_headers=lambda:None
        assert handler.json(200,{'ok':True}) is False

class Client:
    def __init__(self,base:str):
        self.base=base
        self.jar=CookieJar()
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.token=''
    def request(self,path:str,method='GET',body=None,expected=200,headers=None,parse_json=True):
        payload=None if body is None else json.dumps(body).encode('utf-8')
        hdr={'Accept':'application/json' if parse_json else '*/*',**(headers or {})}
        if payload is not None:hdr['Content-Type']='application/json'
        if self.token:hdr['Authorization']=f'Bearer {self.token}'
        req=urllib.request.Request(self.base+path,data=payload,method=method,headers=hdr)
        try:
            with self.opener.open(req,timeout=12) as response:
                status=response.status;raw=response.read();response_headers=response.headers
        except urllib.error.HTTPError as exc:
            status=exc.code;raw=exc.read();response_headers=exc.headers
        if status!=expected:
            raise AssertionError(f'{method} {path}: expected {expected}, got {status}: {raw[:500]!r}')
        if parse_json:
            return json.loads(raw or b'{}'),response_headers
        return raw,response_headers

def run():
    assert_disconnect_safe()
    with app_server({'EINVITE_REQUIRE_EMAIL_VERIFICATION':'0'}) as (_process,base,_data):
        client=Client(base)
        health,_=client.request('/api/health')
        assert health.get('ok') is True

        # Real bundled pages and headers.
        page_expectations={
            '/dashboard.html':'bundle-dashboard-v15.js',
            '/index.html':'bundle-index-v15.js',
            '/public.html':'bundle-public-v15.js',
            '/account.html':'bundle-account-v15.js',
            '/materials.html':'bundle-materials-v15.js',
            '/templates.html':'bundle-templates-v15.js',
            '/guests.html':'bundle-guests-v15.js',
            '/responses.html':'bundle-responses-v15.js',
            '/analytics.html':'bundle-analytics-v15.js',
            '/checkin.html':'bundle-checkin-v15.js',
        }
        for path,bundle in page_expectations.items():
            raw,headers=client.request(path,parse_json=False)
            text=raw.decode('utf-8')
            assert bundle in text,path
            csp=headers.get('Content-Security-Policy','')
            assert "require-trusted-types-for" not in csp
            assert "script-src 'self'" in csp and "script-src 'self' 'unsafe-inline'" not in csp

        for asset,mime in [('/bundle-index-v15.js','javascript'),('/bundle-index-v15.css','text/css'),('/bundle-public-v15.js','javascript')]:
            raw,headers=client.request(asset,parse_json=False)
            assert len(raw)>1000
            assert mime in headers.get_content_type() or mime in headers.get('Content-Type','')

        registered,_=client.request('/api/auth/register','POST',{'email':'v15-http@example.com','password':'strong-password-123'},201)
        client.token=registered.get('token','')
        assert client.token
        invite_doc={
            'schemaVersion':13,
            'eventType':'Wedding',
            'fields':{'names':'V15 HTTP Couple','namesKm':'វី១៥','date':'2027-02-14','venue':'HTTP Venue'},
            'objects':{},'designPages':[],'sectionOrder':['rsvp'],
            'settings':{'rsvpEnabled':False,'wishesEnabled':False},
        }
        invitation,_=client.request('/api/invitations','POST',{'slug':'v15-http-invitation','document':invite_doc},201)
        invite_id=invitation['id'];slug=invitation['slug']

        # Management routes must serve the root-bundled editor and related pages.
        for suffix,bundle in [('editor','bundle-index-v15.js'),('guests','bundle-guests-v15.js'),('responses','bundle-responses-v15.js'),('analytics','bundle-analytics-v15.js'),('materials','bundle-materials-v15.js')]:
            raw,_=client.request(f'/invitations/{invite_id}/{suffix}',parse_json=False)
            assert bundle in raw.decode('utf-8')

        client.request(f'/api/invitations/{invite_id}/publish','POST',{'document':invite_doc},201)
        public_page,_=client.request(f'/i/{slug}',parse_json=False)
        public_html=public_page.decode('utf-8')
        assert 'bundle-public-v15.js' in public_html
        assert slug in public_html
        public_doc,_=client.request(f'/api/public/{slug}')
        assert public_doc['document']['fields']['names']=='V15 HTTP Couple'
        assert public_doc['document']['settings']['rsvpEnabled'] is False

        # Shutdown is handled by app_server; this also exercises close/cleanup paths.
        print('V15_HTTP_INTEGRATION_TEST_PASSED')

if __name__=='__main__':run()
