"""Static integrity checks for local HTML assets and JavaScript syntax."""
from __future__ import annotations
import re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HTML=list(ROOT.glob('*.html'))
missing=[]
for page in HTML:
    text=page.read_text(encoding='utf-8')
    for attr in ('src','href'):
        for value in re.findall(fr'{attr}=["\']([^"\']+)["\']',text,re.I):
            if value.startswith(('http://','https://','data:','#','mailto:','tel:')) or '${' in value:continue
            value=value.split('?',1)[0].split('#',1)[0]
            if not value or value.startswith('/api/') or value.startswith('/i/') or value.startswith('/uploads/'):continue
            target=ROOT/value.lstrip('/')
            if not target.exists():missing.append((page.name,value))
if missing:raise AssertionError(f'Missing local assets: {missing}')
# All external JS files parse.
for js in ROOT.glob('*.js'):
    subprocess.run(['node','--check',str(js)],check=True,stdout=subprocess.DEVNULL)
# Inline scripts parse as a combined file per HTML document.
for page in HTML:
    scripts=re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>',page.read_text(encoding='utf-8'),re.S|re.I)
    if not scripts:continue
    with tempfile.NamedTemporaryFile('w',suffix='.js',delete=False,encoding='utf-8') as f:
        f.write('\n'.join(scripts));name=f.name
    result=subprocess.run(['node','--check',name],capture_output=True,text=True)
    Path(name).unlink(missing_ok=True)
    if result.returncode:raise AssertionError(f'{page.name} inline JavaScript failed: {result.stderr}')
print('STATIC_INTEGRITY_TEST_PASSED')
