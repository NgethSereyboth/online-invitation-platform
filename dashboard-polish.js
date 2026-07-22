/* Dashboard overview and discovery polish. Loaded after dashboard-enhancements.js. */
(() => {
  'use strict';
  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => [...r.querySelectorAll(s)];
  const view = $('#dashboardView');
  if (!view) return;

  const head = $('.dash-head', view);
  const grid = $('#inviteGrid');
  if (!head || !grid) return;

  const intro = document.createElement('div');
  intro.className = 'dashboard-intro';
  intro.innerHTML = `
    <div class="dashboard-intro-copy">
      <span class="dashboard-eyebrow">Invitation workspace</span>
      <h2>Create beautiful moments, manage every guest.</h2>
      <p>Design, publish, collect RSVPs and keep your event experience in one place.</p>
    </div>
    <div class="dashboard-overview-cards">
      <article><span>Invitations</span><strong id="dashMetricTotal">0</strong></article>
      <article><span>Published</span><strong id="dashMetricLive">0</strong></article>
      <article><span>Total views</span><strong id="dashMetricViews">0</strong></article>
      <article><span>RSVPs</span><strong id="dashMetricRsvp">0</strong></article>
    </div>`;
  head.after(intro);

  const toolbar = document.createElement('div');
  toolbar.className = 'dashboard-filterbar';
  toolbar.innerHTML = `
    <div class="dashboard-search"><span>⌕</span><input id="dashboardSearch" type="search" placeholder="Search invitations…"></div>
    <div class="dashboard-filter-tabs" role="group" aria-label="Invitation status">
      <button type="button" class="active" data-dash-filter="all">All</button>
      <button type="button" data-dash-filter="published">Published</button>
      <button type="button" data-dash-filter="draft">Drafts</button>
      <button type="button" data-dash-filter="archived">Archived</button>
    </div>`;
  intro.after(toolbar);

  let statusFilter = 'all';
  function availableInvites(){
    try { return Array.isArray(invites) ? invites : []; } catch { return []; }
  }
  function updateMetrics(){
    const items = availableInvites();
    const total = items.filter(x=>!x.archived).length;
    const live = items.filter(x=>!x.archived && String(x.status||'').toLowerCase().includes('publish')).length;
    const views = items.reduce((s,x)=>s+Number(x.views||0),0);
    const rsvp = items.reduce((s,x)=>s+Number(x.rsvps||0),0);
    $('#dashMetricTotal').textContent = total.toLocaleString();
    $('#dashMetricLive').textContent = live.toLocaleString();
    $('#dashMetricViews').textContent = views.toLocaleString();
    $('#dashMetricRsvp').textContent = rsvp.toLocaleString();
  }
  function decorateCards(){
    const items = availableInvites();
    $$('.invite-card', grid).forEach((card,index)=>{
      const item=items[index];
      const cover=$('.invite-cover',card);
      if(cover && !cover.querySelector('.invite-cover-inner')){
        const label=cover.textContent.trim();
        cover.innerHTML=`<div class="invite-cover-inner"><span>${label==='Wedding'?'♡':label==='Birthday'?'✦':'◇'}</span><strong>${label}</strong><small>${item?.status||'Draft'}</small></div>`;
      }
      const status = $('.invite-body>span',card);
      if(status) status.classList.add('invite-status-pill');
    });
  }
  function applyFilter(){
    const q = ($('#dashboardSearch')?.value||'').trim().toLowerCase();
    $$('.invite-card',grid).forEach(card=>{
      const title=($('.invite-body h2',card)?.textContent||'').toLowerCase();
      const status=($('.invite-body>span',card)?.textContent||'').toLowerCase();
      const archived=Number.parseFloat(card.style.opacity||'1')<1;
      const statusOk=statusFilter==='all'||(statusFilter==='published'&&status.includes('publish'))||(statusFilter==='draft'&&!archived&&!status.includes('publish'))||(statusFilter==='archived'&&archived);
      card.hidden=!(statusOk&&(!q||title.includes(q)));
    });
  }
  $('#dashboardSearch').addEventListener('input',applyFilter);
  $$('[data-dash-filter]').forEach(b=>b.onclick=()=>{statusFilter=b.dataset.dashFilter;$$('[data-dash-filter]').forEach(x=>x.classList.toggle('active',x===b));applyFilter()});

  const observer=new MutationObserver(()=>{decorateCards();updateMetrics();applyFilter()});
  observer.observe(grid,{childList:true,subtree:true});
  decorateCards();updateMetrics();applyFilter();
})();
