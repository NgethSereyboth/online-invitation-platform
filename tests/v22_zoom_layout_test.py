from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
css=(ROOT/'zoom-layout-v22.css').read_text(encoding='utf-8');manifest=json.loads((ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8'))
for token in ['@media(max-width:1500px)','@media(max-width:1280px)','@media(max-width:1180px)','.studio-inspector-tabs','overflow-x:auto!important','--v22-control-min:44px','min-width:72px!important','flex-wrap:nowrap!important']:assert token in css,token
compact=(ROOT/'zoom-layout-pages-v22.css').read_text(encoding='utf-8');assert 'compact authenticated-page zoom support' in compact and '--v22-control-min:44px' in compact
for page,cfg in manifest['pages'].items():
 if page=='public.html':assert 'zoom-layout-v22.css' not in cfg['styles'] and 'zoom-layout-pages-v22.css' not in cfg['styles'];continue
 expected='zoom-layout-v22.css' if page=='index.html' else 'zoom-layout-pages-v22.css';assert expected in cfg['styles'],(page,expected)
 if page=='index.html':
  assert cfg['styles'].index(expected)<cfg['styles'].index('editor-responsive-contract-v27.css')
  assert cfg['styles'][-1]=='editor-responsive-contract-v27.css'
 bundle=ROOT/f"bundle-{Path(page).stem}-v15.css";assert bundle.exists(),bundle
 text=bundle.read_text(encoding='utf-8');assert ('--v22-control-min:44px' in text if page=='index.html' else 'compact authenticated-page zoom support' in text),page
print('V22_ZOOM_LAYOUT_TEST_PASSED')
