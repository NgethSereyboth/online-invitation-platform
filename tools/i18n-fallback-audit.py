#!/usr/bin/env python3
"""FB-14 — classify the remaining fallback rows in docs/i18n/TRANSLATIONS.csv.

Audit-only (owner gate 2026-10-22: audit first, no translations applied).
Regenerates artifacts/next-work/fb-14/fallback-audit.md deterministically.
ID/path/URL tokens stay English (technical allowlist); admin/billing/
monitoring screens are English-only-admin pending owner review; everything
else is a REAL user-facing gap, deferred pending owner-supplied Khmer.
"""
import csv, re, os
from collections import Counter

ROWS = list(csv.DictReader(open('docs/i18n/TRANSLATIONS.csv', encoding='utf-8-sig')))
FB = [r for r in ROWS if r['status'] == 'fallback']
assert len(FB) == 6, len(FB)

ADMIN_FILES = {'src/js/pages/admin/feature-flags.js', 'src/js/pages/admin/invitations.js',
               'src/js/pages/admin/audit-log.js', 'src/html/admin.html',
               'src/js/monitoring.js', 'src/html/billing.html'}
GUEST_FILES = {'src/js/guests.js', 'src/html/guests.html', 'src/js/templates.js',
               'src/html/templates.html', 'src/js/responses.js', 'src/html/responses.html',
               'src/js/materials.js', 'src/html/materials.html', 'src/js/reset.js',
               'src/html/privacy.html'}


def kind(row):
    en = row['en'].strip()
    if re.fullmatch(r'[A-Za-z0-9_.\-/:#]+', en) and ' ' not in en:
        return 'technical'
    if row['file'] in ADMIN_FILES:
        return 'admin'
    if row['file'] in GUEST_FILES:
        return 'guest-facing'
    return 'other-user'


groups = {'technical': [], 'admin': [], 'guest-facing': [], 'other-user': []}
for r in FB:
    groups[kind(r)].append(r)

seen, ordered = set(), []
for r in groups['guest-facing'] + groups['other-user']:
    if r['en'] not in seen:
        seen.add(r['en'])
        ordered.append((r['en'], r['file']))

os.makedirs('artifacts/next-work/fb-14', exist_ok=True)
with open('artifacts/next-work/fb-14/fallback-audit.md', 'w', encoding='utf-8') as fh:
    fh.write('# FB-14 fallback audit — 6 rows classified (LT-1.2 moved the pin from 305; LT-1.8 added the admin 403 sentence; LT-2.2 added the Khmer numerals label and command; LT-3.2 added the Messenger label and desktop fallback)\n\n')
    fh.write('Date: 2026-10-22. No translation applied (owner gate: audit first; OD-8 / feature-flags deferred separately).\n\n')
    fh.write('| class | rows | disposition |\n|---|---|---|\n')
    fh.write(f"| technical/non-UI (ids, keys, URLs — keep English) | {len(groups['technical'])} | allowlist; no Khmer needed |\n")
    fh.write(f"| admin/billing/monitoring (owner-only screens) | {len(groups['admin'])} | English-only admin — future owner review |\n")
    fh.write(f"| guest/invitee-facing missing Khmer | {len(groups['guest-facing'])} | deferred pending owner Khmer |\n")
    fh.write(f"| host-side user-facing missing Khmer | {len(groups['other-user'])} | deferred pending owner Khmer |\n\n")
    fh.write('## Technical allowlist (%d rows)\n\n' % len(groups['technical']))
    fh.write('Every fallback `en` value that is a single token (id, key, URL fragment, filename, CSS class, event name, attribute). By file: ')
    tf = Counter(r['file'] for r in groups['technical'])
    fh.write(', '.join(f'{f} ({c})' for f, c in tf.most_common()) + '\n\n')
    fh.write('## Admin allowlist (%d rows)\n\n' % len(groups['admin']))
    fh.write('Files: ' + ', '.join(sorted({r['file'] for r in groups['admin']})) + '\n\n')
    fh.write('OD-8 already covers feature-flags.js as deferred trusted Khmer (12 rows); the remaining rows are admin/monitoring/billing screens — English-only admin pending owner review. Not translated in this pass.\n\n')
    fh.write('## Real user-facing gaps — ordered list (%d unique strings; guests first, then host-side)\n\n' % len(ordered))
    fh.write('| # | en text | first seen in |\n|---|---|---|\n')
    for i, (en, f) in enumerate(ordered, 1):
        fh.write(f'| {i} | {en.replace("|", "\\|")} | {f} |\n')
    fh.write('\n## Policy\n\nBoth rows keep `status=fallback` in the CSV: fallback means "English shown in Khmer mode" until the owner supplies Khmer byte-exact strings. The bilingual checker still passes (fallback is allowed); no row was flipped to translated without an owner string.\n')

print('audit written; ordered gaps:', len(ordered))
print('counts:', {k: len(v) for k, v in groups.items()})
