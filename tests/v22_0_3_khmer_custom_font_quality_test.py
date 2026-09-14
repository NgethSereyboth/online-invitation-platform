#!/usr/bin/env python3
from __future__ import annotations
import io,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('EINVITE_DATA_DIR',tempfile.mkdtemp(prefix='einvite-khmer-font-quality-'))
sys.path.insert(0,str(ROOT))
import server
from fontTools.ttLib import TTFont


def test_server_khmer_quality():
    source=ROOT/'assets/fonts/noto-sans-khmer-400.woff2'
    optimized,meta=server.optimize_custom_font(source.read_bytes(),source.name,'font/woff2')
    assert optimized.startswith(b'wOF2')
    assert meta['optimizationProfile']=='khmer-safe-full'
    assert meta['scripts']==['Khmer'] and meta['category']=='sans'
    assert meta['khmerReady'] is True and meta['khmerSupport']=='ready'
    assert meta['khmerCoreCoveragePercent']>=99 and meta['khmerShaping'] is True
    assert meta['khmerScriptTables'] is True and {'pref','blwf','abvf','pstf','abvm','blwm','dist'}.issubset(set(meta['khmerFeatures']))
    assert meta['khmerMissingCore']==[] and meta['khmerWarnings']==[]
    assert 1.38<=meta['recommendedLineHeight']<=1.8
    decoded=TTFont(io.BytesIO(optimized))
    assert 'GSUB' in decoded and 'GPOS' in decoded and 'GDEF' in decoded
    decoded.close()

    # Remove most Khmer cmap entries while preserving the OpenType tables. The
    # font must remain uploadable but may not become the primary Khmer face.
    partial=TTFont(source)
    keep={0x1780,0x17B6,0x17D2,0x17E0}
    for table in partial['cmap'].tables:
        if table.isUnicode():
            table.cmap={cp:glyph for cp,glyph in table.cmap.items() if cp not in server._KHMER_BLOCK_CODEPOINTS or cp in keep}
    partial.flavor='woff2';buf=io.BytesIO();partial.save(buf);partial.close()
    _,partial_meta=server.optimize_custom_font(buf.getvalue(),'partial-khmer.woff2','font/woff2')
    assert 'Khmer' in partial_meta['scripts']
    assert partial_meta['khmerSupport']=='partial' and partial_meta['khmerReady'] is False
    assert partial_meta['khmerCoreCoveragePercent']<10
    assert partial_meta['khmerWarnings']


def test_runtime_pairing_and_metrics():
    code=r'''
const fs=require('fs'),vm=require('vm');
global.window=global;global.location={href:'http://localhost/index.html'};global.queueMicrotask=fn=>fn();
global.document={fonts:{add(){},delete(){},ready:Promise.resolve()},dispatchEvent(){}};
global.FontFace=class{constructor(){this.status='unloaded'}async load(){this.status='loaded';return this}};
for(const file of ['typography-contract.js','custom-font-core-v22.js','typography-layout-service.js','rich-text-renderer-v21.js'])vm.runInThisContext(fs.readFileSync(file,'utf8'),{filename:file});
const ready='custom-111111111111',partial='custom-222222222222',doc={customFonts:{
 [ready]:{id:ready,label:'Khmer Ready',url:'/ready.woff2',sha256:'1'.repeat(64),category:'sans',scripts:['Khmer'],khmerReady:true,khmerSupport:'ready',khmerCoreCoveragePercent:100,khmerShaping:true,recommendedLineHeight:1.48},
 [partial]:{id:partial,label:'Khmer Partial',url:'/partial.woff2',sha256:'2'.repeat(64),category:'sans',scripts:['Khmer'],khmerReady:false,khmerSupport:'partial',khmerCoreCoveragePercent:12,khmerShaping:false,recommendedLineHeight:1.45}
}};
EInviteCustomFonts.normalizeDocumentFonts(doc,{install:false});
if(EInviteFontRegistry.pairedFont('custom-pair-'+ready,'km')!==ready)throw Error('verified Khmer font was not paired');
if(EInviteFontRegistry.pairedFont('custom-pair-'+partial,'km')!=='noto-sans-khmer')throw Error('partial Khmer font bypassed fallback');
const meta=EInviteFontRegistry.data.fonts[ready];if(!meta.khmerReady||meta.recommendedLineHeight!==1.48)throw Error('Khmer metadata lost');
const style=TypographyLayoutService.styleObject({locale:'km',text:'អាពាហ៍ពិពាហ៍',font:ready,fontStack:meta.stack,fontSize:32,lineHeight:1.1,textPadding:0,textColumns:1});
if(Number(style.outer.lineHeight)<1.48)throw Error('Khmer line-height safety not applied');
if(style.outer.fontSynthesis!=='none')throw Error('font synthesis protection missing');
const rich={version:1,paragraphs:[{id:'p',locale:'km',direction:'ltr',paragraphStyleId:'body',runs:[{id:'r',locale:'km',text:'សិរីមង្គល',marks:{fontPairing:'custom-pair-'+ready}}]}],entities:{}};
const html=RichTextRenderer.renderDocument(rich,{});if(!html.includes('line-height:1.48')||!html.includes('lang="km"'))throw Error('rich-text Khmer shaping parity missing');
console.log('V22_0_3_KHMER_RUNTIME_OK');
'''
    result=subprocess.run(['node','-e',code],cwd=ROOT,text=True,capture_output=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'V22_0_3_KHMER_RUNTIME_OK' in result.stdout
    css=(ROOT/'rich-text-renderer-v21.css').read_text(encoding='utf-8')
    assert 'font-synthesis:none' in css and 'font-variant-ligatures:common-ligatures contextual' in css


def main():
    test_server_khmer_quality();test_runtime_pairing_and_metrics()
    print('V22_0_3_KHMER_CUSTOM_FONT_QUALITY_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
