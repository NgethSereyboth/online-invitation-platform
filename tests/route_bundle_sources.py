"""Helpers for compatibility tests after deterministic V15 route bundling."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8'))
def scripts(page:str)->list[str]:return list(DATA['pages'][page]['scripts'])
def styles(page:str)->list[str]:return list(DATA['pages'][page]['styles'])
def has(page:str,name:str)->bool:return name in scripts(page) or name in styles(page)
def after(page:str,later:str,earlier:str,kind='scripts')->bool:
 rows=scripts(page) if kind=='scripts' else styles(page)
 return rows.index(later)>rows.index(earlier)
