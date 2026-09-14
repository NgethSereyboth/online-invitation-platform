#!/usr/bin/env python3
from __future__ import annotations
import io,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('EINVITE_DATA_DIR',tempfile.mkdtemp(prefix='einvite-font-test-'))
sys.path.insert(0,str(ROOT))
import server
from fontTools.ttLib import TTFont


def sample_font():
 candidates=[
  Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
  Path('/usr/share/fonts/truetype/lato/Lato-Medium.ttf'),
  Path('C:/Windows/Fonts/arial.ttf'),
 ]
 for path in candidates:
  if path.is_file():return path
 raise RuntimeError('No test TTF font is available')


def test_server_optimization():
 source=sample_font().read_bytes()
 optimized,meta=server.optimize_custom_font(source,sample_font().name,'font/ttf')
 assert optimized.startswith(b'wOF2')
 assert meta['format']=='woff2' and meta['sourceFormat']=='ttf'
 assert meta['family'] and meta['glyphCount']>0 and 'Latin' in meta['scripts']
 assert meta['optimizedBytes']==len(optimized) and meta['originalBytes']==len(source)
 decoded=TTFont(io.BytesIO(optimized));assert decoded['maxp'].numGlyphs==meta['glyphCount'];decoded.close()
 try:server.optimize_custom_font(b'not-a-font','bad.ttf','font/ttf')
 except ValueError:pass
 else:raise AssertionError('Invalid font content was accepted')
 try:server.optimize_custom_font(b'ttcf'+b'\0'*40,'collection.ttc','application/octet-stream')
 except ValueError as exc:assert 'collections' in str(exc).lower()
 else:raise AssertionError('A font collection was accepted')


def test_runtime_registry():
 node=r'''
const fs=require('fs'),vm=require('vm');
global.window=global;global.location={href:'http://localhost/index.html'};
global.CustomEvent=class{constructor(type,init={}){this.type=type;this.detail=init.detail}};
const faces=new Set();global.document={fonts:{add:x=>faces.add(x),delete:x=>faces.delete(x)},dispatchEvent:()=>{}};
global.FontFace=class{constructor(family,source,descriptors){this.family=family;this.source=source;this.descriptors=descriptors;this.status='unloaded'}async load(){this.status='loaded';return this}};
vm.runInThisContext(fs.readFileSync('typography-contract.js','utf8'),{filename:'typography-contract.js'});
vm.runInThisContext(fs.readFileSync('custom-font-core-v22.js','utf8'),{filename:'custom-font-core-v22.js'});
const id='custom-1234567890ab',doc={customFonts:{[id]:{id,label:'Test Custom',url:'/uploads/test.woff2',sha256:'1234567890abcdef',scripts:['Latin'],weight:400,style:'normal',licenseAcknowledged:true}}};
EInviteCustomFonts.normalizeDocumentFonts(doc,{install:false});
if(EInviteTypography.fontId(id)!==id)throw Error('dynamic font ID not accepted');
if(!EInviteFontRegistry.data.fonts[id]?.custom)throw Error('custom registry metadata missing');
const pair='custom-pair-'+id;
if(EInviteFontRegistry.pairedFont(pair,'en')!==id)throw Error('Latin custom pairing missing');
if(EInviteFontRegistry.pairedFont(pair,'km')!=='noto-serif-khmer')throw Error('Khmer fallback missing');
(async()=>{await EInviteCustomFonts.installDocumentFonts(doc);if(!faces.size)throw Error('FontFace was not installed');console.log('CUSTOM_FONT_RUNTIME_OK')})().catch(error=>{console.error(error);process.exit(1)});
'''
 result=subprocess.run(['node','-e',node],cwd=ROOT,text=True,capture_output=True)
 assert result.returncode==0,result.stdout+result.stderr
 assert 'CUSTOM_FONT_RUNTIME_OK' in result.stdout


def test_integration_contracts():
 routes=json.loads((ROOT/'route-bundle-sources-v15.json').read_text())
 index=routes['pages']['index.html']['scripts'];public=routes['pages']['public.html']['scripts'];dashboard=routes['pages']['dashboard.html']['scripts']
 assert 'custom-font-core-v22.js' in index and index.index('custom-font-core-v22.js')==index.index('typography-contract.js')+1
 assert 'custom-font-core-v22.js' in public and public.index('custom-font-core-v22.js')==public.index('typography-contract.js')+1
 assert 'custom-font-core-v22.js' not in dashboard and 'custom-fonts-v22.js' not in dashboard
 assert 'editor-deferred-tools-bootstrap-v0_52.js' in index and 'font-browser-loader-v22.js' not in index and 'custom-fonts-v22.js' not in index
 assert 'custom-fonts-v22.css' not in routes['pages']['index.html']['styles']
 bootstrap=(ROOT/'editor-deferred-tools-bootstrap-v0_52.js').read_text();assert 'font-browser-loader-v22.js' in bootstrap
 loader=(ROOT/'font-browser-loader-v22.js').read_text();assert 'custom-fonts-v22.js' in loader and 'font-browser.js' in loader and 'custom-fonts-v22.css' in loader
 upload=(ROOT/'upload-client.js').read_text();assert 'uploadFont' in upload and '/fonts' in upload
 browser=(ROOT/'font-browser.js').read_text();assert '.ttf,.tff,.otf,.woff2' in browser and 'licenseAcknowledged' in browser
 server_text=(ROOT/'server.py').read_text();assert 'optimize_custom_font' in server_text and 'def upload_font' in server_text
 model=(ROOT/'typography-document-model.js').read_text();assert 'normalizeDocumentFonts' in model


if __name__=='__main__':
 test_server_optimization();test_runtime_registry();test_integration_contracts();print('V22_CUSTOM_FONT_UPLOAD_TEST_PASSED')
