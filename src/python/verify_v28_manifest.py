#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/'V28_RELEASE_FILE_HASHES.sha256'
def main()->int:
 if not MANIFEST.is_file():raise SystemExit('V28 manifest is missing')
 expected={}
 for line in MANIFEST.read_text(encoding='utf-8').splitlines():
  if not line.strip():continue
  digest,rel=line.split('  ',1);expected[rel.removeprefix('./')]=digest
 actual={}
 for path in sorted(ROOT.rglob('*')):
  if not path.is_file() or path==MANIFEST or '__pycache__' in path.parts:continue
  rel=path.relative_to(ROOT).as_posix();actual[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
 if actual!=expected:
  missing=sorted(set(expected)-set(actual));extra=sorted(set(actual)-set(expected));changed=sorted(k for k in expected.keys()&actual.keys() if expected[k]!=actual[k])
  raise SystemExit(f'Manifest mismatch: missing={missing[:10]} extra={extra[:10]} changed={changed[:10]}')
 print(f'V28_RELEASE_MANIFEST_VERIFIED {len(actual)} files');return 0
if __name__=='__main__':raise SystemExit(main())
