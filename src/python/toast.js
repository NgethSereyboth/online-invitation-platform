/**
 * V2-UX-7 (ROADMAP-V2 §3.7) — Toast notification system.
 *
 * A tiny, dependency-free toast stack. Exposes a single global:
 *
 *     window.EInviteToast.show({ type, message_en, message_km, duration })
 *
 *   - type:        'success' | 'error' | 'info' | 'warning' (default 'info')
 *   - message_en:  required English text
 *   - message_km:  required Khmer text
 *   - duration:    ms before auto-dismiss (default 4000; pass 6000 for errors)
 *
 * Layout: top-right fixed `#toast-stack` container (auto-created if missing).
 * Stack semantics: newest at the top; max 5 visible; oldest is dismissed
 * when a 6th would arrive.
 *
 * Accessibility:
 *   - The container carries `aria-live="polite"` + `aria-atomic="false"` so
 *     screen readers announce each new toast without stealing focus.
 *   - Each toast is `role="status"`.
 *   - The close button is a real `<button>` with a bilingual `aria-label`.
 *   - Hover/focus pauses the auto-dismiss timer (a11y nicety).
 *   - `@media (prefers-reduced-motion: reduce)` disables the slide-in.
 *
 * Design tokens: reuses `--app-bg`, `--app-surface`, `--app-text`,
 * `--app-muted`, `--app-line`, `--danger`, `--app-good`, `--app-warn`,
 * `--app-accent-2`, `--app-shadow`, `--app-radius`. If ux-9 ever defines a
 * global `--info` token, the `.toast--info` border picks it up automatically;
 * falls back to `--app-accent-2`.
 *
 * IIFE shape mirrors `host-signup-sheets.js` / `host-polls.js`. Idempotent:
 * if the bundle is somehow loaded twice, the second IIFE no-ops.
 */
(function () {
  'use strict';

  if (window.EInviteToast) return; // idempotent — already defined

  /** Bilingual strings for the toast chrome itself (close button label). */
  var STRINGS = {
    close: { en: 'Close', km: 'បិទ' }
  };

  var MAX_VISIBLE = 5;
  var DEFAULT_DURATION = 4000;
  var VALID_TYPES = { success: 1, error: 1, info: 1, warning: 1 };
  var LEAVE_TIMEOUT_MS = 280; // matches the --leave transition in toast.css

  /** Pick the active language: explicit window.EInviteLang, then <html lang>. */
  function activeLang() {
    if (window.EInviteLang === 'km') return 'km';
    if (window.EInviteLang === 'en') return 'en';
    var htmlLang = String(document.documentElement.lang || '').toLowerCase();
    if (htmlLang === 'km' || htmlLang.indexOf('km-') === 0) return 'km';
    return 'en';
  }

  /** Find or create the top-right `#toast-stack` container. */
  function getStack() {
    var stack = document.getElementById('toast-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.id = 'toast-stack';
      stack.className = 'toast-stack';
      stack.setAttribute('aria-live', 'polite');
      stack.setAttribute('aria-atomic', 'false');
      document.body.appendChild(stack);
    }
    return stack;
  }

  /** Bilingual close-button label. */
  function closeLabel() {
    var lang = activeLang();
    return STRINGS.close[lang] || STRINGS.close.en;
  }

  /** Per-type icon glyph (no external icon font — kept inline). */
  function iconFor(type) {
    switch (type) {
      case 'success': return '\u2713';        // ✓
      case 'error':   return '\u26A0';        // ⚠
      case 'warning': return '\u26A0';        // ⚠
      case 'info':
      default:        return '\u2139';        // ℹ
    }
  }

  /**
   * Show a toast.
   *
   * @param {object} opts
   * @param {string} opts.type        'success' | 'error' | 'info' | 'warning'
   * @param {string} opts.message_en  English message (required)
   * @param {string} opts.message_km  Khmer message (required)
   * @param {number} [opts.duration]  ms before auto-dismiss (default 4000)
   * @returns {HTMLElement} the toast element (for testing)
   */
  function show(opts) {
    opts = opts || {};
    var type = VALID_TYPES[opts.type] ? opts.type : 'info';
    var lang = activeLang();
    var msg = (lang === 'km' ? opts.message_km : opts.message_en) ||
              opts.message_en || opts.message_km || '';
    var duration = Number(opts.duration) > 0 ? Number(opts.duration) : DEFAULT_DURATION;

    var stack = getStack();

    // Enforce max-visible: dismiss oldest from the top (stack is newest-first).
    while (stack.children.length >= MAX_VISIBLE) {
      var oldest = stack.lastElementChild;
      if (!oldest) break;
      dismiss(oldest);
    }

    var toast = document.createElement('div');
    toast.className = 'toast toast--' + type + ' toast--enter';
    toast.setAttribute('role', 'status');
    toast.setAttribute('data-toast', '');

    var icon = document.createElement('span');
    icon.className = 'toast__icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = iconFor(type);

    var message = document.createElement('span');
    message.className = 'toast__message';
    message.textContent = msg;
    // Hint the language for screen readers + the :lang(km) rule (ux-5 §3.5).
    message.lang = lang;

    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'toast__close';
    close.setAttribute('aria-label', closeLabel());
    close.textContent = '\u00D7'; // ×
    close.addEventListener('click', function () { dismiss(toast); });

    toast.appendChild(icon);
    toast.appendChild(message);
    toast.appendChild(close);

    // Insert at top (newest first), then promote to `--visible` on the next
    // frame so the CSS transition runs (slide-in-from-right + fade).
    stack.insertBefore(toast, stack.firstChild);
    requestAnimationFrame(function () {
      toast.classList.add('toast--visible');
      toast.classList.remove('toast--enter');
    });

    // Auto-dismiss timer (stored on the element so manual close + hover-pause
    // can cancel it).
    toast._einviteToastTimer = setTimeout(function () { dismiss(toast); }, duration);

    // Pause auto-dismiss on hover/focus; resume (with a short grace period)
    // on leave/blur so keyboard users can read the toast at their own pace.
    function pause() {
      if (toast._einviteToastTimer) {
        clearTimeout(toast._einviteToastTimer);
        toast._einviteToastTimer = null;
      }
    }
    function resume() {
      pause();
      toast._einviteToastTimer = setTimeout(function () { dismiss(toast); }, 1500);
    }
    toast.addEventListener('mouseenter', pause);
    toast.addEventListener('mouseleave', resume);
    toast.addEventListener('focus', pause);
    toast.addEventListener('blur', resume);

    return toast;
  }

  /** Animate out + remove a toast (idempotent). */
  function dismiss(toast) {
    if (!toast || !toast.parentNode) return;
    if (toast._einviteToastDismissed) return;
    toast._einviteToastDismissed = true;

    if (toast._einviteToastTimer) {
      clearTimeout(toast._einviteToastTimer);
      toast._einviteToastTimer = null;
    }

    toast.classList.add('toast--leave');
    toast.classList.remove('toast--visible');

    var remove = function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    };
    var fallback = setTimeout(remove, LEAVE_TIMEOUT_MS);
    toast.addEventListener('transitionend', function handler(ev) {
      if (ev.target !== toast) return;
      clearTimeout(fallback);
      toast.removeEventListener('transitionend', handler);
      remove();
    });
  }

  window.EInviteToast = { show: show };
})();
