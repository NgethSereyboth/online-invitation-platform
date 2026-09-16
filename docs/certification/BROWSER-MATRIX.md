# Browser Matrix — 4 desktop + 2 mobile

> **Phase 3 deliverable.** Companion file to [`CERTIFICATION.md`](./CERTIFICATION.md) §2. This document defines the per-browser acceptance procedure for the six target browsers and links the existing automated coverage.
>
> **Build-tool-free constraint.** The platform is **vanilla JS** — no bundler, no transpiler, no framework. Browser compatibility is therefore primarily a function of:
> - **CSS feature support** — the editor uses CSS `grid`, `flexbox`, `clamp()`, `min()/max()/calc()`, `aspect-ratio`, `:has()`, container queries (limited — only `@container` for the timeline panel), CSS nesting (only in `editor-styles.css`). The `theme-hardening.css` + `accessibility-v12.css` files contain the fallback declarations for older engines.
> - **WebCrypto support** — ES256 passkey registration + authentication via `navigator.credentials.create()` / `.get()` (see `src/js/account-security-v13.js`). Requires WebAuthn Level 1 + WebCrypto subtle ECDSA.
> - **WebGL support** — the V22 scene model (`src/js/scene-model-v22.js` + `src/js/webgl-scene-backend-v22.js`) requires WebGL 2.0 for the GPU raster path; the software fallback (`src/js/scene-render-worker-v22.js`) runs in a Web Worker if WebGL is unavailable. See `tests/v22_1_7_gpu_fallback_test.py` for the fallback contract.
>
> **Existing automated coverage.**
> - `tests/browser_runtime.py` — the cross-platform Playwright Chromium launcher used by every browser-runtime test in the suite. Exports `launch_chromium(playwright)` (with `--no-sandbox` on Linux + `OPENSSL_CONF` work-around on Windows), `dismiss_editor_onboarding(page)`, `open_event_details(page)`, and `wait_for_reachable_control(page, selector)` (diagnoses pointer-events + z-index + scroll-into-view races). See [`tests/browser_runtime.py`](../../tests/browser_runtime.py).
> - `tests/inline_editor_runtime_test.py` — a 429-line real-Chromium DOM/runtime smoke for the editor. Inlines the app's local CSS/JS via `page.set_content()` (the test environment blocks network navigation to localhost) and executes the real editor in Chromium. Catches runtime races that static tests cannot. See [`tests/inline_editor_runtime_test.py`](../../tests/inline_editor_runtime_test.py).
>
> **Coverage gap.** Both existing automated tests run only on Chromium (Playwright's bundled Chromium). The matrix below extends that to Firefox, Safari, Edge, Safari iOS, and Chrome Android via manual + Playwright-multi-browser procedures.

---

## 1. Target browsers

| ID | Browser | Version target | Engine | Automation |
|----|---------|----------------|--------|------------|
| B1 | Chrome (desktop) | latest stable | Blink + V8 | `tests/browser_runtime.py::launch_chromium` (existing) + `tests/inline_editor_runtime_test.py` (existing). Playwright `channel: 'chrome'` for the system Chrome. |
| B2 | Firefox (desktop) | latest ESR + latest stable | Gecko + SpiderMonkey | Playwright `channel: 'firefox'` (ESR + stable channels). Manual: load `about:config` and disable `privacy.resistFingerprinting` for the test profile (it breaks the WebGL renderer fingerprint used by `gpu-projection-v22.js`). |
| B3 | Safari (desktop) | latest stable (macOS 14+) | WebKit + JavaScriptCore | Manual + `playwright-webkit` (the WebKit bundle is the closest automation analog to Safari; a true Safari test requires macOS + `safaridriver`). |
| B4 | Edge (desktop) | latest stable | Blink + V8 (Chromium-based since 2020) | Playwright `channel: 'msedge'`. |
| B5 | Safari iOS | latest stable (iOS 17+) | WebKit (mobile) | Manual on a real device or `BrowserStack` / `LambdaTest` iOS Safari session. iOS Simulator Safari is also acceptable for the desktop-only gates (G3-G5); the WebGL + WebAuthn gates require a real device. |
| B6 | Chrome Android | latest stable (Android 13+) | Blink (mobile) | Manual on a real device or `BrowserStack` / `LambdaTest` Android Chrome session. Chrome on Android supports `chrome://inspect` remote debugging — recommended for the AI-agent panel test (G4). |

---

## 2. Acceptance gates (identical across all six browsers)

A browser is certified only when **all six** of the following hold.

| # | Gate | How to verify |
|---|------|---------------|
| G1 | All 16 HTML pages render with no `console.error` | Open each page in the browser; capture the dev-tools console. Third-party favicon/YouTube/SoundCloud origin errors are excluded (see `tests/v14_live_server_acceptance_test.py::serious_console` — the predicate returns False for any console message containing `favicon`, `youtube`, `soundcloud`, or `net::err_name_not_resolved`). |
| G2 | The editor loads with `document.documentElement.dataset.editorReady === 'true'` | Open `/dashboard.html` → log in or register → create invitation from a built-in template → open the editor. The `<html>` element gains `data-editor-ready="true"` when `editor-core.js` finishes its init handshake (see `tests/inline_editor_runtime_test.py` line 12 for the assertion contract). |
| G3 | The public RSVP form submits | Open `/i/{slug}` → fill the RSVP form (name, status = "Yes, joyfully", count = 1) → submit. The browser network tab should show `POST /api/public/{slug}/rsvps` returning 201 with `{"id":"...","saved":true,"updated":false}`. The host dashboard (`/invitations/{id}/responses`) should show the new RSVP row within one refresh. |
| G4 | The AI agent panel renders | Open the editor → click the AI agent icon (toolbar). The panel should render without runtime errors; the tool registry (`src/js/ai-agent-tool-registry-v28.js`) should load (visible in the network tab as `ai-creative-agent-v28.js` + `ai-assistant-loader-v27.js`); typing a prompt and clicking "Plan" should call `POST /api/invitations/{id}/ai/plan` and return a plan with at least one tool call. |
| G5 | Bilingual EN↔KH toggle works | On any bilingual page (dashboard, editor, public), click the language toggle (top-right `EN | ភាសាខ្មែរ` pill). The page should re-render in the chosen script without a full page reload; the choice persists in `localStorage['einvite.lang']` across sessions. Verify Khmer text shaping: `សិរី និង សុភា` should render with correct complex-text shaping (no broken conjuncts, no missing vowel signs) — see [`docs/i18n/KHMER-TYPOGRAPHY.md`](../i18n/KHMER-TYPOGRAPHY.md) for the W3C reference. |
| G6 | No CSP violation report in the dev-tools console | The CSP is `script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'; frame-src 'self'` (see `server.py::end_headers`). If a browser blocks an inline script or a third-party origin, a CSP violation report appears in the console. There must be **zero** violation reports across all 16 pages. |

---

## 3. Per-browser procedure

### 3.1 Chrome (desktop)

**Existing automated coverage:**
- `tests/browser_runtime.py::launch_chromium(playwright)` is the cross-platform launcher.
- `tests/inline_editor_runtime_test.py` runs the editor inline via `page.set_content()`.
- `tests/v14_live_server_acceptance_test.py` runs the full walkthrough against the real HTTP server.

**Manual procedure for gates G3 (RSVP) + G5 (bilingual toggle):**
1. Launch Chrome with a clean profile: `chromium --user-data-dir=/tmp/einvite-cert-chrome http://127.0.0.1:8080/dashboard.html`.
2. Walk the `tests/v14_live_server_acceptance_test.py` flow manually (register → create invitation → publish → submit RSVP → verify).
3. Toggle the language pill to `ភាសាខ្មែរ`; verify Khmer shaping.
4. Check the dev-tools console for CSP violations.

**Known-good versions:** Chrome 130+ (Chromium 130 ships the `:has()` selector without a flag, which the editor uses for the timeline panel).

---

### 3.2 Firefox (desktop)

**Both channels tested:**
- **Firefox ESR** (currently 115.x — the channel enterprises + Debian stable ship). ESR is the conservative target; if ESR fails, the platform must ship a fallback.
- **Firefox stable** (currently 131+).

**Procedure:**
1. Install both channels (they coexist; ESR installs as `firefox-esr` on Debian/Ubuntu, stable as `firefox`).
2. Launch each with a clean profile: `firefox -P --no-remote` → create a profile named `einvite-cert-esr` (or `-stable`).
3. Walk gates G1–G6.
4. **ESR-specific note:** Firefox ESR 115 does NOT support the `:has()` selector (it landed in 121). The editor's timeline panel uses `:has()` for the active-tab indicator. Verify the visual fallback (`theme-hardening.css` ships a `.is-active` class fallback that the JS sets when `:has()` is unsupported — see `src/js/editor-suite.js` for the `CSS.supports('selector(:has(*))')` check).

---

### 3.3 Safari (desktop)

**Requirement:** macOS 14 (Sonoma) or later. Safari 17+ is required because:
- Safari 16.4 introduced `:has()` selector support.
- Safari 17 introduced WebAuthn PRF (Platform Rendered Function) extensions used by the passkey flow.
- Safari 17.4 introduced `WebCrypto subtle ECDSA P-256` in a worker (used by `scene-render-worker-v22.js` for the GPU fallback path — verified by `tests/v22_1_7_gpu_fallback_test.py`).

**Procedure:**
1. Use `playwright-webkit` (the WebKit bundle is the closest automation analog to Safari) OR `safaridriver` (Safari's WebDriver implementation, bundled with macOS).
2. For `safaridriver`: enable `Develop → Allow Remote Automation` in Safari's menu, then `safaridriver --port 4444` and connect Playwright via `webdriver:safari`.
3. Walk gates G1–G6.
4. **Safari-specific note:** Safari's ITP (Intelligent Tracking Prevention) blocks third-party cookies by default. The eInvite session cookie is `SameSite=Lax` (not `None`), so ITP does not affect it. Verify by checking `document.cookie` returns the `einvite_session` cookie on the dashboard after login.

---

### 3.4 Edge (desktop)

**Note:** Edge is Chromium-based (since 2020). The Blink + V8 engine is identical to Chrome's. The Edge-specific gates are:
- The Microsoft Defender SmartScreen reputation check (does not affect a localhost dev URL).
- The Edge `Tracking prevention` setting (default = `Balanced`) — this is more permissive than Safari ITP but stricter than Chrome's default. Verify the session cookie persists across reloads.
- The Edge Collections / Sidebar feature does not interfere with the editor's right-side panel (it shouldn't — verify the `aside.right` element in the editor DOM remains visible when the sidebar is open).

**Procedure:**
1. Launch Edge with `--user-data-dir=/tmp/einvite-cert-edge`.
2. Walk gates G1–G6.
3. Use Playwright `channel: 'msedge'` for automation.

---

### 3.5 Safari iOS

**Requirement:** iOS 17+ on a real device (or iOS Simulator for the desktop-equivalent gates G1, G3, G5 — but NOT G2 WebAuthn or G4 AI-agent because the simulator does not have a Secure Enclave for passkeys).

**Procedure:**
1. On a real iPhone/iPad running iOS 17+:
   - Open Safari → navigate to the public invitation URL.
   - Submit the RSVP form (gate G3).
   - Toggle the language to Khmer (gate G5).
   - Open the host dashboard, register an account, register a passkey via Face ID (gate G2 — requires WebAuthn on iOS, which is supported since iOS 13.4; the ES256 P-256 curve is supported since iOS 15).
2. For the AI agent panel (gate G4): the panel is responsive (`mobile-editor-v14.js` ships the mobile layout). Verify the panel opens, the prompt input is reachable by the iOS software keyboard without occluding the submit button (the editor's `safe-area-inset-bottom` CSS token — see `tests/v16_windows_ui_hardening_test.py` line 24 — handles this).
3. **iOS-specific note:** Safari iOS limits localStorage to 5 MB per origin (Chrome desktop is 10 MB). The editor's CRDT checkpoint (`y-indexeddb` planned in Phase 4b — currently not yet wired) could exceed this on a very large invitation. For Phase 3, the platform does not yet use IndexedDB, so this is a non-issue. Document as a Phase 4 risk.

---

### 3.6 Chrome Android

**Requirement:** Android 13+ on a real device (or Android Emulator for the desktop-equivalent gates). Chrome on Android is the same Blink engine as desktop Chrome — the gates that fail on Android are usually touch-event-related (the editor's `direct-manipulation-v24.js` was written for pointer events, which Chrome Android supports since v55).

**Procedure:**
1. On a real Android device:
   - Open Chrome → navigate to the public invitation URL.
   - Submit the RSVP form (gate G3).
   - Toggle the language to Khmer (gate G5).
   - Open the host dashboard, register, log in.
2. For the editor (gate G2): open the editor on a phone in portrait orientation. Verify the editor chrome collapses to the mobile layout (`mobile-editor-v14.js`).
3. For the AI agent panel (gate G4): use `chrome://inspect` to remote-debug the panel from a desktop Chrome. Verify the panel renders + a plan is returned.
4. **Android-specific note:** Chrome Android limits the WebGL context to a single concurrent context per page. The V22 scene model opens ONE WebGL context (`src/js/webgl-scene-backend-v22.js`); verify no `WebGL context lost` event fires during the editor session.

---

## 4. Cross-browser feature matrix

| Feature | Chrome | Firefox ESR | Firefox stable | Safari | Edge | Safari iOS | Chrome Android |
|---------|--------|-------------|----------------|--------|------|------------|----------------|
| `:has()` selector | 105+ | 121+ (stable) / ✗ (ESR 115) | 121+ | 15.4+ | 105+ | 15.4+ | 105+ |
| `aspect-ratio` | 88+ | 89+ | 89+ | 15+ | 88+ | 15+ | 88+ |
| `clamp()` | 79+ | 75+ | 75+ | 13.1+ | 79+ | 13.4+ | 79+ |
| Container queries (`@container`) | 105+ | 110+ | 110+ | 16+ | 105+ | 16+ | 105+ |
| WebAuthn (passkeys, ES256) | 67+ | 60+ (ESR) / 60+ | 60+ | 13.4+ (PRF in 17+) | 87+ | 13.4+ | 70+ |
| WebCrypto subtle ECDSA | 37+ | 34+ (ESR) / 34+ | 34+ | 11+ (worker in 17.4+) | 12+ | 11+ | 37+ |
| WebGL 2.0 | 56+ | 51+ | 51+ | 15+ | 79+ | 15+ | 56+ |
| `IntersectionObserver` | 51+ | 55+ | 55+ | 12.1+ (Safari iOS 12.2+) | 15+ | 12.2+ | 51+ |
| `<img loading="lazy">` | 76+ | 75+ | 75+ | 15.4+ (Safari iOS 15.4+) | 79+ | 15.4+ | 76+ |

The `:has()` selector and Firefox ESR 115 is the **only** known feature gap. The editor's `editor-suite.js` includes a `CSS.supports('selector(:has(*))')` runtime check that activates the `.is-active` class fallback when `:has()` is unsupported — verified by `tests/v16_windows_ui_hardening_test.py` line 24 (the `transform:none!important` token is the fallback declaration).

---

## 5. Cross-references

- [`CERTIFICATION.md`](./CERTIFICATION.md) §2 — executive summary.
- [`tests/browser_runtime.py`](../../tests/browser_runtime.py) — existing Chromium launcher.
- [`tests/inline_editor_runtime_test.py`](../../tests/inline_editor_runtime_test.py) — existing Chromium editor smoke test.
- [`tests/v14_live_server_acceptance_test.py`](../../tests/v14_live_server_acceptance_test.py) — existing real-HTTP walkthrough.
- [`tests/v22_1_7_gpu_fallback_test.py`](../../tests/v22_1_7_gpu_fallback_test.py) — WebGL fallback contract.
- [`tests/v16_windows_ui_hardening_test.py`](../../tests/v16_windows_ui_hardening_test.py) — file-content portability assertions (the `:has()` fallback tokens).
- [`docs/i18n/KHMER-TYPOGRAPHY.md`](../i18n/KHMER-TYPOGRAPHY.md) — W3C Khmer Script Resources.
- [`docs/a11y/WCAG-AA-AUDIT.md`](../a11y/WCAG-AA-AUDIT.md) — WCAG 2.1 AA audit (Phase 2b deliverable; cross-referenced from gate G5 because Khmer rendering quality is also an accessibility concern).
