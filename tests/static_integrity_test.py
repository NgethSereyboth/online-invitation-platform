"""Static integrity checks for local HTML assets and JavaScript syntax."""
from __future__ import annotations
import re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def resolve_repo_path(relative):
    stripped=relative.lstrip('/')
    for candidate in (ROOT/stripped,ROOT/'src'/'js'/stripped,ROOT/'src'/'css'/stripped,ROOT/'src'/'html'/stripped):
        if candidate.exists():return candidate
    return ROOT/stripped
HTML=list(ROOT.glob('src/html/*.html'))
missing=[]
for page in HTML:
    text=page.read_text(encoding='utf-8')
    for attr in ('src','href'):
        for value in re.findall(fr'{attr}=["\']([^"\']+)["\']',text,re.I):
            if value.startswith(('http://','https://','data:','#','mailto:','tel:')) or '${' in value:continue
            value=value.split('?',1)[0].split('#',1)[0]
            if not value or value.startswith('/api/') or value.startswith('/i/') or value.startswith('/uploads/'):continue
            target=resolve_repo_path(value)
            if not target.exists():missing.append((page.name,value))
if missing:raise AssertionError(f'Missing local assets: {missing}')
# All external JS files parse.
for js in ROOT.glob('src/js/*.js'):
    subprocess.run(['node','--check',str(js)],check=True,stdout=subprocess.DEVNULL)
# Inline scripts parse as a combined file per HTML document.
def _inline_scripts(text):
    """Inline <script> bodies, with HTML comments removed first.

    Stripping comments is not cosmetic: the route-bundle header comment in the pages spells out
    ``Do NOT add direct <script>/<link> ...``, and the old regex read that literal ``<script>`` as an
    opening tag and captured everything up to the next real ``</script>`` (a ``<link>`` line and all),
    so the combined temp file was not JavaScript at all. That only stayed hidden while each page had a
    real inline script *before* the comment; once the last inline block moved into a module (C1/D2),
    index.html collected to a syntax error instead of a check. Comments are not inline scripts.
    """
    without_comments=re.sub(r'<!--.*?-->','',text,flags=re.S)
    return re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>',without_comments,re.S|re.I)
# Inline scripts parse as a combined file per HTML document.
for page in HTML:
    scripts=_inline_scripts(page.read_text(encoding='utf-8'))
    if not scripts:continue
    with tempfile.NamedTemporaryFile('w',suffix='.js',delete=False,encoding='utf-8') as f:
        f.write('\n'.join(scripts));name=f.name
    result=subprocess.run(['node','--check',name],capture_output=True,text=True)
    Path(name).unlink(missing_ok=True)
    if result.returncode:raise AssertionError(f'{page.name} inline JavaScript failed: {result.stderr}')
print('STATIC_INTEGRITY_TEST_PASSED')
