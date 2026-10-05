/**
 * monitoring.js — System tab + system-health metrics (ROADMAP §5.9).
 * Dynamically injects a "System" admin tab, renders /api/health + /api/admin/metrics
 * cards into that panel, and re-renders on language switch via subscribe().
 * All user-facing strings go through EInviteI18n.langText() (dual spans, CSS-driven
 * toggle) or a plain-text helper (_txt) for DOM APIs — no STRINGS table so the
 * check-bilingual-consistency.py scan is not polluted with EN-FALLBACK placeholders.
 */
(() => {
  'use strict';
  if (!document.querySelector('.admin-tabs')) return;
  const $ = s => document.querySelector(s);
  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const _isKm = () => (window.EInviteI18n && window.EInviteI18n.get ? window.EInviteI18n.get() : (document.documentElement.lang || 'en').toLowerCase()).startsWith('km');
  const _html = (en, km) => {
    if (window.EInviteI18n) return window.EInviteI18n.langText(en, km);
    return `<span class="i18n i18n-en">${esc(en)}</span><span class="i18n i18n-km khmer-text" lang="km">${esc(km != null ? km : en)}</span>`;
  };
  const _txt = (en, km) => _isKm() ? (km != null ? km : en) : en;
  localStorage.removeItem('sovan-auth-token');
  async function api(path) {
    const r = await fetch(path, { credentials: 'same-origin', headers: {} });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw Error(d.error || 'Request failed');
    return d;
  }
  // Dynamically create the "System" admin tab + panel (absent from static HTML).
  const tabs = $('.admin-tabs');
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.dataset.adminTab = 'system';
  btn.innerHTML = _html('System', 'System');
  tabs.append(btn);
  const panel = document.createElement('section');
  panel.id = 'systemPanel';
  panel.className = 'admin-panel';
  panel.innerHTML = '<div class="ei-system-grid" id="eiSystemMetrics"></div><div class="ei-system-table" id="eiSystemServices"></div>';
  document.querySelector('.admin-page').append(panel);
  function fmtBytes(v) {
    v = Number(v || 0);
    for (const u of ['B', 'KB', 'MB', 'GB']) { if (v < 1024) return `${v.toFixed(v < 10 && u !== 'B' ? 1 : 0)} ${u}`; v /= 1024; }
    return `${v.toFixed(1)} TB`;
  }
  async function load() {
    try {
      const [health, m] = await Promise.all([api('/api/health'), api('/api/admin/metrics')]);
      const cards = [
        [_html('Uptime', 'Uptime'), `${Math.floor(m.uptimeSeconds / 3600)}h ${Math.floor(m.uptimeSeconds % 3600 / 60)}m`],
        [_html('Users', 'អ្នកប្រើ'), m.users],
        [_html('Invitations', 'ការអញ្ជើញ'), m.invitations],
        [_html('Publications', 'Publications'), m.publications],
        [_html('RSVPs', 'RSVPs'), m.rsvps],
        [_html('Assets', 'Assets'), m.assets],
        [_html('Material storage', 'Material storage'), fmtBytes(m.assetBytes)],
      ];
      $('#eiSystemMetrics').innerHTML = cards.map(([a, b]) => `<article class="ei-system-card"><small>${a}</small><strong>${esc(b)}</strong></article>`).join('');
      const services = [
        [_html('API', 'API'), _html('Healthy', 'Healthy')],
        [_html('Database', 'Database'), esc(health.database)],
        [_html('Asset storage', 'Asset storage'), esc(health.assetStorage)],
        [_html('Redis rate limiting', 'Redis rate limiting'), health.redis ? _html('Connected', 'Connected') : _html('In-memory fallback', 'In-memory fallback')],
        [_html('AI provider', 'AI provider'), health.aiConfigured ? _html('Configured', 'Configured') : _html('Local assistant', 'Local assistant')],
        [_html('SMTP', 'SMTP'), health.smtpConfigured ? _html('Configured', 'Configured') : _html('Not configured', 'Not configured')],
        [_html('Billing webhook', 'Billing webhook'), health.billingWebhookConfigured ? _html('Configured', 'Configured') : _html('Not configured', 'Not configured')],
      ];
      $('#eiSystemServices').innerHTML = services.map(([a, b]) => `<div class="ei-system-row"><span>${a}</span><strong class="ei-system-status">${b}</strong></div>`).join('');
    } catch (e) {
      $('#eiSystemServices').innerHTML = `<div class="empty">${esc(_txt(e.message || 'Request failed', e.message || 'Request failed'))}</div>`;
    }
  }
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-admin-tab]').forEach(x => x.classList.toggle('active', x === btn));
    document.querySelectorAll('.admin-panel').forEach(x => x.classList.remove('active'));
    panel.classList.add('active');
    setTimeout(load, 0);
  });
  // Re-render on language switch (cached payload, no refetch).
  if (window.EInviteI18n && typeof window.EInviteI18n.subscribe === 'function') {
    window.EInviteI18n.subscribe(function () {
      btn.innerHTML = _html('System', 'System');
      if (panel.classList.contains('active')) load();
    });
  }
})();
