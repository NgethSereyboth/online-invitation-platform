#!/usr/bin/env python3
"""Regression coverage for rich-text sanitization and invalid nested controls."""
from __future__ import annotations
import os,re,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
os.environ['EINVITE_DATA_DIR']=tempfile.mkdtemp(prefix='einvite-security-')
import server  # noqa: E402

def run():
    malicious={
        '<img src=x onerror=alert(1)>':'',
        '<script>alert(1)</script>':'',
        '<a href="javascript:alert(1)">Test</a>':'<a>Test</a>',
    }
    for raw,expected in malicious.items():
        clean=server.sanitize_rich_text_html(raw)
        assert clean==expected,(raw,clean)
        lowered=clean.lower()
        assert '<script' not in lowered and 'onerror' not in lowered and 'javascript:' not in lowered
    safe='<strong>សិរីមង្គល</strong><br><em>Hello &amp; welcome</em><span style="color:#9d4555;font-weight:700;position:fixed">Text</span>'
    clean=server.sanitize_rich_text_html(safe)
    assert '<strong>សិរីមង្គល</strong>' in clean and '<br>' in clean and '<em>Hello &amp; welcome</em>' in clean
    assert 'color:#9d4555' in clean and 'font-weight:700' in clean and 'position:' not in clean
    document={'objects':{'safe':{'type':'text','html':safe},'bad':{'type':'text','html':'<iframe src=x>bad</iframe><b>Good</b>'}},'designPages':[{'id':'p','objects':{'nested':{'type':'text','html':'<a href="javascript:x">ខ្មែរ</a><i>Safe</i>'}}}]}
    validated=server.validate_document(document)
    assert '<iframe' not in validated['objects']['bad']['html'] and 'bad' not in validated['objects']['bad']['html']
    assert validated['objects']['bad']['html']=='<strong>Good</strong>'
    assert validated['designPages'][0]['objects']['nested']['html']=='ខ្មែរ<em>Safe</em>'
    nested=re.compile(r'<a\b[^>]*>\s*<button\b',re.I)
    offenders=[]
    for path in list(ROOT.glob('*.html'))+list(ROOT.glob('*.js')):
        if nested.search(path.read_text(encoding='utf-8',errors='ignore')):offenders.append(path.name)
    assert not offenders,offenders
    print('SECURITY_REGRESSION_TEST_PASSED')
if __name__=='__main__':run()
