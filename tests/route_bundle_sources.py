"""Helpers for compatibility tests after deterministic V15 route bundling."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
_candidates = [ROOT/'docs'/'route-bundle-sources-v15.json', ROOT / "docs" / "route-bundle-sources-v15.json"]
SOURCE = next((path for path in _candidates if path.exists()), _candidates[0])
DATA=json.loads(SOURCE.read_text(encoding='utf-8'))
def startup_scripts(page:str)->list[str]:return list(DATA['pages'][page]['scripts'])
def startup_styles(page:str)->list[str]:return list(DATA['pages'][page]['styles'])
def scripts(page:str)->list[str]:
    """Every script the page loads: startup bundle first, then the deferred chunk.

    Deferred modules (``deferredScripts``) load via route-deferred-loader-v15.js
    after first paint; membership checks mean "the page ships it", so both lists
    count. Use ``startup_scripts`` to assert startup-bundle placement.
    """
    return startup_scripts(page)+list(DATA['pages'][page].get('deferredScripts') or [])
def styles(page:str)->list[str]:
    return startup_styles(page)+list(DATA['pages'][page].get('deferredStyles') or [])
def has(page:str,name:str)->bool:return name in scripts(page) or name in styles(page)
def after(page:str,later:str,earlier:str,kind='scripts')->bool:
 rows=scripts(page) if kind=='scripts' else styles(page)
 return rows.index(later)>rows.index(earlier)
