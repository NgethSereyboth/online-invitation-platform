#!/usr/bin/env python3
"""Static contract for the lightweight public invitation journey controls."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=json.loads((ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8'))['pages']['public.html']
scripts=spec['scripts'];styles=spec['styles']
assert 'guest-journey.js' in scripts and scripts.index('guest-journey.js')<scripts.index('public-page.js'),scripts
assert 'guest-journey.css' in styles,styles
source=(ROOT/'guest-journey.js').read_text(encoding='utf-8')
for token in ('guestNavigationEnabled===false','prefers-reduced-motion','aria-current','data-journey-prev','data-journey-next','data-journey-share','data-journey-top'):
 assert token in source,token
assert 'EInviteGuestJourney?.enhance(root,d)' in (ROOT/'public-page.js').read_text(encoding='utf-8')
print('V0_52_GUEST_JOURNEY_CONTRACT_TEST_PASSED')
