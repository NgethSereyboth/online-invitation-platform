(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const page=document.body?.dataset.page||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''));
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

// -----------------------------------------------------------------------------
// Dashboard — actual project previews, compact menus, profile navigation
// -----------------------------------------------------------------------------
function dashboardFinal(){
  const grid=$('#inviteGrid'),view=$('#dashboardView'),header=$('body>header'); if(!grid||!view)return;
  const getInvites=()=>{try{return Array.isArray(invites)?invites:[]}catch{return[]}};
  const findInvite=id=>getInvites().find(x=>String(x.id)===String(id));
  const localDoc=id=>{try{return JSON.parse(localStorage.getItem(`sovan-invite-draft-v3:${id}`)||'null')}catch{return null}};
  const previewDoc=item=>item?.preview||localDoc(item?.id)||null;
  const pct=(value,axis='x')=>{
    if(value==null)return null; const s=String(value).trim(); if(s.endsWith('%'))return s;
    const n=parseFloat(s); if(!Number.isFinite(n))return null;
    if(s.endsWith('px'))return `${Math.max(0,Math.min(100,n/(axis==='x'?390:844)*100))}%`;
    return `${Math.max(0,Math.min(100,n))}%`;
  };
  function objectPreview(obj){
    const node=document.createElement('div');node.className='fp-thumb-object';
    const left=pct(obj.left,'x')||'10%',top=pct(obj.top,'y')||'10%',width=pct(obj.width,'x')||'50%',height=pct(obj.height,'y')||'12%';
    Object.assign(node.style,{left,top,width,height,zIndex:String(obj.zIndex||1),opacity:String(obj.opacity??1),transform:`rotate(${Number(obj.rotation||0)}deg)`});
    if(obj.type==='image'&&obj.src){const img=document.createElement('img');img.src=obj.src;img.alt='';img.style.objectPosition=`${Number(obj.imagePositionX??50)}% ${Number(obj.imagePositionY??50)}%`;img.style.objectFit=obj.imageFit||'cover';node.append(img)}
    else if(obj.type==='shape'){node.classList.add('fp-thumb-shape');node.style.background=obj.fillColor||obj.backgroundColor||'#d9a6ad';node.style.borderRadius=`${Number(obj.borderRadius||0)/4}px`;if(obj.shapeKind==='circle')node.style.borderRadius='50%'}
    else{node.textContent=String(obj.html||obj.text||'').replace(/<[^>]+>/g,' ').trim();node.style.fontFamily=obj.font||'Georgia,serif';node.style.fontSize=`${Math.max(5,Number(obj.fontSize||24)/5.2)}px`;node.style.fontWeight=obj.fontWeight||'400';node.style.fontStyle=obj.fontStyle||'normal';node.style.letterSpacing=`${Number(obj.letterSpacing||0)/5}px`;node.style.color=obj.color||'#342c26';node.style.textAlign=obj.textAlign||'center';}
    return node;
  }
  function buildPreview(item){
    const doc=previewDoc(item)||{},palette=doc.palette||{},fields=doc.fields||{},page0=(doc.designPages||[])[0]||null;
    const bg=page0?.background||doc.masterPageStyle?.background||palette.background||'#fff7f3',surface=palette.surface||'#fff',text=palette.text||'#342c26',heading=palette.heading||doc.accent||'#9d4555',accent=doc.accent||heading;
    const shell=document.createElement('div');shell.className='fp-project-preview';shell.style.setProperty('--preview-shell',`color-mix(in srgb, ${bg} 52%, var(--app-surface-2))`);
    const art=document.createElement('div');art.className='fp-project-artboard';art.style.setProperty('--preview-bg',bg);art.style.setProperty('--preview-text',text);art.style.setProperty('--preview-heading',heading);art.style.setProperty('--preview-accent',accent);art.style.background=bg;
    const objects=page0?.objects||doc.objects||{};const list=Object.values(objects).filter(Boolean).slice(0,28);
    if(list.length){list.sort((a,b)=>Number(a.zIndex||0)-Number(b.zIndex||0)).forEach(obj=>art.append(objectPreview(obj)))}else{const f=document.createElement('div');f.className='fp-thumb-fallback';f.innerHTML=`<small>${esc(doc.eventType||item.type||'Invitation')}</small><strong>${esc(fields.names||item.title||'Untitled invitation')}</strong><span>${esc(fields.date||'')} ${fields.venue?`· ${esc(fields.venue)}`:''}</span>`;art.append(f)}
    shell.append(art);return shell;
  }
  const timeAgo=value=>{const t=Number(value)||Date.parse(value)||0;if(!t)return'';const sec=Math.max(0,Math.round((Date.now()-t)/1000));if(sec<60)return'Edited just now';if(sec<3600)return`Edited ${Math.floor(sec/60)}m ago`;if(sec<86400)return`Edited ${Math.floor(sec/3600)}h ago`;if(sec<604800)return`Edited ${Math.floor(sec/86400)}d ago`;return`Edited ${new Date(t).toLocaleDateString()}`};
  function decorateCard(card){
    if(card.dataset.fpReady==='1')return;const id=card.querySelector('[data-edit]')?.dataset.edit;if(!id)return;const item=findInvite(id);if(!item)return;card.dataset.fpReady='1';card.dataset.inviteId=id;
    const cover=$('.invite-cover',card);if(cover){cover.replaceChildren(buildPreview(item));const status=document.createElement('span');status.className='fp-project-status';status.textContent=item.status||'Draft';cover.append(status);cover.onclick=()=>{if(!item.archived)card.querySelector('[data-edit]')?.click()}}
    const body=$('.invite-body',card),stats=$('.stats',card),actions=$('.actions',card);if(!body||!actions)return;
    if(stats)stats.innerHTML=`<span>${esc(item.status||'Draft')}</span><span>${esc(timeAgo(item.updatedAt))}</span>`;
    const more=document.createElement('button');more.type='button';more.className='fp-project-more';more.setAttribute('aria-label','Project actions');more.setAttribute('aria-expanded','false');more.textContent='•••';
    const menu=document.createElement('div');menu.className='fp-project-menu';menu.setAttribute('role','menu');
    const map=[['Edit','[data-edit]'],['Guests','[data-guests]'],['Responses','[data-responses]'],['Analytics','[data-analytics]'],['Duplicate','[data-copy]'],[item.archived?'Restore':'Archive','[data-archive]'],['Delete','[data-delete]']];
    map.forEach(([label,selector])=>{const source=$(selector,actions);if(!source)return;const b=document.createElement('button');b.type='button';b.textContent=label;if(label==='Delete')b.className='danger';b.onclick=e=>{e.stopPropagation();menu.classList.remove('open');more.setAttribute('aria-expanded','false');source.click()};menu.append(b)});
    more.onclick=e=>{e.stopPropagation();$$('.fp-project-menu.open').filter(x=>x!==menu).forEach(x=>x.classList.remove('open'));menu.classList.toggle('open');more.setAttribute('aria-expanded',menu.classList.contains('open')?'true':'false')};
    body.append(more);card.append(menu);
  }
  const refresh=()=>$$('.invite-card',grid).forEach(decorateCard);new MutationObserver(refresh).observe(grid,{childList:true,subtree:true});refresh();
  document.addEventListener('click',()=>$$('.fp-project-menu.open').forEach(x=>x.classList.remove('open')));

  if(header&&!$('.fp-dashboard-profile',header)){
    const wrap=document.createElement('div');wrap.className='fp-dashboard-profile';wrap.innerHTML=`<button type="button" class="fp-profile-button" aria-label="Account menu">U</button><div class="fp-profile-popover"><div class="fp-profile-summary"><strong>Account</strong><small></small></div><a href="account.html">Account settings</a><a href="materials.html">Materials</a><a href="billing.html">Plans & usage</a><a href="designer.html" data-profile-designer hidden>Designer workspace</a><a href="admin.html" data-profile-admin hidden>Administration</a><button type="button" data-signout>Sign out</button></div>`;header.append(wrap);
    const button=$('.fp-profile-button',wrap),pop=$('.fp-profile-popover',wrap);button.onclick=e=>{e.stopPropagation();pop.classList.toggle('open')};pop.onclick=e=>e.stopPropagation();$('[data-signout]',wrap).onclick=()=>$('#logoutBtn')?.click();
    const update=()=>{let a=null;try{a=account}catch{}const email=a?.email||'Account';$('.fp-profile-summary strong',wrap).textContent=email;$('.fp-profile-summary small',wrap).textContent=[a?.role,a?.plan].filter(Boolean).join(' · ');button.textContent=(email[0]||'U').toUpperCase();$('[data-profile-designer]',wrap).hidden=!['designer','admin'].includes(a?.role);$('[data-profile-admin]',wrap).hidden=a?.role!=='admin';wrap.hidden=view.hidden};new MutationObserver(update).observe(view,{attributes:true,attributeFilter:['hidden']});update();document.addEventListener('click',()=>pop.classList.remove('open'));
  }
}

// -----------------------------------------------------------------------------
// Materials — signed-out state, rich previews, use-in-design
// -----------------------------------------------------------------------------
function materialsFinal(){
  const grid=$('#grid');if(!grid)return;
  let dialog=null;
  function itemById(id){try{return materials.find(x=>String(x.id)===String(id))}catch{return null}}
  function inviteName(id){try{return invitations.find(x=>String(x.id)===String(id))?.title||invitations.find(x=>String(x.id)===String(id))?.slug||'Invitation'}catch{return'Invitation'}}
  function ensureDialog(){if(dialog)return dialog;dialog=document.createElement('dialog');dialog.className='fp-material-preview-dialog';document.body.append(dialog);return dialog}
  function openPreview(item){if(!item)return;const kind=item.mime?.startsWith('image/')?'image':item.mime?.startsWith('video/')?'video':item.mime?.startsWith('audio/')?'audio':'file',d=ensureDialog();
    let media=kind==='image'?`<img src="${esc(item.url)}" alt="${esc(item.name)}">`:kind==='video'?`<video src="${esc(item.url)}" controls preload="metadata"></video>`:kind==='audio'?`<div><div class="fp-material-audio-art">♫</div><audio src="${esc(item.url)}" controls preload="metadata"></audio></div>`:`<div class="fp-material-audio-art">◇</div>`;
    d.innerHTML=`<div class="fp-material-preview-shell"><div class="fp-material-stage">${media}</div><aside class="fp-material-detail"><div class="fp-material-detail-head"><h2>${esc(item.name)}</h2><button type="button" class="fp-material-close">×</button></div><div class="fp-material-facts"><div><span>Type</span><strong>${esc(item.mime||'Unknown')}</strong></div><div><span>Size</span><strong>${typeof formatBytes==='function'?formatBytes(item.size):esc(item.size)}</strong></div><div><span>Invitation</span><strong>${esc(inviteName(item.invitationId))}</strong></div><div><span>Folder</span><strong>${esc(item.folder||'No folder')}</strong></div><div><span>Used</span><strong>${Number(item.usageCount||0)} reference${Number(item.usageCount||0)===1?'':'s'}</strong></div></div><div class="fp-material-preview-actions"><button type="button" class="primary" data-use>Use in design</button><div class="fp-material-secondary-actions"><button type="button" data-edit> Edit details</button><a href="${esc(item.url)}" download target="_blank" rel="noopener"><button type="button">Download</button></a></div><button type="button" class="fp-material-danger" data-delete>Delete material</button></div></aside></div>`;
    $('.fp-material-close',d).onclick=()=>d.close();$('[data-edit]',d).onclick=()=>{d.close();try{openEdit(item.id)}catch{grid.querySelector(`[data-edit="${CSS.escape(String(item.id))}"]`)?.click()}};$('[data-delete]',d).onclick=()=>{d.close();try{openEdit(item.id);setTimeout(()=>$('#deleteBtn')?.click(),40)}catch{}};$('[data-use]',d).onclick=()=>{localStorage.setItem('sovan-active-invite',item.invitationId);localStorage.setItem('einvite-pending-material-insert',JSON.stringify({url:item.url,name:item.name,mime:item.mime,assetId:item.id}));location.href='index.html'};d.showModal();
  }
  function decorate(){
    const empty=$('.empty-library',grid);if(empty&&/Authentication required|sign in|unauthorized/i.test(empty.textContent)){document.body.classList.add('material-auth-required');grid.innerHTML=`<div class="fp-material-auth-state"><div class="fp-material-auth-card"><div class="icon">◌</div><h2>Your session has expired</h2><p>Sign in again to access your photos, videos, audio, folders, and saved materials.</p><a href="dashboard.html"><button type="button" class="primary">Sign in again</button></a></div></div>`;return}else document.body.classList.remove('material-auth-required');
    $$('.material-card-page',grid).forEach(card=>{if(card.dataset.fpReady==='1')return;const id=card.querySelector('[data-edit]')?.dataset.edit,item=itemById(id);if(!item)return;card.dataset.fpReady='1';const thumb=$('.material-thumb',card);if(thumb)thumb.onclick=()=>openPreview(item);const info=$('.material-info',card);if(info){const row=document.createElement('div');row.className='fp-material-meta-row';row.innerHTML=`<span>${item.mime?.split('/')[0]||'file'}</span>${Number(item.usageCount||0)?`<span class="fp-material-usage">Used ${Number(item.usageCount)}</span>`:''}`;info.append(row)}})
  }
  new MutationObserver(decorate).observe(grid,{childList:true,subtree:true});decorate();
}

// -----------------------------------------------------------------------------
// Editor — real visual assets, richer text browser, mobile behavior, compact context
// -----------------------------------------------------------------------------
function editorFinal(){
  const stage=$('#stage'),host=$('.studio-pane-host'),rail=$('.studio-tool-rail');if(!stage||!host||!rail)return;
  const saveNow=()=>{try{typeof save==='function'&&save()}catch{}};const choose=o=>{try{typeof clearSelection==='function'&&clearSelection();typeof setSelection==='function'&&setSelection([o])}catch{}};
  const makeId=p=>`${p}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;
  const closePaneOnMobile=()=>{if(innerWidth<=980&&document.body.classList.contains('studio-design-mode'))document.body.classList.add('mobile-pane-collapsed')};
  const openPane=()=>document.body.classList.remove('mobile-pane-collapsed');
  rail.addEventListener('click',openPane,true);
  if(!$('.fp-mobile-pane-handle')){const h=document.createElement('button');h.type='button';h.className='fp-mobile-pane-handle';h.textContent='›';h.title='Open creation panel';h.onclick=openPane;document.body.append(h)}
  $$('.studio-pane-heading',host).forEach(head=>{if(head.querySelector('.fp-mobile-pane-close'))return;const b=document.createElement('button');b.type='button';b.className='fp-mobile-pane-close';b.textContent='‹';b.title='Hide panel';b.onclick=closePaneOnMobile;head.append(b)});

  function addSvgAsset(asset){if(typeof createObject!=='function')return;const o=createObject(makeId('graphic'),'image');const data=`data:image/svg+xml;charset=utf-8,${encodeURIComponent(asset.svg)}`;o.style.left=asset.left||'18%';o.style.top=asset.top||'24%';o.style.width=asset.width||'64%';o.style.height=asset.height||'190px';o.dataset.src=data;o.dataset.layerName=asset.name;o.dataset.showInGallery='false';o.dataset.showInHero='true';const img=o.querySelector('img');if(img){img.src=data;img.alt=asset.name}stage.append(o);choose(o);saveNow();window.uiToast?.(`${asset.name} added`,'✦');closePaneOnMobile()}
  const assets=[
    {name:'Khmer lotus corner',cat:'Khmer',width:'38%',height:'210px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 220"><g fill="none" stroke="#b48735" stroke-width="5" stroke-linecap="round"><path d="M20 200C82 190 110 154 113 92M20 200c52-42 90-49 154-44"/><path d="M113 92c-29 21-44 51-40 84 28-10 51-31 64-61 12 29 35 49 65 58 1-34-15-63-45-83-1 31-8 57-20 77-13-20-21-45-24-75Z"/><path d="M174 156c38-12 72-9 120 21M205 148c18-18 31-40 36-68"/></g></svg>`},
    {name:'Royal gold flourish',cat:'Wedding',height:'120px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 160"><g fill="none" stroke="#c5a15b" stroke-width="5"><path d="M18 82c110 0 124-58 210-58 48 0 57 38 72 58 15-20 24-58 72-58 86 0 100 58 210 58"/><path d="M22 84c110 0 126 54 218 54 32 0 49-18 60-48 11 30 28 48 60 48 92 0 108-54 218-54"/><circle cx="300" cy="82" r="12" fill="#c5a15b"/></g></svg>`},
    {name:'Botanical sprig',cat:'Botanical',width:'34%',height:'250px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 380"><g fill="none" stroke="#527760" stroke-width="5" stroke-linecap="round"><path d="M68 350C102 254 128 162 196 40"/><path d="M111 237c-58 4-84-23-91-59 44-7 76 11 98 44M137 176c-9-52 10-83 49-101 15 40 7 74-31 106M85 293c-43 4-67-15-76-47 34-8 64 2 83 31M169 116c-5-39 10-65 43-79 11 32 4 58-24 82"/></g></svg>`},
    {name:'Wedding arch',cat:'Wedding',width:'66%',height:'300px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 620"><path d="M80 600V270C80 120 145 30 250 30s170 90 170 240v330" fill="none" stroke="#b58a5a" stroke-width="10"/><g fill="#d9aeb3"><circle cx="93" cy="240" r="24"/><circle cx="112" cy="192" r="18"/><circle cx="392" cy="215" r="24"/><circle cx="370" cy="165" r="17"/></g><g fill="#6f8d72"><ellipse cx="126" cy="230" rx="12" ry="34" transform="rotate(45 126 230)"/><ellipse cx="374" cy="240" rx="12" ry="34" transform="rotate(-45 374 240)"/></g></svg>`},
    {name:'Diamond frame',cat:'Frames',width:'58%',height:'320px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500"><path d="M250 18 482 250 250 482 18 250Z" fill="none" stroke="#c6a35b" stroke-width="9"/><path d="M250 46 454 250 250 454 46 250Z" fill="none" stroke="#c6a35b" stroke-width="2" opacity=".7"/></svg>`},
    {name:'Lotus divider',cat:'Khmer',height:'110px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 150"><g fill="none" stroke="#a87616" stroke-width="4"><path d="M20 75h250M430 75h250"/><path d="M350 28c-24 18-36 40-35 66 17-6 29-18 35-36 6 18 18 30 35 36 1-26-11-48-35-66Z"/><path d="M350 44c-12 13-18 28-18 44 8-3 14-9 18-18 4 9 10 15 18 18 0-16-6-31-18-44Z"/></g></svg>`},
    {name:'Celebration confetti',cat:'Celebration',height:'220px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 320"><g fill="none" stroke-linecap="round" stroke-width="10"><path d="M55 55l32 30M420 44l-28 36M118 258l35-17M380 263l-36-23" stroke="#ff5d8f"/><path d="M158 38l-8 42M328 45l18 39M58 180l44-4M410 170l34 12" stroke="#50b9d6"/><path d="M235 34l8 44M255 263l-5 38" stroke="#7d59d4"/></g><g fill="#f2b84b"><circle cx="101" cy="122" r="10"/><circle cx="395" cy="112" r="9"/><circle cx="205" cy="238" r="8"/></g></svg>`},
    {name:'Executive wave',cat:'Business',height:'150px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 180"><path d="M0 132C120 46 205 36 330 104c109 59 229 45 370-46v122H0Z" fill="#173e58"/><path d="M0 154C140 82 222 76 344 132c104 48 216 38 356-30v78H0Z" fill="#20a49b" opacity=".78"/></svg>`},
    {name:'Rose corner',cat:'Wedding',width:'36%',height:'220px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 300"><g fill="#d48d9c"><circle cx="82" cy="82" r="38"/><circle cx="120" cy="58" r="30"/><circle cx="131" cy="101" r="34"/></g><g fill="#6d8b70"><ellipse cx="186" cy="85" rx="24" ry="54" transform="rotate(48 186 85)"/><ellipse cx="98" cy="176" rx="22" ry="60" transform="rotate(12 98 176)"/></g><path d="M20 282C66 210 107 151 178 96" fill="none" stroke="#6d8b70" stroke-width="7"/></svg>`},
    {name:'Minimal line frame',cat:'Frames',width:'72%',height:'360px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 700"><rect x="18" y="18" width="464" height="664" rx="18" fill="none" stroke="#65535f" stroke-width="3"/><rect x="38" y="38" width="424" height="624" rx="12" fill="none" stroke="#65535f" stroke-width="1" opacity=".55"/></svg>`},
    {name:'Star sparkle cluster',cat:'Celebration',width:'34%',height:'210px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 260"><g fill="#c69d55"><path d="m150 18 14 57 56 14-56 14-14 57-14-57-56-14 56-14Z"/><path d="m240 126 8 30 30 8-30 8-8 30-8-30-30-8 30-8Z" opacity=".72"/><circle cx="66" cy="182" r="12" opacity=".55"/></g></svg>`},
    {name:'Khmer geometric border',cat:'Khmer',height:'88px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 100"><defs><pattern id="p" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M40 4 76 40 40 76 4 40Z" fill="none" stroke="#a87616" stroke-width="4"/><path d="M40 19 61 40 40 61 19 40Z" fill="none" stroke="#a87616" stroke-width="2"/></pattern></defs><rect width="800" height="80" y="10" fill="url(#p)"/></svg>`}
  ];
  const pane=$('[data-studio-pane="elements"]',host);
  if(pane&&!$('.fp-visual-assets',pane)){
    const section=document.createElement('section');section.className='fp-visual-assets';section.innerHTML=`<div class="fp-visual-assets-head"><h3>Visual graphics</h3><small>Invitation-ready SVG</small></div><div class="fp-visual-asset-grid"></div>`;const grid=$('.fp-visual-asset-grid',section);
    assets.forEach(asset=>{const b=document.createElement('button');b.type='button';b.className='fp-visual-asset';b.innerHTML=`<span class="art">${asset.svg}</span><strong>${esc(asset.name)}</strong>`;b.title=`${asset.name} · ${asset.cat}`;b.onclick=()=>addSvgAsset(asset);grid.append(b)});
    const existing=$('.final-element-library',pane);pane.insertBefore(section,existing||pane.firstChild);if(existing&&!existing.closest('.fp-simple-symbols')){const details=document.createElement('details');details.className='fp-simple-symbols';details.innerHTML='<summary>Simple symbols & shapes</summary>';existing.before(details);details.append(existing)}
  }

  // Richer inline text/font browsing.
  const textPane=$('[data-studio-pane="text"]',host);
  if(textPane&&!$('.fp-text-fonts',textPane)){
    const fonts=[
      ['Inter','Inter,ui-sans-serif,system-ui,sans-serif','Modern'],['Segoe UI','"Segoe UI",Arial,sans-serif','Modern'],['Georgia','Georgia,serif','Serif'],['Garamond','Garamond,"Times New Roman",serif','Serif'],['Bodoni','"Bodoni 72","Bodoni MT",Didot,serif','Display'],['Didot','Didot,"Bodoni 72",serif','Display'],['Brush Script','"Brush Script MT",cursive','Script'],['Segoe Script','"Segoe Script",cursive','Script'],['Khmer Sans','"Noto Sans Khmer","Khmer OS Battambang",sans-serif','Khmer'],['Khmer Serif','"Noto Serif Khmer","Khmer OS Battambang",serif','Khmer'],['Khmer Ceremonial','"Khmer OS Muol Light","Noto Serif Khmer",serif','Khmer'],['Khmer Battambang','"Khmer OS Battambang","Noto Sans Khmer",sans-serif','Khmer']
    ].map(([name,stack,cat])=>({name,stack,cat}));
    const recent=()=>{try{return JSON.parse(localStorage.getItem('einvite-font-recent-v1')||'[]')}catch{return[]}};
    const section=document.createElement('section');section.className='refine-text-section fp-text-fonts';section.innerHTML=`<div><h3>Fonts</h3><small>Click a font to apply it or create text</small></div><div class="fp-text-category-tabs"></div><div class="fp-inline-font-list"></div>`;
    const combo=document.createElement('section');combo.className='refine-text-section';combo.innerHTML=`<div><h3>Font combinations</h3><small>Ready-made invitation typography</small></div><div class="fp-text-combo-grid">
      <button class="fp-text-combo" data-fp-combo="gold"><span class="hero" style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
      <button class="fp-text-combo" data-fp-combo="editorial"><span class="hero" style="font-family:Didot,Georgia,serif">THE<br><i>MOMENT</i></span><small>Editorial contrast</small></button>
      <button class="fp-text-combo" data-fp-combo="modern"><span class="hero" style="font-family:Arial,sans-serif;font-weight:800">TITLE<br><small>SUBHEADING</small></span><small>Modern clean</small></button>
      <button class="fp-text-combo" data-fp-combo="romance"><span class="hero" style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
      <button class="fp-text-combo" data-fp-combo="khmer"><span class="hero" style="font-family:'Khmer OS Muol Light','Noto Serif Khmer',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
      <button class="fp-text-combo" data-fp-combo="minimal"><span class="hero" style="font-family:Inter,Arial,sans-serif;letter-spacing:.12em">SAVE<br>THE DATE</span><small>Minimal spaced</small></button>
    </div>`;
    const fontPlaceholder=$('.refine-text-section',textPane)?.nextElementSibling;textPane.append(section,combo);
    let cat='All',query='';const categories=['All','Recent','Khmer','Serif','Modern','Display','Script'];
    const selected=()=>$('.object.selected,.object.multi-selected',stage);
    const applyFont=font=>{let o=selected();if(!o){$('#addText')?.click();o=selected()}if(!o)return;o.dataset.font=font.stack;try{applyObjectVisualStyle(o);save()}catch{}const r=[font.stack,...recent().filter(x=>x!==font.stack)].slice(0,12);localStorage.setItem('einvite-font-recent-v1',JSON.stringify(r));closePaneOnMobile()};
    function renderFonts(){const tabs=$('.fp-text-category-tabs',section),list=$('.fp-inline-font-list',section);tabs.innerHTML=categories.map(x=>`<button type="button" class="${x===cat?'active':''}" data-cat="${x}">${x}</button>`).join('');$$('[data-cat]',tabs).forEach(b=>b.onclick=()=>{cat=b.dataset.cat;renderFonts()});let data=fonts.filter(f=>{if(cat==='Recent'&&!recent().includes(f.stack))return false;if(!['All','Recent'].includes(cat)&&f.cat!==cat)return false;return!query||`${f.name} ${f.cat}`.toLowerCase().includes(query)});if(cat==='Recent')data.sort((a,b)=>recent().indexOf(a.stack)-recent().indexOf(b.stack));list.innerHTML='';data.forEach(f=>{const b=document.createElement('button');b.type='button';b.className='fp-inline-font';b.innerHTML=`<span class="sample" style="font-family:${f.stack}">${f.cat==='Khmer'?'សិរីមង្គល':'Beautiful moments'}</span><small>${esc(f.name)}</small>`;b.onclick=()=>applyFont(f);list.append(b)});if(!data.length)list.innerHTML='<small style="padding:12px;color:var(--app-muted)">No fonts match this view.</small>'}
    renderFonts();
    const search=$('.refine-text-search input',textPane);if(search){const prior=search.oninput;search.oninput=e=>{query=e.target.value.trim().toLowerCase();renderFonts();$$('.refine-text-preset,.fp-text-combo',textPane).forEach(x=>x.hidden=!!query&&!x.textContent.toLowerCase().includes(query));if(typeof prior==='function')prior.call(search,e)}}
    const combos={gold:{font:'Georgia,serif',fontSize:'48',color:'#b48a20',text:'Golden Hour',letterSpacing:'1'},editorial:{font:'Didot,Georgia,serif',fontSize:'48',color:'#2c2530',text:'The Moment',fontStyle:'italic'},modern:{font:'Arial,sans-serif',fontSize:'44',color:'#202127',text:'Your Celebration',fontWeight:'700'},romance:{font:'Georgia,serif',fontSize:'46',color:'#426b52',text:'Bride & Groom',fontStyle:'italic'},khmer:{font:"'Khmer OS Muol Light','Noto Serif Khmer',serif",fontSize:'38',color:'#9b6b13',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍'},minimal:{font:'Inter,Arial,sans-serif',fontSize:'34',color:'#22242a',text:'SAVE THE DATE',letterSpacing:'5'}};
    $$('.fp-text-combo',combo).forEach(b=>b.onclick=()=>{const c=combos[b.dataset.fpCombo];$('#addText')?.click();setTimeout(()=>{const o=selected();if(!o)return;const content=o.querySelector('.content');if(content)content.textContent=c.text;Object.entries(c).forEach(([k,v])=>{if(k!=='text')o.dataset[k]=v});try{applyObjectVisualStyle(o);save()}catch{}closePaneOnMobile()},30)});
  }

  // After a design item is inserted on tablet/mobile, reveal the canvas automatically.
  host.addEventListener('click',e=>{const insert=e.target.closest('.final-element-card,.ei-pack-card,[data-add-element],[data-text-preset],.refine-text-preset,.refine-font-combo,.fp-text-combo,.fp-visual-asset,.material-picker-card');if(insert)setTimeout(closePaneOnMobile,80)},true);

  // Pending material chosen from Material Library.
  setTimeout(()=>{let pending=null;try{pending=JSON.parse(localStorage.getItem('einvite-pending-material-insert')||'null')}catch{}if(!pending?.url||typeof createObject!=='function')return;localStorage.removeItem('einvite-pending-material-insert');const o=createObject(makeId('material'),'image');o.style.left='14%';o.style.top='18%';o.style.width='72%';o.style.height='420px';o.dataset.src=pending.url;o.dataset.layerName=pending.name||'Material';const img=o.querySelector('img');if(img){img.src=pending.url;img.alt=pending.name||'Invitation material'}stage.append(o);choose(o);saveNow();window.uiToast?.(`${pending.name||'Material'} added to the canvas`,'↑')},500);

  // Simplify the contextual toolbar and move secondary actions into a More menu.
  const context=$('.ei-context-toolbar');if(context){let scheduled=false;const decorate=()=>{scheduled=false;if(context.querySelector('.ei-context-more'))return;const secondary=['effects','animate','flipX','flipY','tidy','ungroup','page-motion','check'];const nodes=secondary.map(a=>context.querySelector(`[data-action="${a}"]`)).filter(Boolean);if(nodes.length){const more=document.createElement('button');more.type='button';more.className='ei-context-more';more.textContent='•••';more.title='More actions';const overflow=document.createElement('div');overflow.className='ei-context-overflow';nodes.forEach(n=>overflow.append(n));more.onclick=e=>{e.stopPropagation();overflow.classList.toggle('open')};context.append(more,overflow);document.addEventListener('click',()=>overflow.classList.remove('open'))}};const observer=new MutationObserver(()=>{if(context.querySelector('.ei-context-more'))return;if(scheduled)return;scheduled=true;queueMicrotask(decorate)});observer.observe(context,{childList:true,subtree:false});decorate()}
}

if(page==='dashboard')setTimeout(dashboardFinal,0);
if(page==='materials')setTimeout(materialsFinal,0);
if(page==='index')setTimeout(editorFinal,120);
})();
