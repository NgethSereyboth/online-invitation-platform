/* v0.64.0 — admin shell (ROADMAP-v0.54-to-v1.0 §5.1)
 *
 * Orchestrates the admin page: stat cards grid + system status banner +
 * tab navigation between the 9 admin modules. Polls /api/admin/metrics-v2
 * + /api/admin/system-status every 30s.
 *
 * Replaces the legacy admin.js (kept for backward-compat with the old
 * users/templates/invitations/ai panels — the new modules layer on top).
 */
(function(){
  'use strict';
  if (window.EInviteAdminShell && window.EInviteAdminShell.version >= 64) return;

  const STRINGS = {
    en: {
      title:'Administration',
      loading:'Loading…',
      noData:'No data yet.',
      masked:'masked',
      polling:'Polling every 30s',
      suspended:'Suspended',
      active:'Active',
      notAvailable:'n/a',
      refresh:'Refresh now',
      error:'Failed to load admin data',
      unauthorized:'Administrator access required',
    },
    km: {
      title:'ការគ្រប់គ្រង',
      loading:'កំពុងផ្ទុក…',
      noData:'មិនមានទិន្នន័យនៅឡើយ។',
      masked:'បិទបាំង',
      polling:'ធ្វើបច្ចុប្បន្នភាពរៀងរាល់ ៣០ វិនាទី',
      suspended:'បានផ្អាក',
      active:'សកម្ម',
      notAvailable:'គ្មាន',
      refresh:'ធ្វើបច្ចុប្បន្នភាព',
      error:'បរាជ័យក្នុងការផ្ទុកទិន្នន័យអ្នកគ្រប់គ្រង',
      unauthorized:'ត្រូវការសិទ្ធិអ្នកគ្រប់គ្រង',
    }
  };

  function locale(){ return (document.documentElement.lang || 'en').startsWith('km') ? 'km' : 'en'; }
  function t(key){ const l = locale(); return (STRINGS[l] && STRINGS[l][key]) || STRINGS.en[key] || key; }
  function esc(v){ return String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  function formatNumber(n){
    if (n == null) return '—';
    try { return new Intl.NumberFormat(locale()==='km' ? 'en-US' : 'en-US').format(n); }
    catch(e){ return String(n); }
  }
  function formatBytes(b){
    if (!b) return '0 B';
    const units = ['B','KB','MB','GB','TB'];
    let i=0; let v=b;
    while (v >= 1024 && i < units.length-1){ v/=1024; i++; }
    return `${v.toFixed(i===0?0:1)} ${units[i]}`;
  }
  function formatDelta(card){
    if (card.delta7d == null) return '';
    const sign = card.delta7d > 0 ? '+' : '';
    return `<small class="ei-stat-card-delta">7d: ${sign}${formatNumber(card.delta7d)}</small>`;
  }

  const api = window.EInviteAdminAPI || {
    async get(path){
      const r = await fetch(path, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
      if (!r.ok) {
        if (r.status === 401 || r.status === 403) throw new Error(t('unauthorized'));
        throw new Error(`${r.status} ${r.statusText}`);
      }
      const ct = r.headers.get('Content-Type') || '';
      if (ct.includes('application/json')) return r.json();
      return r.text();
    },
    async send(path, method, body){
      const r = await fetch(path, {
        method, credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: body == null ? undefined : JSON.stringify(body),
      });
      let data;
      try { data = await r.json(); } catch(e){ data = {}; }
      if (!r.ok) throw new Error(data.error || `${r.status} ${r.statusText}`);
      return data;
    },
  };

  function renderStatCards(payload){
    const host = document.getElementById('statCardsGrid');
    if (!host || !payload || !payload.cards) return;
    host.innerHTML = payload.cards.map(card => {
      const valueDisplay = card.unit === 'bytes' ? formatBytes(card.value)
                         : card.unit === 'ms' ? `${formatNumber(card.value)} ms`
                         : formatNumber(card.value);
      const totalDisplay = card.unit === 'bytes' && card.total ? ` / ${formatBytes(card.total)}` : '';
      const label = locale() === 'km' ? (card.label_km || card.label) : card.label;
      return `<div class="ei-stat-card" data-key="${esc(card.key)}">
        <span class="ei-stat-card-label">${esc(label)}</span>
        <strong class="ei-stat-card-value">${esc(valueDisplay)}${totalDisplay}</strong>
        ${formatDelta(card)}
      </div>`;
    }).join('');
  }

  function renderSystemStatus(payload){
    const banner = document.getElementById('systemStatusBanner');
    if (!banner) return;
    const level = (payload && payload.level) || 'green';
    banner.dataset.status = level;
    const text = (payload && payload.messages && payload.messages[0]) || t('noData');
    const el = banner.querySelector('[data-i18n="en"]');
    if (el) el.textContent = text;
    const km = banner.querySelector('[data-i18n="km"]');
    if (km) km.textContent = text;
  }

  function showImpersonationBanner(){
    // The server sets the `einvite_admin_origin` cookie when an admin
    // starts an impersonation session. We can't read it directly (HttpOnly),
    // so we rely on the session payload from /api/auth/me to surface
    // impersonation state — server returns `impersonating` if the cookie
    // is present. If absent, hide the banner.
    const banner = document.getElementById('impersonationBanner');
    if (!banner) return;
    api.get('/api/auth/me').then(me => {
      const u = me && me.user;
      if (u && u.impersonating) {
        banner.hidden = false;
        const emailEl = document.getElementById('impersonationEmail');
        if (emailEl) emailEl.textContent = u.email || '—';
      } else {
        banner.hidden = true;
      }
    }).catch(()=>{ banner.hidden = true; });
  }

  let pollTimer = null;
  async function pollOnce(){
    try {
      const [metrics, status] = await Promise.all([api.get('/api/admin/metrics-v2'), api.get('/api/admin/system-status')]);
      renderStatCards(metrics);
      renderSystemStatus(status);
    } catch(e) {
      // Don't spam the console on every poll; first failure clears the cards.
      const host = document.getElementById('statCardsGrid');
      if (host) host.innerHTML = `<p class="ei-error">${esc(e.message || t('error'))}</p>`;
    }
  }
  function startPolling(){
    if (pollTimer) return;
    pollTimer = setInterval(pollOnce, 30_000);
  }
  function stopPolling(){ if (pollTimer){ clearInterval(pollTimer); pollTimer = null; } }

  function initTabs(){
    const buttons = document.querySelectorAll('[data-admin-tab]');
    buttons.forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.adminTab;
        buttons.forEach(b => b.classList.toggle('active', b === btn));
        document.querySelectorAll('.admin-panel').forEach(p => p.classList.remove('active'));
        const panel = document.getElementById(`${tab === 'feature-flags' ? 'featureFlags'
                                              : tab === 'audit-log' ? 'auditLog'
                                              : tab === 'system-health' ? 'systemHealth'
                                              : tab === 'bulk-ops' ? 'bulkOps'
                                              : tab}Panel`);
        if (panel) panel.classList.add('active');
        // Lazy-mount each module on first show.
        mountModule(tab);
      });
    });
  }

  function mountModule(tab){
    const map = {
      'users':         () => window.EInviteAdminUsers,
      'invitations':   () => window.EInviteAdminInvitations,
      'feature-flags': () => window.EInviteAdminFeatureFlags,
      'audit-log':     () => window.EInviteAdminAuditLog,
      'system-health': () => window.EInviteAdminSystemHealth,
      'bulk-ops':      () => window.EInviteAdminBulkOps,
      'impersonate':   () => window.EInviteAdminImpersonate,
      'reports':       () => window.EInviteAdminReports,
    };
    const getter = map[tab];
    if (!getter) return;
    const mod = getter();
    if (mod && typeof mod.mount === 'function' && !mod._mounted) {
      mod._mounted = true;
      try { mod.mount(); } catch(e) { console.warn('[admin] module mount failed', tab, e); }
    }
  }

  async function init(){
    initTabs();
    showImpersonationBanner();
    await pollOnce();
    startPolling();
    // Lazy-mount the default tab (users).
    mountModule('users');
  }

  window.EInviteAdminShell = Object.freeze({
    version: 64,
    STRINGS,
    api,
    pollOnce,
    startPolling,
    stopPolling,
    formatNumber,
    formatBytes,
    renderStatCards,
    renderSystemStatus,
    showImpersonationBanner,
    init,
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
