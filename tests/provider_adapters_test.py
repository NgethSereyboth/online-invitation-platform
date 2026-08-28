"""Exercise provider-neutral AI and hosted-checkout adapters against local mock providers."""
from __future__ import annotations
import hashlib,hmac,json,os,socket,subprocess,sys,tempfile,threading,time,urllib.error,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ["EINVITE_DEV_AUTH_TOKENS"]="1"

def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
class Provider(BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def do_POST(self):
        n=int(self.headers.get('Content-Length','0'));payload=json.loads(self.rfile.read(n) or b'{}')
        if self.path=='/ai':body={'text':f"External provider: {payload.get('task','write')}"}
        elif self.path=='/checkout':body={'url':'https://checkout.example.test/session/demo'}
        else:self.send_response(404);self.end_headers();return
        raw=json.dumps(body).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
def request(base,path,method='GET',body=None,token=None,expected=200):
    raw=None if body is None else json.dumps(body).encode();headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+path,data=raw,method=method,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=8) as r:return r.status,json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        data=json.loads(e.read() or b'{}')
        if e.code!=expected:raise AssertionError((path,e.code,data))
        return e.code,data
def wait(base):
    for _ in range(80):
        try:
            if request(base,'/api/health')[0]==200:return
        except Exception:time.sleep(.1)
    raise RuntimeError('server unavailable')
def main():
    provider_port=port();provider=ThreadingHTTPServer(('127.0.0.1',provider_port),Provider);thread=threading.Thread(target=provider.serve_forever,daemon=True);thread.start()
    app_port=port();base=f'http://127.0.0.1:{app_port}'
    with tempfile.TemporaryDirectory(prefix='einvite-adapters-') as data:
        env={**os.environ,'EINVITE_DATA_DIR':data,'EINVITE_AI_ENDPOINT':f'http://127.0.0.1:{provider_port}/ai','EINVITE_BILLING_CHECKOUT_ENDPOINT':f'http://127.0.0.1:{provider_port}/checkout','EINVITE_BILLING_WEBHOOK_SECRET':'adapter-webhook-secret','EINVITE_ADMIN_EMAIL':'adapter@example.com'}
        proc=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(app_port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            wait(base)
            _,reg=request(base,'/api/auth/register','POST',{'email':'adapter@example.com','password':'password123'},expected=201);token=reg['token']
            _,ai=request(base,'/api/ai/assist','POST',{'task':'romantic','prompt':'hello','context':{}},token);assert ai['provider']=='external' and ai['text'].startswith('External provider:')
            _,billing=request(base,'/api/billing/status',token=token);assert billing['configured'] and billing['paymentMethods']==['visa','mastercard']
            _,checkout=request(base,'/api/billing/checkout','POST',{'plan':'creator'},token);assert checkout['url'].startswith('https://checkout.example.test/') and checkout['orderId'].startswith('ord_')
            event={'id':'evt_card_paid','type':'payment.completed','data':{'orderId':checkout['orderId'],'plan':'creator','amountMinor':900,'currency':'USD'}}
            raw=json.dumps(event).encode();signature=hmac.new(b'adapter-webhook-secret',raw,hashlib.sha256).hexdigest()
            webhook=urllib.request.Request(base+'/api/billing/webhook',data=raw,method='POST',headers={'Content-Type':'application/json','X-EInvite-Signature':signature})
            with urllib.request.urlopen(webhook,timeout=8) as response:assert response.status==200
            _,usage=request(base,'/api/account/usage',token=token);assert usage['plan']=='creator'
            print('PROVIDER_ADAPTERS_TEST_PASSED')
        finally:
            proc.terminate()
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:proc.kill()
    provider.shutdown();provider.server_close()
if __name__=='__main__':main()
