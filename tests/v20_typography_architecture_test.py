#!/usr/bin/env python3
"""Deterministic V20 typography architecture, migration and hostile-input checks."""
from __future__ import annotations
import copy,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from typography_document_model import normalize_document_typography,DEFAULT_STYLES,STYLE_FIELDS

def expect_reject(doc):
 try:normalize_document_typography(copy.deepcopy(doc),strict=True)
 except (TypeError,ValueError):return
 raise AssertionError(f'hostile typography input accepted: {doc!r}')

def main()->int:
 contract=json.loads((ROOT/'typography-contract.json').read_text(encoding='utf-8'))
 assert contract['version']=='20.1' and contract['modelVersion']==1
 assert set(contract['fonts'])=={'noto-serif','noto-sans','noto-serif-khmer','noto-sans-khmer','serif-georgia','sans-arial','sans-trebuchet'}
 assert {'serif-formal','sans-modern','modern-system','ceremonial-khmer','classic-system','friendly-system'}<=set(contract['pairings'])
 for font_id,font in contract['fonts'].items():
  assert re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',font_id) and font['family'] and font['stack']
  assert isinstance(font['scripts'],list) and font['scripts']
  if font.get('bundled'):
   assert font['assets'] and all(str(asset).endswith('.woff2') for asset in font['assets'].values())
   assert font['license']=='SIL Open Font License 1.1' and font.get('copyright')
 for style_id in ('display','heading','subheading','body','caption','khmer-ceremonial'):
  style=DEFAULT_STYLES[style_id]
  assert (set(STYLE_FIELDS)-{'color'})<=set(style),style_id

 legacy={'objects':{'title':{'type':'text','html':'សូមស្វាគមន៍','font':'noto-serif-khmer','fontSize':52,'textAutoFit':'fit','textAutoFitMax':64,'textMinFontSize':14}},'designPages':[]}
 migrated=normalize_document_typography(copy.deepcopy(legacy),strict=True)
 obj=migrated['objects']['title']
 assert obj['typographyModelVersion']==1 and obj['textStyleId']=='khmer-ceremonial'
 assert obj['font']=='noto-serif-khmer' and obj['fontPairing'] in contract['pairings']
 assert obj['typographyResolvedSnapshot']['fontSize']==obj['fontSize']
 assert not any(',' in str(value) or '"' in str(value) for key,value in obj.items() if key in {'font','fontPairing'})

 # A legacy flat-field command after migration becomes an explicit override.
 changed=copy.deepcopy(migrated);changed['objects']['title']['fontSize']=37
 changed=normalize_document_typography(changed,strict=True)
 assert changed['objects']['title']['typographyOverrides']['fontSize']==37

 # A linked-style update propagates because unchanged flattened snapshots are not mistaken for overrides.
 linked=copy.deepcopy(migrated);linked['objects']['title']['typographyOverrides'].pop('fontSize',None);linked['typography']['styles']['khmer-ceremonial']['fontSize']=58
 linked=normalize_document_typography(linked,strict=True)
 assert linked['objects']['title']['fontSize']==58
 assert 'fontSize' not in linked['objects']['title']['typographyOverrides']

 base={'objects':{'x':{'type':'text','html':'x'}},'designPages':[]}
 for bad in (
  {**base,'typography':{'styles':{'evil style':{}}}},
  {**base,'typography':{'styles':{'body':{'fontPairing':'Arial, sans-serif'}}}},
  {**base,'typography':{'styles':{'body':{'fontSize':'NaN'}}}},
  {**base,'typography':{'styles':{'body':{'textColumns':1.5}}}},
  {'objects':{'x':{'type':'text','html':'x','font':'Papyrus, fantasy'}},'designPages':[]},
  {'objects':{'x':{'type':'text','html':'x','typographyOverrides':{'fontFamily':'serif'}}},'designPages':[]},
 ):
  expect_reject(bad)


 legacy_family=normalize_document_typography({'objects':{'x':{'type':'text','html':'x','font':'Arial, sans-serif'}},'designPages':[]},strict=True)
 assert legacy_family['objects']['x']['font']=='sans-arial'

 sources=json.loads((ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8'))['pages']
 for page in ('index.html','public.html','dashboard.html'):
  scripts=sources[page]['scripts']
  assert scripts.index('typography-contract.js')<scripts.index('typography-document-model.js')<scripts.index('typography-layout-service.js')<scripts.index('renderer-core.js')
 assert 'typography-editor-v20.js' in sources['index.html']['scripts']
 assert 'typography-system-v20.css' in sources['index.html']['styles']

 renderer=(ROOT/'renderer-core.js').read_text(encoding='utf-8')
 assert 'EInviteTypographyRendererAdapters' in renderer and 'TypographyLayoutService.styleObject' in renderer
 assert 'const wrap=model.textWrap' not in renderer and 'const vertical=model.textVerticalAlign' not in renderer
 assert 'TypographyLayoutService must load before renderer-core.js' in renderer
 assert 'data-typography-model-version="1"' in renderer
 app=(ROOT/'app.js').read_text(encoding='utf-8')
 assert 'TypographyDocumentModel.resolveObjectTypography' in app and 'TypographyLayoutService.installResponsive' in app
 assert 'v19FitFrame' not in app and 'v19ResizeObserver' not in app and 'new ResizeObserver' not in app and 'document.fonts' not in app
 assert 'renderThumbnail' in app
 editor=(ROOT/'typography-editor-v20.js').read_text(encoding='utf-8')
 assert 'Actual editor DOM' in editor and 'Actual public renderer' in editor and 'data-preview-pipeline' not in editor
 dashboard=(ROOT/'dashboard.js').read_text(encoding='utf-8');polish=(ROOT/'final-polish.js').read_text(encoding='utf-8');assert 'renderThumbnail' in polish and 'objectPreview' not in polish and 'overflowEstimate' not in dashboard
 assert 'typographyResolvedSnapshot' in app
 print('V20_TYPOGRAPHY_ARCHITECTURE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
