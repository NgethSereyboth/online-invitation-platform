/* v0.69.0 — admin step-up prompt (ROADMAP §4.2 / §5.9, LT-7.2).
 *
 * Destructive admin routes answer 403 {code:'step_up_required'} until the admin
 * re-verifies with their password (plus a TOTP code when MFA is enabled). This
 * module owns the prompt and an **in-memory** cache of the 30-minute server
 * grant (D-7: no browser-storage persistence, so a reload re-prompts),
 * and `pages/admin/admin.js` retries through it, so every admin page gets the
 * flow without changing each call site.
 *
 * No HTML strings are built except the dialog's own fixed skeleton; user text is
 * set with textContent. Khmer rows do not exist yet (OWNER-QUEUE), so the `km`
 * bank carries the accepted English fallback — the bilingual checker reports
 * those pairs as fallback/PLACEHOLDER rather than a missing counterpart.
 */
(function(){
  'use strict';
  if (window.EInviteAdminStepUp && window.EInviteAdminStepUp.version >= 70) return;

  var TTL_MS = 30 * 60 * 1000;
  var grantUntil = 0;
  var pending = null;

  var STRINGS = {
    en: {
      title: 'Confirm it is you',
      message: 'Destructive admin actions need a fresh sign-in check.',
      password: 'Password',
      code: 'Authenticator code (only when MFA is on)',
      verify: 'Verify',
      cancel: 'Cancel',
      failed: 'Step-up verification failed',
      fallback: 'Your session cannot request a step-up right now.'
    },
    // English fallback until a Khmer map row exists (never hand-written Khmer).
    km: {
      title: 'Confirm it is you',
      message: 'Destructive admin actions need a fresh sign-in check.',
      password: 'Password',
      code: 'Authenticator code (only when MFA is on)',
      verify: 'Verify',
      cancel: 'Cancel',
      failed: 'Step-up verification failed',
      fallback: 'Your session cannot request a step-up right now.'
    }
  };

  function t(key){
    var lang = (document.documentElement.lang || 'en').toString().toLowerCase().startsWith('km') ? 'km' : 'en';
    var bank = STRINGS[lang] || STRINGS.en;
    if (window.EInviteI18n && typeof window.EInviteI18n.t === 'function') {
      var out = window.EInviteI18n.t(key, STRINGS);
      if (out && out !== key) return out;
    }
    return bank[key] || STRINGS.en[key] || key;
  }

  function until(){ return grantUntil; }
  function remember(expiresAt){ grantUntil = Number(expiresAt) || (Date.now() + TTL_MS); }
  function forget(){ grantUntil = 0; }
  function granted(){ return until() > Date.now(); }

  function ask(){
    return new Promise(function(resolve){
      var dialog = document.createElement('dialog');
      dialog.className = 'ei-dialog';
      dialog.setAttribute('aria-labelledby', 'adminStepUpTitle');
      dialog.setAttribute('aria-describedby', 'adminStepUpMessage');
      var opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;

      var form = document.createElement('form');
      form.method = 'dialog';
      form.className = 'ei-dialog-card';

      var head = document.createElement('div');
      head.className = 'ei-dialog-head';
      var icon = document.createElement('span');
      icon.className = 'ei-dialog-icon';
      icon.textContent = '⚿';
      var headText = document.createElement('div');
      var title = document.createElement('h2');
      title.id = 'adminStepUpTitle';
      title.textContent = t('title');
      var message = document.createElement('p');
      message.className = 'ei-dialog-message';
      message.id = 'adminStepUpMessage';
      message.textContent = t('message');
      headText.append(title, message);
      head.append(icon, headText);

      var fields = document.createElement('div');
      fields.className = 'ei-dialog-input';
      var pwLabel = document.createElement('label');
      pwLabel.htmlFor = 'adminStepUpPassword';
      pwLabel.textContent = t('password');
      var pw = document.createElement('input');
      pw.id = 'adminStepUpPassword';
      pw.type = 'password';
      pw.autocomplete = 'current-password';
      pw.required = true;
      var codeLabel = document.createElement('label');
      codeLabel.htmlFor = 'adminStepUpCode';
      codeLabel.textContent = t('code');
      var code = document.createElement('input');
      code.id = 'adminStepUpCode';
      code.inputMode = 'numeric';
      code.autocomplete = 'one-time-code';
      fields.append(pwLabel, pw, codeLabel, code);

      var actions = document.createElement('div');
      actions.className = 'ei-dialog-actions';
      var cancel = document.createElement('button');
      cancel.type = 'button';
      cancel.dataset.cancel = '';
      cancel.textContent = t('cancel');
      var confirm = document.createElement('button');
      confirm.type = 'submit';
      confirm.value = 'confirm';
      confirm.dataset.confirm = '';
      confirm.className = 'ei-primary';
      confirm.textContent = t('verify');
      actions.append(cancel, confirm);

      form.append(head, fields, actions);
      dialog.append(form);
      document.body.append(dialog);

      var done = false;
      function finish(value){
        if (done) return;
        done = true;
        dialog.remove();
        // WCAG 2.4.3: focus goes back to whatever opened the prompt, so a
        // keyboard user is not dropped at the top of the document.
        if (opener && opener.isConnected && typeof opener.focus === 'function') {
          try { opener.focus({ preventScroll: true }); } catch (e) { opener.focus(); }
        }
        resolve(value);
      }
      cancel.addEventListener('click', function(){ dialog.close(); finish(null); });
      dialog.addEventListener('cancel', function(event){ event.preventDefault(); dialog.close(); finish(null); });
      form.addEventListener('submit', function(event){
        event.preventDefault();
        var password = pw.value;
        if (!password) { pw.focus(); return; }
        finish({ password: password, code: code.value.trim() });
      });
      dialog.addEventListener('close', function(){ finish(null); });
      dialog.showModal();
      setTimeout(function(){ pw.focus(); }, 0);
    });
  }

  async function verify(credentials){
    var response;
    try {
      response = await fetch('/api/admin/step-up', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(credentials)
      });
    } catch (error) {
      if (window.uiAlert) window.uiAlert(t('fallback'), { type: 'error' });
      return false;
    }
    var data = {};
    try { data = await response.json(); } catch (error) { data = {}; }
    if (!response.ok || !data.stepUp) {
      if (window.uiAlert) window.uiAlert(data.error || t('failed'), { type: 'error' });
      return false;
    }
    remember(data.expiresAt);
    return true;
  }

  async function request(){
    if (granted()) return true;
    if (pending) return pending;
    pending = (async function(){
      var credentials = await ask();
      if (!credentials) {
        forget();
        return false;
      }
      return verify(credentials);
    })();
    try {
      return await pending;
    } finally {
      pending = null;
    }
  }

  window.EInviteAdminStepUp = Object.freeze({
    version: 70,
    request: request,
    forget: forget,
    granted: granted
  });
})();
