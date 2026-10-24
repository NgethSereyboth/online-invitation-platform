# Khmer gap — shared header and page furniture (2026-10-24)

Discovery from the post-round-4 audit (FB-61). Every row below is a `<span class="i18n-km">`
slot whose visible text is still **English**, so a Khmer reader sees English in the Khmer UI.
They stay English because rule R3 of `KHMER-TRANSLATION-MAP-2026-10-24.md` forbids inventing
Khmer, and no map row applies to that slot: either the string has no row at all ("—"), or the
row exists under a different file/section and `tools/i18n-apply-khmer-map.py` does not match it
there ("row elsewhere"). Applying either needs a new map row with owner-supplied Khmer.

**Totals:** 72 occurrences, 42 unique strings, 12 pages.

| English in the km slot | occurrences | pages | map |
|---|---|---|---|
| Workspace | 20 | account.html, admin.html, analytics.html, billing.html, dashboard.html, designer.html, guests.html, materials.html, responses.html, templates.html | — |
| Plans | 11 | account.html, admin.html, analytics.html, billing.html, dashboard.html, designer.html, guests.html, materials.html, responses.html, templates.html | — |
| Passkeys | 2 | account.html | — |
| Administration | 1 | admin.html | — |
| Analytics | 1 | analytics.html | row elsewhere |
| Built-in templates now include page structure, palette, section styling, animation, and visual-page layouts. Invitations saved as your own templates appear here too. | 1 | dashboard.html | — |
| Cancel | 1 | dashboard.html | row elsewhere |
| Canva-like design studio for invitations and posters | 1 | dashboard.html | — |
| Canvas zoom | 1 | index.html | — |
| Close | 1 | dashboard.html | — |
| Create from template | 1 | dashboard.html | row elsewhere |
| Create invitation | 1 | dashboard.html | — |
| Delete | 1 | materials.html | — |
| Design invitations that feel premium, personal, and alive. | 1 | dashboard.html | — |
| Designer | 1 | designer.html | — |
| Designer Workspace | 1 | dashboard.html | row elsewhere |
| Event Check-in | 1 | guests.html | — |
| Event type | 1 | dashboard.html | — |
| Filter materials | 1 | index.html | — |
| Guest list, RSVP responses and analytics in one workspace | 1 | dashboard.html | — |
| Guest preview | 1 | index.html | — |
| Invitation name | 1 | dashboard.html | — |
| Khmer + English, light + dark, publish-ready pages | 1 | dashboard.html | — |
| Local mode | 1 | index.html | — |
| Marketplace | 1 | dashboard.html | row elsewhere |
| My invitations | 1 | dashboard.html | — |
| My templates | 1 | dashboard.html | — |
| Online | 1 | checkin.html | — |
| or | 1 | dashboard.html | — |
| Plans &amp; usage | 1 | billing.html | — |
| Publish snapshot | 1 | index.html | — |
| Redo | 1 | index.html | — |
| Sign in to continue working on your invitations and events. | 1 | dashboard.html | — |
| Sign out | 1 | dashboard.html | — |
| Style & motion | 1 | index.html | — |
| Template Studio | 1 | templates.html | row elsewhere |
| Undo | 1 | index.html | — |
| Untitled design | 1 | index.html | — |
| Use this template | 1 | dashboard.html | — |
| Welcome back | 1 | dashboard.html | — |
| ★ Favorites | 1 | dashboard.html | — |
| ＋ New poster | 1 | templates.html | — |

## What the next Khmer round needs

Extend the map with a section per file (`### `src/html/<file>``) carrying these English strings
as `EN` and owner-supplied Khmer as `KM`; `python3 tools/i18n-apply-khmer-map.py` then applies
them by script exactly as FB-54 did. Do not hand-edit `TRANSLATIONS.csv`: `tools/i18n-fallback-audit.py`
pins its fallback count at 305 and has to move in the same item.

Excluded from this list: slots with no Latin letters (`×`) and console hints (`Ctrl K`, `Space`),
which stay Latin by design.
