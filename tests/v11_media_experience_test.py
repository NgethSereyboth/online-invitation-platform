#!/usr/bin/env python3
"""V11 media, sharing, responsive-image, and schema regression coverage."""
from __future__ import annotations
import io,json,os,socket,subprocess,sys,tempfile,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def free_port():
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

def wait(base):
    end=time.time()+12
    while time.time()<end:
        try:
            with urllib.request.urlopen(base+'/api/health',timeout=2) as r:
                if r.status==200:return
        except Exception:time.sleep(.1)
    raise RuntimeError('server did not start')

def json_request(base,path,method='GET',body=None,token=None,expected=200):
    data=None if body is None else json.dumps(body).encode();headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+path,data=data,method=method,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=15) as r:status=r.status;payload=json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as exc:status=exc.code;payload=json.loads(exc.read() or b'{}')
    assert status==expected,(method,path,status,payload);return payload

def binary_request(base,path,token=None,expected=200):
    headers={}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+path,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return r.status,r.headers.get_content_type(),r.read()
    except urllib.error.HTTPError as exc:
        assert exc.code==expected,(path,exc.code,exc.read());raise

def raw_upload(base,invite_id,token,payload,mime='image/png',name='cover.png'):
    req=urllib.request.Request(base+f'/api/invitations/{invite_id}/assets/raw',data=payload,method='POST',headers={'Authorization':'Bearer '+token,'Content-Type':mime,'Content-Length':str(len(payload)),'X-File-Name':urllib.parse.quote(name)})
    with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read())

def main():
    from PIL import Image
    image=Image.new('RGB',(1600,1000),(38,116,167));buf=io.BytesIO();image.save(buf,'PNG');raw=buf.getvalue()
    port=free_port();base=f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory(prefix='einvite-v11-media-') as data_dir:
        env={**os.environ,'EINVITE_DATA_DIR':data_dir,'EINVITE_DEV_AUTH_TOKENS':'1'}
        process=subprocess.Popen([sys.executable,'-u',str(ROOT/'server.py'),'--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            wait(base);registered=json_request(base,'/api/auth/register','POST',{'email':'v11@example.com','password':'password123'},expected=201);token=registered['token']
            document={'schemaVersion':10,'fields':{'names':'Dara & Sophea','namesKm':'ដារ៉ា និង សុភា','date':'2027-01-03','venue':'Phnom Penh','venueKm':'ភ្នំពេញ'},'objects':{},'designPages':[],'sectionOrder':['gallery','wishes','rsvp'],'settings':{'rsvpEnabled':False,'wishesEnabled':True},'palette':{'background':'#fff8e7','text':'#342c26'},'accent':'#8a5b16','socialCard':{'photo':'','alignment':'left','textVariant':'light','language':'both','monogram':'DS'}}
            invite=json_request(base,'/api/invitations','POST',{'slug':'V11 Media Test','document':document},token,201);asset=raw_upload(base,invite['id'],token,raw)
            assert asset['width']==1600 and asset['height']==1000 and asset['dominantColor'].startswith('#') and asset['responsiveBase'].startswith('/api/image/'),asset
            document['socialCard']['photo']=asset['url'];document['objects']['photo']={'type':'image','src':asset['url'],'intrinsicWidth':1600,'intrinsicHeight':1000,'sizeBytes':len(raw),'dominantColor':asset['dominantColor'],'responsiveBase':asset['responsiveBase'],'width':'80%','height':'420px'}
            json_request(base,f"/api/invitations/{invite['id']}",'PUT',{'document':document},token,200);json_request(base,f"/api/invitations/{invite['id']}/publish",'POST',{'document':document},token,201)
            status,ctype,og=binary_request(base,f"/api/public/{invite['slug']}/social-card.png");assert status==200 and ctype=='image/png'
            with Image.open(io.BytesIO(og)) as card:assert card.size==(1200,630);assert card.getpixel((50,50))!=(255,248,231)
            _,_,square=binary_request(base,f"/api/public/{invite['slug']}/social-card.png?format=square");assert Image.open(io.BytesIO(square)).size==(1080,1080)
            _,qr_type,qr=binary_request(base,f"/api/public/{invite['slug']}/qr-card.png");assert qr_type=='image/png' and Image.open(io.BytesIO(qr)).size==(1080,1080)
            _,responsive_type,resized=binary_request(base,f"/api/image/{Path(urllib.parse.urlparse(asset['url']).path).name}?w=480&format=webp");assert responsive_type=='image/webp';assert Image.open(io.BytesIO(resized)).width<=480
            html=urllib.request.urlopen(base+f"/i/{invite['slug']}").read().decode();assert f'{base}/api/public/{invite["slug"]}/social-card.png' in html;assert '<meta property="og:image:width" content="1200">' in html;assert '<link rel="canonical"' in html
            guest=json_request(base,f"/api/invitations/{invite['id']}/guests",'POST',{'name':'Guest','phone':''},token,201);_,guest_qr_type,guest_qr=binary_request(base,f"/api/invitations/{invite['id']}/guests/{guest['id']}/qr.png",token);assert guest_qr_type=='image/png' and len(guest_qr)>500
            assert 'quickchart.io' not in (ROOT/'guests.js').read_text(encoding='utf-8')
            renderer=(ROOT/'renderer-core.js').read_text(encoding='utf-8');assert 'responsiveBase' in renderer and 'intrinsicWidth' in renderer and 'format=webp' in renderer and 'join' in renderer
            schema=(ROOT/'experience-schema.js').read_text(encoding='utf-8');assert r'[\u1780-\u17FF]' in schema
            print('V11_MEDIA_EXPERIENCE_TEST_PASSED')
        finally:
            process.terminate()
            try:process.wait(timeout=4)
            except subprocess.TimeoutExpired:process.kill()
if __name__=='__main__':main()
