#!/usr/bin/env python3
from __future__ import annotations
import json,os,socket,sys,tempfile,threading,urllib.error,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['EINVITE_DEV_AUTH_TOKENS']='1'
sys.path.insert(0,str(ROOT))

def free_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return int(s.getsockname()[1])

def json_request(base,path,method='GET',body=None,token=None,expected=200):
    data=None if body is None else json.dumps(body).encode();headers={'Content-Type':'application/json'}
    if token:headers['Authorization']=f'Bearer {token}'
    req=urllib.request.Request(base+path,data=data,method=method,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=20) as res:status=res.status;payload=json.loads(res.read() or b'{}')
    except urllib.error.HTTPError as exc:status=exc.code;payload=json.loads(exc.read() or b'{}')
    assert status==expected,(method,path,status,payload);return payload

def raw_request(base,path,raw,mime,name,token,expected=201,acknowledged=True):
    headers={'Content-Type':mime,'Content-Length':str(len(raw)),'X-File-Name':urllib.parse.quote(name),'Authorization':f'Bearer {token}'}
    if acknowledged:headers['X-Font-License-Acknowledged']='true'
    req=urllib.request.Request(base+path,data=raw,method='POST',headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=30) as res:status=res.status;payload=json.loads(res.read() or b'{}')
    except urllib.error.HTTPError as exc:status=exc.code;payload=json.loads(exc.read() or b'{}')
    assert status==expected,(path,status,payload);return payload

def sample_font():
    for p in (Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),Path('/usr/share/fonts/truetype/lato/Lato-Medium.ttf'),Path('C:/Windows/Fonts/arial.ttf')):
        if p.is_file():return p
    raise RuntimeError('No TTF font available')

def main():
    with tempfile.TemporaryDirectory(prefix='einvite-v22-font-api-') as data:
        os.environ['EINVITE_DATA_DIR']=data
        import server
        port=free_port();httpd=server.ThreadingHTTPServer(('127.0.0.1',port),server.Handler);thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{port}'
        try:
            auth=json_request(base,'/api/auth/register','POST',{'email':'font-api@example.com','password':'password123'},expected=201);token=auth['token']
            doc={'eventType':'Wedding','fields':{'names':'Font Test','date':'2026-12-27','venue':'Venue','message':'Join us'},'objects':{},'designPages':[],'sectionOrder':['rsvp'],'settings':{'rsvpEnabled':True}}
            invitation=json_request(base,'/api/invitations','POST',{'slug':'font-api-test','document':doc},token,201);iid=invitation['id'];raw=sample_font().read_bytes()
            declined=raw_request(base,f'/api/invitations/{iid}/fonts',raw,'font/ttf',sample_font().name,token,400,False);assert 'permission' in str(declined).lower()
            first=raw_request(base,f'/api/invitations/{iid}/fonts',raw,'font/ttf',sample_font().name,token)
            assert first['mime']=='font/woff2' and first['url'].startswith('/uploads/')
            assert first['format']=='woff2' and first['sourceFormat']=='ttf' and first['glyphCount']>0
            assert first['optimizedBytes']==first['size'] and first['originalBytes']==len(raw)
            assert first['family'] and 'Latin' in first['scripts'] and first['duplicate'] is False
            second=raw_request(base,f'/api/invitations/{iid}/fonts',raw,'font/ttf','renamed.tff',token)
            assert second['duplicate'] is True and second['sha256']==first['sha256'] and second['url']==first['url']
            khmer_raw=(ROOT/'assets/fonts/noto-sans-khmer-400.woff2').read_bytes()
            khmer=raw_request(base,f'/api/invitations/{iid}/fonts',khmer_raw,'font/woff2','NotoSansKhmer.woff2',token)
            assert khmer['khmerReady'] is True and khmer['khmerSupport']=='ready'
            assert khmer['khmerCoreCoveragePercent']>=99 and khmer['khmerShaping'] is True
            assert khmer['recommendedLineHeight']>=1.38 and khmer['category']=='sans'
            bad=raw_request(base,f'/api/invitations/{iid}/fonts',b'not-a-font','font/ttf','bad.ttf',token,400)
            assert 'font' in str(bad).lower()
            req=urllib.request.Request(base+first['url'],headers={'Authorization':f'Bearer {token}'})
            with urllib.request.urlopen(req,timeout=15) as res:
                body=res.read();assert res.status==200 and res.headers.get_content_type()=='font/woff2' and body.startswith(b'wOF2')
        finally:httpd.shutdown();httpd.server_close();thread.join(timeout=3)
    print('V22_CUSTOM_FONT_SERVER_ENDPOINT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
