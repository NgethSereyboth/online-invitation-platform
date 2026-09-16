/* v0.65.1 — system health & diagnostics (ROADMAP §5.6)
 * Per-subsystem status with "how to fix" hints. 60s server cache.
 */
(function(){
  'use strict';
  if (window.EInviteAdminSystemHealth && window.EInviteAdminSystemHealth.version >= 65) return;
  const shell = () => window.EInviteAdminShell || {};
  const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: { title:'System health', refresh:'Refresh', cached:'60s cache — values may be up to 60s old', ok:'OK', fail:'FAIL', warn:'WARN', howToFix:'How to fix', subsystem:'Subsystem', detail:'Detail', uptime:'Uptime', computedAt:'Computed at', loadFailed:'Failed to load health detail' },
    km: { title:'សុខភាពប្រព័ន្ធ', refresh:'ធ្វើបច្ចុប្បន្នភាព', cached:'ឃ្លាំងសម្ងាត់ ៦០ វិ — តម្លៃអាចចាស់រហូតដល់ ៦០ វិ', ok:'ល្អ', fail:'បរាជ័យ', warn:'ព្រមាន', howToFix:'របៀបជួសជុល', subsystem:'ប្រព័ន្ធរង', detail:'លម្អិត', uptime:'ពេលវេលាដំណើរការ', computedAt:'គណនានៅ', loadFailed:'បរាជ័យក្នុងការផ្ទុកសុខភាពលម្អិត' }
  };
  function t(k){ const l = (document.documentElement.lang || 'en').startsWith('km') ? 'km' : 'en'; return (STRINGS[l] && STRINGS[l][k]) || STRINGS.en[k] || k; }
  let state = { payload: null };

  async function load(){
    const api = shell().api;
    state.payload = await api.get('/api/admin/health-detail');
  }

  function render(){
    const host = document.getElementById('systemHealthPanel');
    if (!host) return;
    const p = state.payload || {};
    const checks = p.checks || {};
    const rows = Object.entries(checks).map(([name, c]) => {
      const ok = c.ok === true;
      const klass = ok ? 'ei-tag-ok' : (c.note ? 'ei-tag-warn' : 'ei-tag-fail');
      const status = ok ? t('ok') : (c.note ? t('warn') : t('fail'));
      const detail = c.note ? esc(c.note)
                    : c.error ? esc(c.error)
                    : Object.entries(c).filter(([k]) => !['ok','howToFix'].includes(k)).map(([k,v]) => `<small>${esc(k)}: ${esc(v)}</small>`).join(' ');
      const fix = c.howToFix ? `<details><summary>${esc(t('howToFix'))}</summary><p>${esc(c.howToFix)}</p></details>` : '';
      return `<tr>
        <td><strong>${esc(name)}</strong></td>
        <td><span class="ei-tag ${klass}">${status}</span></td>
        <td>${detail}</td>
        <td>${fix}</td>
      </tr>`;
    }).join('');
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <p class="ei-help">${esc(t('cached'))}</p>
      <p><small>${esc(t('uptime'))}: ${esc(p.uptimeSeconds || 0)}s · ${esc(t('computedAt'))}: ${p.computedAt ? new Date(p.computedAt).toLocaleString() : '—'}</small></p>
      <button id="systemHealthRefresh">${esc(t('refresh'))}</button>
      <table class="ei-admin-table"><thead><tr>
        <th>${esc(t('subsystem'))}</th><th>${esc(t('ok'))}</th><th>${esc(t('detail'))}</th><th>${esc(t('howToFix'))}</th>
      </tr></thead><tbody>${rows || `<tr><td colspan="4">${esc(t('loadFailed'))}</td></tr>`}</tbody></table>`;
    const btn = document.getElementById('systemHealthRefresh');
    if (btn) btn.addEventListener('click', () => { load().then(render).catch(e => alert(e.message)); });
  }

  async function mount(){ try { await load(); } catch(e) {} render(); }
  window.EInviteAdminSystemHealth = Object.freeze({ version: 65, mount, render, load });
})();
