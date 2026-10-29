# Real-device checklist — mid-range Android phone

**Why this file exists.** Headless Chromium on this machine has no Khmer ICU data, no IME, no
Android share sheet and no phone GPU, so the gate matrix cannot answer these questions. This is the
honest substitute: one screen per step, each with what to do and what should happen.

**Where to run it.** `<DEMO URL>` is the demo's base URL:

- **Today:** `http://127.0.0.1:8941/` — a *local* demo. **A phone cannot reach localhost.**
  Treat the steps below as runnable on the desktop browser now, and as the phone list once the demo
  has a host the phone can open. The missing public host is recorded in
  `artifacts/next-work/OWNER-QUEUE.md` (A-4).
- **When the host exists:** put its URL on the line below and replace every `<DEMO URL>` with it.
  Nothing else in this file changes.

```
Phone URL: ______________________________     Build/commit: ____________________
Phone model: ___________________________     Android version: __________________
Browser:        ________________________     Date: ___________________________
```

Sign in as `demo@einvite.test`; the password is in `FREEBUFF-ANSWERS-2026-10-28.md`
(`## Demo credentials`) — never paste it into this file.

Mark each step **PASS**, **FAIL** or **SKIP** and note what happened. A failure needs a screenshot,
the step number and the URL; file it with the rules in `FREEBUFF-OWNER-INBOX.md` so it can jump the
queue as `INBOX-n`.

---

## 1. Khmer keyboard typing in the editor

**Do:** open `<DEMO URL>/index.html`, sign in, open Dashboard and the demo wedding invitation in the
editor, tap the bride's name on the canvas, clear it, and type `សុភា` with the phone's Khmer keyboard.
The same invitation's guest page is `/i/demo-wd-royal-maroon-gold` (steps 4–10).

**Expected:** every cluster appears in order as typed; no Latin fallback, no blank boxes, no
duplicated vowels; the caret stays after the last cluster. The text is still there after a reload.

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

## 2. Khmer paste into the editor

**Do:** copy `សូមគោរពអញ្ជើញ` from another app, paste it into the same field. Then paste a two-line
Khmer block from a message.

**Expected:** the paste lands as one run, clusters intact, no mojibake; two-line paste keeps its
line break or wraps cleanly. Reload keeps the pasted text.

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

## 3. Editor at 375 px

**Do:** open `<DEMO URL>/dashboard.html` → the demo wedding invitation at phone width in portrait.
Select an object, use the layers panel, nudge
with the arrow pad once, undo once.

**Expected:** no horizontal page scroll; the toolbar is one row; the canvas fits; handles are
reachable with a thumb; the layer list scrolls inside its own panel; nudge moves exactly 1 px and
undo restores it. No control sits under the notch or the gesture bar.

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

## 4. Opening an invitation link

**Do:** open `<DEMO URL>/i/demo-wd-royal-maroon-gold` from a chat app (not the address bar), then
from the address bar. Let the opening scene play, then tap "Open invitation".

**Expected:** the page loads under 3 s on 4G; the scene fades; the invitation is readable without
zooming; no blank flash; the address bar colour matches the page; back returns to the chat.

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

## 5. RSVP — success

**Do:** on the same invitation, fill name, attendance = yes, guest count 2, submit.

**Expected:** a clear confirmation with the name and count; the button shows a pending state while
sending and cannot be double-submitted; reloading keeps the submitted state (or says it was already
recorded) rather than showing an empty form.

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

## 6. RSVP — error

**Do:** enable airplane mode (or block the site in the browser's data saver), submit an RSVP, then
restore the connection and submit again.

**Expected:** a readable error in the current language — not a raw `HTTP 500`/`TypeError` — with a
retry path; the typed values are not lost; the retry succeeds.

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

## 7. Music play / pause

**Do:** tap the music control on the invitation, lock the phone for 10 s, unlock, pause, play again.

**Expected:** audio starts only after the tap (no autoplay block error shown), the icon reflects
playing/paused, it survives the lock screen, and it pauses when another app takes audio focus.

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

## 8. Language switch

**Do:** switch the guest page to Khmer, read the whole page, then switch back to English. Reload.

**Expected:** headings, body, RSVP labels, buttons and the language toggle all switch together; no
half-translated block; Khmer line breaks do not split clusters; the choice survives the reload.

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

## 9. Share sheet — Telegram, Messenger, WhatsApp

**Do:** tap Share on the invitation, choose Telegram, cancel, repeat for Messenger and WhatsApp.

**Expected:** the Android share sheet opens with a preview that contains the invitation title and
URL; each app receives a working link; cancelling returns to the invitation with no state loss; no
app opens a blank composer.

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

## 10. Copy link

**Do:** tap Copy link, then paste into a message to yourself.

**Expected:** the clipboard holds the full `https://…/i/…` URL (not `undefined`, not a relative
path), and a short confirmation appears.

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

## 11. Khmer PDF and PNG export

**Do:** in the editor, open Export, choose PDF (bleed 0 with crop marks off, then 3 mm + marks) and
PNG 1×, for the Khmer wedding template.

**Expected:** the download completes; the PDF opens in the phone viewer with the Khmer face (not
boxes) and the same layout as the canvas; the PNG is 420 × 640 for 1× and sharp; a 3 mm bleed sheet
keeps the trim artwork and puts marks only in the margin. Report the file sizes.

PDF size: ________ KB   PNG size: ________ KB

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

## 12. Two tabs

**Do:** open the same invitation in two browser tabs. Edit and save in tab A, then edit and save in
tab B. Also open a second invitation in a new tab.

**Expected:** tab B either shows a named "changed in another session" message and a reload path, or
saves cleanly; it never half-renders or silently discards tab A's save. Opening a different
invitation in another tab does not disturb the first.

Result: ☐ PASS ☐ FAIL ☐ SKIP — notes: ______________________________

---

## What is already known, so it is not re-reported

- **iPhone/Safari** is out of scope for this pass; this list is Android Chrome.
- **The phone cannot reach the local demo.** Until A-4 has a host, run the list on the desktop
  browser at 375 px and mark the phone-only items (share sheet, keyboard, audio focus) SKIP.
- The automated gates cover Khmer shaping, CSP, contrast, layout at 320/375/1440 and export
  fidelity; a failure here that the gates pass is a real-device finding, not a duplicate.
