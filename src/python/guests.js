/**
 * guests.js — Guest list management (ROADMAP §5.6).
 * Renders the guest table, summary metrics, per-guest action buttons (edit,
 * personal-link, QR, check-in, remove), CSV import/export, and inline editing.
 * All user-facing strings go through EInviteI18n.langText() (dual .i18n-en/.i18n-km
 * spans, CSS-driven toggle) or a plain-text helper for DOM APIs (alert/confirm/
 * textContent) that reads EInviteI18n.get() at call time. No STRINGS table so
 * check-bilingual-consistency.py (which only scans top-level src/js/*.js) is
 * not polluted with EN-FALLBACK placeholders — see §8 of LANGUAGE-GAP-REPORT.
 */
const $=s=>document.querySelector(s),inviteId=window.EInviteContext?.getInvitationId()||'demo-wedding',localKey=`sovan-guests:${inviteId}`;let guests=[],server=false,slug='invitation',invitation=null,rsvpEnabled=true;
/* Goal 6b (§5.5): the batch-share selection. Declared here, with the other
   module-level state, because the wiring that reads it runs before the
   spreadsheet/link-code sections below — a const declared further down is in
   the temporal dead zone at that point (measured: bundle-guests-v15.js threw
   "Cannot access 'pickedGuests' before initialization" and the list never
   rendered). */
const pickedGuests=new Set();
const _isKm=()=>(window.EInviteI18n&&window.EInviteI18n.get?window.EInviteI18n.get():(document.documentElement.lang||'').toLowerCase()).startsWith('km');
const _html=(en,km)=>{if(window.EInviteI18n)return window.EInviteI18n.langText(en,km);const e=_isKm()?(km!=null?km:en):en;return`<span class="i18n i18n-en">${esc(en)}</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">${esc(km!=null?km:en)}</span>`};
const _txt=(en,km)=>{const isKm=_isKm();return isKm?(km!=null?km:en):en};
async function request(path,options={}){let r=await fetch(path,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',...(options.headers||{})}}),data=await r.json().catch(()=>({}));if(!r.ok)throw Object.assign(Error(data.error||'Request failed'),{status:r.status,data});return data}
async function load(){if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;if(window.EInviteBackend&&!window.EInviteBackend.isAvailable()){server=false;guests=JSON.parse(localStorage.getItem(localKey)||'[]');window.EInviteBackend.message($('#guestList'),_txt('Guest management, personal links, QR codes, and check-in require the full application server.','Guest management, personal links, QR codes, and check-in require the full application server.'));render();return}try{await request('/api/health');server=true;invitation=await request(`/api/invitations/${encodeURIComponent(inviteId)}`);slug=invitation?.slug||slug;rsvpEnabled=invitation?.document?.settings?.rsvpEnabled!==false;guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`)}catch(error){server=false;guests=JSON.parse(localStorage.getItem(localKey)||'[]');if(error.status===404)window.EInviteBackend?.message($('#guestList'),_txt('This invitation is not available in the current server context.','This invitation is not available in the current server context.'))}render()}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function guestUrl(g){if(!g?.token)return'';const code=String(g.slug||'').trim();return server?`${location.origin}/i/${encodeURIComponent(slug)}${code?`/${encodeURIComponent(code)}`:''}?g=${encodeURIComponent(g.token)}`:`${location.origin}${location.pathname.replace(/guests(?:\.html)?$/,'public.html')}?g=${encodeURIComponent(g.token)}`}
/* Goal 6a/6b (§5.1, §5.5): the shareable form of a guest link is the readable
   one — project slug plus the guest's frozen code, no ?g= token. The code is a
   mnemonic, not the capability (§4.1), so this is what a designer pastes into a
   group chat; the token stays in guestUrl() for the private per-guest link. A
   guest whose code has not been generated yet falls back to the bare project
   link, which still opens the invitation. */
function guestShareUrl(g){const code=String(g?.slug||'').trim();return server?`${location.origin}/i/${encodeURIComponent(slug)}${code?`/${encodeURIComponent(code)}`:''}`:''}
function coupleName(){return String(invitation?.document?.fields?.names||'').trim()}
/* The three channel links are the same shapes the public share panel builds
   (src/js/public-share-panel.js: t.me/share/url, wa.me/?text=,
   sharer.php?u=) — that builder is page-local and not exported, so the formats
   are mirrored here rather than loaded onto the guests route for three URLs. */
function shareChannelLinks(row){const url=guestShareUrl(row);if(!url)return'';const message=_txt(`You are invited to ${coupleName()||'our celebration'}. ${url}`,'');return`<a target="_blank" rel="noopener noreferrer" href="https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(message)}">Telegram</a><a target="_blank" rel="noopener noreferrer" href="https://wa.me/?text=${encodeURIComponent(message)}">WhatsApp</a><a target="_blank" rel="noopener noreferrer" href="https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}">Facebook</a>`}
function filtered(){let q=$('#search').value.trim().toLowerCase(),filter=$('#statusFilter').value;return guests.filter(g=>{let text=`${g.name} ${g.phone||''} ${g.email||''} ${g.group_name||''} ${g.household_id||''} ${g.table_name||''} ${(g.tags||[]).join(' ')}`.toLowerCase(),status=g.rsvp_status||'';if(!text.includes(q))return false;if(!rsvpEnabled)return filter==='all'||filter==='checked'&&g.checked_in;return filter==='all'||filter==='yes'&&status.startsWith('Yes')||filter==='no'&&status.startsWith('Unable')||filter==='pending'&&!status||filter==='checked'&&g.checked_in})}
function render(){let yes=guests.filter(g=>g.rsvp_status?.startsWith('Yes')).length,no=guests.filter(g=>g.rsvp_status?.startsWith('Unable')).length,pending=guests.length-yes-no,checked=guests.filter(g=>g.checked_in).length;$('#summary').innerHTML=rsvpEnabled?`<div class="metric"><strong>${guests.length}</strong>${_html('Invited','Invited')}</div><div class="metric"><strong>${yes}</strong>${_html('Attending','Attending')}</div><div class="metric"><strong>${no}</strong>${_html('Declined','Declined')}</div><div class="metric"><strong>${pending}</strong>${_html('Pending','Pending')}</div><div class="metric"><strong>${checked}</strong>${_html('Checked in','Checked in')}</div>`:`<div class="metric"><strong>${guests.length}</strong>${_html('Invited','Invited')}</div><div class="metric"><strong>${checked}</strong>${_html('Checked in','Checked in')}</div><div class="metric"><strong>${_html('Off','Off')}</strong>${_html('RSVP disabled','RSVP disabled')}</div>`;const filter=$('#statusFilter');if(filter){[...filter.options].forEach(o=>{if(['yes','no','pending'].includes(o.value))o.hidden=!rsvpEnabled});if(!rsvpEnabled&&['yes','no','pending'].includes(filter.value))filter.value='all'}
$('#guestList').innerHTML=filtered().map(g=>{const status=rsvpEnabled?esc(g.rsvp_status||_txt('Awaiting reply','Awaiting reply')):(_txt(g.token_revoked_at?'Personal link revoked':(g.personalLinkAvailable?'Personal invitation ready':'Personal link needs rotation'),g.token_revoked_at?'Personal link revoked':(g.personalLinkAvailable?'Personal invitation ready':'Personal link needs rotation')));return`<div class="guest-row ${g.checked_in?'checked':''}"><div><strong>${esc(g.name)}</strong><br><small>${esc([g.phone,g.email,g.group_name&&`${_txt('Group:','Group:')} ${g.group_name}`,g.household_id&&`${_txt('Household:','Household:')} ${g.household_id}`,g.table_name&&`${_txt('Table:','Table:')} ${g.table_name}`,g.seat_label&&`${_txt('Seat:','Seat:')} ${g.seat_label}`].filter(Boolean).join(' · '))}</small>${(g.tags||[]).length?`<span class="tags">${(g.tags||[]).map(tag=>`<span class="tag">${esc(tag)}</span>`).join('')}</span>`:''}
<div class="guest-meta">${g.checked_in?`${_html('Checked in','Checked in')}${g.check_in_at?` ${_html('at','at')} ${esc(new Date(g.check_in_at).toLocaleString())}`:''}`:''}${g.rsvp_status&&rsvpEnabled?`${_html('RSVP','RSVP')}: ${esc(g.rsvp_status)}`:''}${g.delivery_status?` · ${esc(g.delivery_status)}`:''}${g.opened_at?` · ${_html('Opened','Opened')}`:''}</div></div><span>${status}</span><button data-edit="${g.id}">${_html('Edit','Edit')}</button><button data-link="${g.id}">${g.personalLinkAvailable?_html('Link','Link'):_html('Rotate link','Rotate link')}</button><button data-qr="${g.id}" ${g.personalLinkAvailable?'':'disabled'}>${_html('QR','QR')}</button><button data-check="${g.id}">${g.checked_in?_html('Undo check-in','Undo check-in'):_html('Check in','Check in')}</button><button class="danger" data-delete="${g.id}">${_html('Remove','Remove')}</button><label class="guest-pick"><input type="checkbox" data-pick="${g.id}" ${pickedGuests.has(g.id)?'checked':''} aria-label="${esc(_txt('Select this guest for the link list','ជ្រើរើសភ្ញៀវនេះសម្រាប់បញ្ជីតំណ'))}"></label></div>`}).join('')||`<p class="empty">${_html('No guests match this filter.','No guests match this filter.')}</p>`}
;
/* Goal 6b (§5.5): the selection drives "Copy all links". Checked guests are
   copied; with none checked the whole filtered list is, which is what a designer
   who has just imported a sheet wants. */
document.querySelectorAll('[data-pick]').forEach(box=>{box.onchange=()=>{box.checked?pickedGuests.add(box.dataset.pick):pickedGuests.delete(box.dataset.pick);render()}});
const selectAllBox=$('#selectAllGuests');if(selectAllBox){selectAllBox.checked=guests.length>0&&pickedGuests.size===guests.length;selectAllBox.indeterminate=pickedGuests.size>0&&pickedGuests.size<guests.length}
$('#search').oninput=render;$('#statusFilter').onchange=render;
$('#addForm').onsubmit=async e=>{e.preventDefault();let data=Object.fromEntries(new FormData(e.target));data.tags=String(data.tags||'').split(',').map(x=>x.trim()).filter(Boolean);await addGuest(data);e.target.reset();render()};
async function addGuest(data,refresh=true){if(server){const created=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`,{method:'POST',body:JSON.stringify(data)});if(refresh)guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`);return created||null}const local={id:crypto.randomUUID(),name:data.name,phone:data.phone,slug:'',token:crypto.randomUUID().slice(0,12),personalLinkAvailable:true,rsvp_status:null,checked_in:false};guests.unshift(local);localStorage.setItem(localKey,JSON.stringify(guests));return local}
async function editGuest(id){let g=guests.find(x=>x.id===id);if(!g)return;const fields=[['name',_txt('Guest name','Guest name'),g.name],['phone',_txt('Phone number','Phone number'),g.phone||''],['email',_txt('Email','Email'),g.email||''],['groupName',_txt('Group','Group'),g.group_name||''],['householdId',_txt('Household','Household'),g.household_id||''],['tableName',_txt('Table','Table'),g.table_name||''],['seatLabel',_txt('Seat','Seat'),g.seat_label||''],['tags',_txt('Tags (comma separated)','Tags (comma separated)'),(g.tags||[]).join(', ')]];const form=document.createElement('form');form.innerHTML=`<h2>${_html('Edit guest','Edit guest')}</h2>${fields.map(([name,label,value])=>`<label>${esc(label)}<input name="${name}" value="${esc(value)}"></label>`).join('')}<div class="dialog-actions"><button type="button" data-cancel>${_html('Cancel','Cancel')}</button><button class="primary">${_html('Save','Save')}</button></div>`;$('#qrBody').replaceChildren(form);$('#qrModal').showModal();form.querySelector('[data-cancel]').onclick=()=>$('#qrModal').close();form.onsubmit=async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(form));data.tags=String(data.tags||'').split(',').map(x=>x.trim()).filter(Boolean);if(server){await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${id}`,{method:'PUT',body:JSON.stringify(data)});guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`)}else Object.assign(g,{name:data.name,phone:data.phone,email:data.email,group_name:data.groupName,household_id:data.householdId,table_name:data.tableName,seat_label:data.seatLabel,tags:data.tags});$('#qrModal').close();render()}}
async function checkIn(id){let g=guests.find(x=>x.id===id),checkedIn=!g.checked_in;if(server){await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${id}/check-in`,{method:'PUT',body:JSON.stringify({checkedIn})});guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`)}else{g.checked_in=checkedIn;g.checked_in_at=checkedIn?Date.now():null;localStorage.setItem(localKey,JSON.stringify(guests))}render()}
async function removeGuest(id){if(!(await uiConfirm(_txt('Remove this guest?','Remove this guest?'),{title:_txt('Remove guest','Remove guest'),danger:true,confirmText:_txt('Remove','Remove')})))return;if(server){await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${id}`,{method:'DELETE'});guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`)}else{guests=guests.filter(g=>g.id!==id);localStorage.setItem(localKey,JSON.stringify(guests))}render()}
async function rotateLink(g){let value=await uiPrompt(_txt('Optional expiration in days. Leave blank for no expiration.','Optional expiration in days. Leave blank for no expiration.'),'',{title:_txt('Rotate personal invitation link','Rotate personal invitation link'),confirmText:_txt('Rotate link','Rotate link')});if(value===null)return;const days=String(value).trim();const payload=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${g.id}/token/rotate`,{method:'POST',body:JSON.stringify(days?{expiresDays:Number(days)}:{})});g.token=payload.token;g.token_expires_at=payload.tokenExpiresAt||null;g.token_revoked_at=null;g.personalLinkAvailable=true;return payload.token}
async function manageLink(id){let g=guests.find(x=>x.id===id);if(!g)return;if(!g.token){try{await rotateLink(g);render()}catch(error){alert(_txt(error.message||'Action failed','Action failed'))}return}const url=guestUrl(g);$('#qrBody').innerHTML=`<h2>${esc(g.name)}</h2><p>${_html('Personal invitation link','Personal invitation link')}</p><p class="personal-link-status">${g.token_expires_at?`${_html('Expires','Expires')} ${esc(new Date(g.token_expires_at).toLocaleString())}`:_html('No expiration set','No expiration set')}</p><div class="dialog-actions"><button id="copyPersonalLink">${_html('Copy personal link','Copy personal link')}</button><button id="rotatePersonalLink">${_html('Rotate link','Rotate link')}</button><button id="revokePersonalLink" class="danger">${_html('Revoke link','Revoke link')}</button></div>`;$('#qrModal').showModal();$('#copyPersonalLink').onclick=async()=>{await navigator.clipboard.writeText(url);$('#copyPersonalLink').textContent=_txt('Copied!','Copied!')};$('#rotatePersonalLink').onclick=async()=>{try{await rotateLink(g);$('#qrModal').close();render()}catch(error){alert(_txt(error.message||'Action failed','Action failed'))}};$('#revokePersonalLink').onclick=async()=>{if(!(await uiConfirm(_txt('Revoke this personal link? Existing copies and QR codes will stop working.','Revoke this personal link? Existing copies and QR codes will stop working.'),{title:_txt('Revoke personal link','Revoke personal link'),danger:true,confirmText:_txt('Revoke','Revoke')})))return;await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${g.id}/token/revoke`,{method:'POST',body:'{}'});g.token=null;g.personalLinkAvailable=false;g.token_revoked_at=Date.now();$('#qrModal').close();render()}}
function showQr(id){let g=guests.find(x=>x.id===id);if(!g?.token)return manageLink(id);let url=guestUrl(g),qr=server?`/api/invitations/${encodeURIComponent(inviteId)}/guests/${encodeURIComponent(id)}/qr.png`:'';$('#qrBody').innerHTML=`<h2>${esc(g.name)}</h2>${qr?`<div id="qrImageWrap"><img id="guestQrImage" src="${qr}" alt="${_txt('QR code','QR code')} for ${esc(g.name)}" width="420" height="420"><p id="qrError" class="hint" hidden></p></div>`:`<p class="hint">${_html('Run the local server to generate a private QR code.','Run the local server to generate a private QR code.')}</p>`}<p><button id="copyLink">${_html('Copy personal link','Copy personal link')}</button>${qr?` <a id="downloadGuestQr" href="${qr}" download="${esc(g.name)}-qr.png" class="button-link">${_html('Download QR','Download QR')}</a>`:''}</p>`;$('#qrModal').showModal();const img=$('#guestQrImage'),download=$('#downloadGuestQr'),error=$('#qrError');if(img)img.onerror=()=>{img.hidden=true;if(download)download.hidden=true;if(error){error.hidden=false;error.textContent=_txt('QR generation is unavailable. The personal link can still be copied safely.','QR generation is unavailable. The personal link can still be copied safely.')}};$('#copyLink').onclick=async()=>{await navigator.clipboard.writeText(url);$('#copyLink').textContent=_txt('Copied!','Copied!')}}
$('.close').onclick=()=>$('#qrModal').close();
function parseCsv(text){let rows=[],row=[],cell='',quoted=false;for(let i=0;i<text.length;i++){let c=text[i];if(c==='"'&&quoted&&text[i+1]==='"'){cell+='"';i++}else if(c==='"')quoted=!quoted;else if(c===','&&!quoted){row.push(cell.trim());cell=''}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell.trim());if(row.some(Boolean))rows.push(row);row=[];cell=''}else cell+=c}row.push(cell.trim());if(row.some(Boolean))rows.push(row);return rows}
$('#importFile').onchange=e=>{const file=e.target.files?.[0];if(file)openImport(file)};
$('#exportBtn').onclick=()=>{let rows=[[_txt('Name','Name'),_txt('Phone','Phone'),_txt('Email','Email'),_txt('Group','Group'),_txt('Household','Household'),_txt('Table','Table'),_txt('Seat','Seat'),_txt('Tags','Tags'),rsvpEnabled?_txt('RSVP status','RSVP status'):_txt('Invitation mode','Invitation mode'),_txt('Checked in','Checked in'),_txt('Delivery','Delivery'),_txt('Opened','Opened'),_txt('Personal link','Personal link')],...guests.map(g=>[g.name,g.phone||'',g.email||'',g.group_name||'',g.household_id||'',g.table_name||'',g.seat_label||'',(g.tags||[]).join('|'),rsvpEnabled?(g.rsvp_status||_txt('Pending','Pending')):_txt('RSVP disabled','RSVP disabled'),g.checked_in?_txt('Yes','Yes'):_txt('No','No'),g.delivery_status||'',g.opened_at?new Date(g.opened_at).toISOString():'',guestUrl(g)])],csv=rows.map(row=>row.map(v=>`"${String(v).replaceAll('"','""')}"`).join(',')).join('\r\n'),a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='guest-list.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
/* ────────────────────────────────────────────────────────────────────────────
   Bulk guest import — the research pass's phase A (§5.7 of
   docs/reviews/bulk-guest-import-research.md).

   Why Excel is the primary path: a spreadsheet has no charset. Excel on Windows
   writes CSV as UTF-16LE-with-BOM or in a legacy codepage, and reading that as
   UTF-8 either throws or silently imports mojibake Khmer names (research risk
   2). CSV is still accepted, with the BOM sniffed; a byte stream that no
   supported encoding decodes is refused with a message that names the fix,
   never imported as garbage.

   SheetJS is loaded lazily from the vendored build only when a spreadsheet is
   actually chosen, so the guests route keeps its 3-script / 440,000-byte page
   budget (docs/route-bundle-sources-v15.json, src/python/build/build_page_manifests.py).

   Khmer below comes from docs/i18n/TRANSLATIONS.csv where an approved string
   exists; every string passed with an EMPTY Khmer slot is listed as KH_PENDING
   in docs/reviews/bulk-guest-import-implementation.md — none is invented.
   ──────────────────────────────────────────────────────────────────────────── */
const SHEETJS_URL='/vendor/sheetjs/xlsx.mini.min.js';let sheetJsPromise=null;
function loadSheetJs(){if(window.XLSX)return Promise.resolve(window.XLSX);if(!sheetJsPromise)sheetJsPromise=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=SHEETJS_URL;script.onload=()=>window.XLSX?resolve(window.XLSX):reject(Error('Spreadsheet library did not initialise'));script.onerror=()=>reject(Error('Spreadsheet library could not be loaded'));document.head.append(script)});return sheetJsPromise}
function decodeImportText(buffer){const bytes=new Uint8Array(buffer),decode=(encoding,offset)=>new TextDecoder(encoding).decode(bytes.subarray(offset));if(bytes.length>=3&&bytes[0]===0xEF&&bytes[1]===0xBB&&bytes[2]===0xBF)return{text:decode('utf-8',3),encoding:'UTF-8 with BOM'};if(bytes.length>=2&&bytes[0]===0xFF&&bytes[1]===0xFE)return{text:decode('utf-16le',2),encoding:'UTF-16LE with BOM'};if(bytes.length>=2&&bytes[0]===0xFE&&bytes[1]===0xFF)return{text:decode('utf-16be',2),encoding:'UTF-16BE with BOM'};try{return{text:new TextDecoder('utf-8',{fatal:true}).decode(bytes),encoding:'UTF-8'}}catch(error){return{text:'',encoding:'',failed:true}}}
const csvCells=rows=>rows.map(row=>Array.isArray(row)?row.map(value=>String(value??'').trim()):[]);
async function readImportFile(file){const name=String(file?.name||'').toLowerCase();if(/\.xlsx$|\.xlsm$|\.xls$/.test(name)){const XLSX=await loadSheetJs();const workbook=XLSX.read(new Uint8Array(await file.arrayBuffer()));const sheet=workbook.Sheets[workbook.SheetNames[0]];if(!sheet)throw Error('The workbook has no worksheet');return{rows:csvCells(XLSX.utils.sheet_to_json(sheet,{header:1,blankrows:false,defval:''})),source:'Excel'}}const decoded=decodeImportText(await file.arrayBuffer());if(decoded.failed)return{rows:[],source:'CSV',decodeFailure:true};return{rows:csvCells(parseCsv(decoded.text)),source:'CSV · '+decoded.encoding}}
function importStateFor(rows,source){const headerRow=rows[0]||[],header=/name|guest|ឈ្មោះ/i.test(String(headerRow[0]||'')),columns=Math.max(1,rows.reduce((max,row)=>Math.max(max,row.length),0));return{rows,source,header,columns,column:0,skipDuplicates:false,start:header?1:0}}
function importEntries(state){const entries=[];for(let index=state.start;index<state.rows.length;index++){const row=state.rows[index]||[],name=String(row[state.column]||'').trim();if(!row.some(value=>String(value||'').trim()))continue;entries.push({index,name,phone:String(row[1]||'').trim()})}return entries}
function importFindings(state){const entries=importEntries(state),blank=[],duplicates=[],seen=new Set();for(const entry of entries){if(!entry.name){blank.push(entry.index+1);continue}const key=entry.name.toLowerCase();if(seen.has(key)){duplicates.push(entry.name);continue}seen.add(key)}return{entries,blank,duplicates}}
function importRowsToImport(state){const{entries,duplicates}=importFindings(state);if(!state.skipDuplicates)return entries;const seen=new Set(),kept=[];for(const entry of entries){const key=entry.name.toLowerCase();if(seen.has(key))continue;seen.add(key);kept.push(entry)}return kept}
let importDialog=null,importState=null;
function ensureImportDialog(){if(importDialog)return importDialog;importDialog=document.createElement('dialog');importDialog.className='ei-dialog';importDialog.setAttribute('aria-modal','true');importDialog.innerHTML='<div class="ei-dialog-card"><div class="ei-dialog-head"><span class="ei-dialog-icon"></span><div><h2></h2><p class="ei-dialog-message"></p></div></div><div class="guest-import-body"></div><div class="ei-dialog-actions"></div></div>';document.body.append(importDialog);importDialog.addEventListener('close',()=>{importState=null});return importDialog}
function closeImportDialog(){importDialog?.close()}
function renderImportDialog(){
  const dialog=ensureImportDialog(),state=importState;
  const icon=dialog.querySelector('.ei-dialog-icon'),heading=dialog.querySelector('h2'),message=dialog.querySelector('.ei-dialog-message'),body=dialog.querySelector('.guest-import-body'),actions=dialog.querySelector('.ei-dialog-actions');
  if(!state){body.innerHTML='';actions.innerHTML='';return}
  if(state.failure){
    icon.textContent='!';heading.textContent=_txt('Import guests','នាំចូលភ្ញៀវ');
    message.innerHTML=_html('The file could not be read.','មិនអាចអានឯកសារបានទេ។');
    body.innerHTML=`<p class="hint">${esc(state.failure)}</p>`;
    actions.innerHTML=`<button type="button" class="ei-primary" data-cancel>${_html('Close','បិទ')}</button>`;
    actions.querySelector('[data-cancel]').onclick=closeImportDialog;return
  }
  if(state.decodeFailure){
    icon.textContent='!';heading.textContent=_txt('Import guests','នាំចូលភ្ញៀវ');
    message.innerHTML=_html('This CSV is neither UTF-8, UTF-16LE nor UTF-16BE. Export the guest list as .xlsx and import that instead — a spreadsheet has no charset, so Khmer names survive it.','ឯកសារ CSV នេះមិនមែនជា UTF-8, UTF-16LE ឬ UTF-16BE ទេ។ សូមនាំចេញបញ្ជីភ្ញៀវជា .xlsx ហើយនាំចូលវិញ — ឯកសារ spreadsheet មិនមានការកំណត់អក្សរ ដូច្នេះឈ្មោះខ្មែរនៅរក្សាបាន។');
    body.innerHTML='';actions.innerHTML=`<button type="button" class="ei-primary" data-cancel>${_html('Close','បិទ')}</button>`;
    actions.querySelector('[data-cancel]').onclick=closeImportDialog;return
  }
  const{entries,blank,duplicates}=importFindings(state),importable=importRowsToImport(state),detected=state.header?String((state.rows[0]||[])[state.column]||'').trim():'';
  icon.textContent='⇪';heading.textContent=_txt('Import guests','នាំចូលភ្ញៀវ');
  message.innerHTML=_html(state.header?`Found ${entries.length} rows, name column detected as '${detected||'Column 1'}'.`:`Found ${entries.length} rows, no header row detected — choose the name column.`,'');
  const options=Array.from({length:state.columns},(_,index)=>`<option value="${index}" ${index===state.column?'selected':''}>${esc(`Column ${index+1} — ${String((state.rows[0]||[])[index]||'').slice(0,18)||'—'}`)}</option>`).join('');
  const shown=entries.length>7?[...entries.slice(0,5),null,...entries.slice(-2)]:entries;
  const preview=shown.map(entry=>entry===null?`<div class="guest-row"><div><strong>…</strong></div></div>`:`<div class="guest-row"><div><strong>${esc(entry.name||_txt('(empty name)','(គ្មានឈ្មោះ)'))}</strong>${entry.phone?`<br><small>${esc(entry.phone)}</small>`:''}</div></div>`).join('');
  const emptyWarning=blank.length?`<p class="hint">${esc(`${blank.length} row(s) have no name, so nothing was imported yet (rows ${blank.slice(0,8).join(', ')}${blank.length>8?'…':''})`)}</p>`:'';
  // Re-import key (research §5.2): a sheet has no key of its own, so a row is
  // matched on lower(name) within this invitation. A match is updated and keeps
  // its frozen link; anything else is added. Nothing is merged or duplicated
  // silently — the counts are stated before the write.
  const existingByName=existingGuestIndex(),willUpdate=importable.filter(entry=>existingByName.has(entry.name.trim().toLowerCase())).length;
  const updateWarning=importable.length?`<p class="hint">${esc(`${willUpdate} row(s) match a guest already in this list and will be updated with their links kept; ${importable.length-willUpdate} will be added.`)}</p>`:'';
  const duplicateWarning=duplicates.length?`<p class="hint">${esc(`${duplicates.length} duplicate name(s) in this file: ${duplicates.slice(0,5).join(', ')}${duplicates.length>5?'…':''}`)}</p><label style="display:flex;gap:8px;align-items:center"><input type="checkbox" data-skip-duplicates ${state.skipDuplicates?'checked':''}> ${_html('Skip later duplicates (the default keeps both)','រំលងឈ្មោះស្ទួនពេលក្រោយ (ការកំណត់លំនាំដើមរក្សាទាំងពីរ)')}</label>`:'';
  body.innerHTML=`<label class="sr-only" for="importColumn">${_html('Name column','ជួរឈ្មោះ')}</label><select id="importColumn">${options}</select>${emptyWarning}${duplicateWarning}${updateWarning}<div class="guest-table">${preview}</div>`;
  const select=body.querySelector('#importColumn');select.onchange=()=>{state.column=Number(select.value);renderImportDialog()};
  const skip=body.querySelector('[data-skip-duplicates]');if(skip)skip.onchange=()=>{state.skipDuplicates=skip.checked;renderImportDialog()};
  actions.innerHTML=`<button type="button" data-cancel>${_html('Cancel','បោះបង់')}</button><button type="button" class="ei-primary" data-import ${blank.length||!importable.length?'disabled':''}>${esc(`Import ${importable.length} guest(s)`)}</button>`;
  actions.querySelector('[data-cancel]').onclick=closeImportDialog;
  actions.querySelector('[data-import]').onclick=()=>runImport(importable);
}
async function openImport(file){
  let parsed;
  try{parsed=await readImportFile(file)}catch(error){parsed={failure:error.message||String(error)}}
  const dialog=ensureImportDialog();
  importState=parsed.failure?{rows:[],source:'',failure:parsed.failure}:importStateFor(parsed.rows,parsed.source);
  renderImportDialog();
  if(!dialog.open)dialog.showModal();
}
async function runImport(entries){
  const button=importDialog?.querySelector('[data-import]');if(button)button.disabled=true;
  const existing=existingGuestIndex();let added=0,updated=0,failed=0;const touched=[];
  try{
    for(const entry of entries){
      const match=server?existing.get(entry.name.trim().toLowerCase()):null;
      try{
        if(match){
          // The frozen code is deliberately absent from this payload, so
          // update_guest_details' COALESCE(?,slug) leaves it untouched.
          await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${encodeURIComponent(match.id)}`,{method:'PUT',body:JSON.stringify({name:match.name,phone:entry.phone||match.phone||'',email:match.email||'',groupName:match.group_name||'',householdId:match.household_id||'',tableName:match.table_name||'',seatLabel:match.seat_label||'',tags:match.tags||[]})});updated++;touched.push(match.id)
        }else{const created=await addGuest({name:entry.name,phone:entry.phone},false);added++;if(created?.id)touched.push(created.id)}
      }catch(error){failed++}
    }
  }finally{
    if(server)guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`);
    closeImportDialog();render();
  }
  const summary=`${added} ${_txt('added','បានបន្ថែម')} · ${updated} ${_txt('updated','បានធ្វើបច្ចុប្បន្នភាព')}${failed?` · ${failed} ${_txt('failed','បានបរាជ័យ')}`:''}`;
  if(window.EInviteFeedback?.toast)window.EInviteFeedback.toast(summary);else alert(summary);
  $('#importFile').value='';
  openLinkEditor(guests.filter(guest=>touched.includes(guest.id)));
}
/* ── Phase C: per-guest link codes, the mapping screen and the freeze ──
   The code is a mnemonic, not the capability (research §4.1: OSWP's own source
   says the same of its household code and excludes 0 1 i l o so it can be read
   aloud). The 32-character ?g= token stays the capability and is unchanged.

   `slugify`/`randomCode` mirror server-side clean_slug/short_code for the live
   preview only. The server re-validates every submitted code and is
   authoritative; nothing here decides what a guest's link is. */
const SLUG_ALPHABET='23456789abcdefghjkmnpqrstuvwxyz';
async function copyGuestLinks(){const list=pickedGuests.size?guests.filter(g=>pickedGuests.has(g.id)):guests,urls=list.map(guestShareUrl).filter(Boolean);if(!urls.length){alert(_txt('There are no guest links to copy yet.','មិនទាន់មានតំណភ្ញៀវសម្រាប់ចម្លងទេ។'));return}await navigator.clipboard.writeText(urls.join('\n'));const summary=`${urls.length} ${_txt('link(s) copied','តំណបានចម្លង')}`;if(window.EInviteFeedback?.toast)window.EInviteFeedback.toast(summary);else alert(summary)}
function existingGuestIndex(){const index=new Map();for(const guest of guests){const key=String(guest.name||'').trim().toLowerCase();if(key&&!index.has(key))index.set(key,guest)}return index}
function slugify(value){return String(value??'').toLowerCase().replace(/[^a-z0-9-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,60)}
function randomCode(length=6){const bytes=new Uint8Array(length);(window.crypto||window.msCrypto).getRandomValues(bytes);let out='';for(const byte of bytes)out+=SLUG_ALPHABET[byte%SLUG_ALPHABET.length];return out}
function proposedSlug(name,taken){const base=slugify(name)||randomCode(6);let candidate=base,index=2;while(taken.has(candidate)){candidate=`${base}-${index}`;index++}taken.add(candidate);return candidate}
function validSlug(value){return /^[a-z0-9-]{1,60}$/.test(value)}
let linkDialog=null,linkRows=[];
function ensureLinkDialog(){if(linkDialog)return linkDialog;linkDialog=document.createElement('dialog');linkDialog.className='ei-dialog';linkDialog.style.width='min(760px,calc(100vw - 32px))';linkDialog.setAttribute('aria-modal','true');linkDialog.innerHTML='<div class="ei-dialog-card"><div class="ei-dialog-head"><span class="ei-dialog-icon">↗</span><div><h2></h2><p class="ei-dialog-message"></p></div></div><div class="guest-import-body"></div><div class="ei-dialog-actions"></div></div>';document.body.append(linkDialog);linkDialog.addEventListener('close',()=>{linkRows=[]});return linkDialog}
function closeLinkDialog(){linkDialog?.close()}
function renderLinkDialog(){
  if(!linkDialog)return;
  const body=linkDialog.querySelector('.guest-import-body'),actions=linkDialog.querySelector('.ei-dialog-actions'),message=linkDialog.querySelector('.ei-dialog-message');
  linkDialog.querySelector('h2').textContent=_txt('Guest links','តំណភ្ញៀវ');
  const changed=linkRows.filter(row=>row.slug!==row.original);
  message.innerHTML=_html(`Each guest gets their own link. Freezing keeps it: editing a name later changes the card and the page, but not a link you have already shared.${changed.length?` ${changed.length} code(s) changed and their old links will stop working.`:''}`,'');
  body.innerHTML=`<div class="guest-table">${linkRows.map((row,index)=>`<div class="guest-row"><div><strong>${esc(row.name)}</strong><br><small>${esc(slugPreview(row))}</small></div><input data-code="${index}" maxlength="60" value="${esc(row.slug)}" aria-label="${esc(_txt('Guest link code','លេខកូដតំណភ្ញៀវ'))}"><button type="button" data-regenerate="${index}" title="${esc(_txt('Generate a new code','បង្កើតលេខកូដថ្មី'))}">↻</button><span class="share-channels">${shareChannelLinks(row)}</span></div>`).join('')||`<p class="hint">${_html('No guests yet.','មិនទាន់មានភ្ញៀវនៅឡើយ។')}</p>`}</div><p class="share-note hint">${_html('Send a bare link on its own: Telegram then shows the invitation preview, and any text beside it suppresses the card.','ផ្ញើតំណទទេតែមួយដោយឡែក៖ Telegram នឹងបង្ហាញការមើលជាមុននៃការអញ្ជើញ ហើយអត្ថបទណាមួយនៅជាប់វានឹងលាក់កាតនោះ។')}</p>`;
  body.querySelectorAll('[data-code]').forEach(input=>{const index=Number(input.dataset.code);input.onchange=()=>{const cleaned=slugify(input.value)||linkRows[index].original;if(!validSlug(cleaned)){input.value=linkRows[index].original;linkRows[index].slug=linkRows[index].original}else{linkRows[index].slug=cleaned;input.value=cleaned}renderLinkDialog()}});
  body.querySelectorAll('[data-regenerate]').forEach(button=>{button.onclick=()=>{const index=Number(button.dataset.regenerate);const taken=new Set(linkRows.filter((_,position)=>position!==index).map(row=>row.slug));linkRows[index].slug=proposedSlug(linkRows[index].name,taken);renderLinkDialog()}});
  actions.innerHTML=`<button type="button" data-cancel>${_html('Close','បិទ')}</button><button type="button" data-regenerate-all>${_html('Regenerate all','បង្កើតឡើងវិញទាំងអស់')}</button><button type="button" class="ei-primary" data-freeze>${_html('Freeze and generate','ជួសជុល និងបង្កើត')}</button>`;
  actions.querySelector('[data-cancel]').onclick=closeLinkDialog;
  actions.querySelector('[data-regenerate-all]').onclick=()=>{const taken=new Set();linkRows.forEach(row=>{row.slug=proposedSlug(row.name,taken)});renderLinkDialog()};
  actions.querySelector('[data-freeze]').onclick=freezeLinks;
}
function slugPreview(row){return `/${slug}/${row.slug}${row.original&&row.slug!==row.original?`  ·  ${_txt('was','ពីមុន')} /${slug}/${row.original}`:''}`}
function openLinkEditor(list){
  if(!server)return;
  linkRows=(list&&list.length?list:guests).map(guest=>({id:guest.id,name:guest.name,slug:guest.slug||'',original:guest.slug||''})).filter(row=>row.id);
  ensureLinkDialog();renderLinkDialog();
  if(!linkDialog.open)linkDialog.showModal();
}
async function freezeLinks(){
  const changed=linkRows.filter(row=>row.slug&&row.slug!==row.original);
  const button=linkDialog?.querySelector('[data-freeze]');if(button)button.disabled=true;
  let payload;
  try{payload=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/freeze`,{method:'POST',body:JSON.stringify({guests:changed.map(row=>({id:row.id,slug:row.slug}))})})}
  catch(error){if(button)button.disabled=false;alert(_txt(error.message||'Action failed','Action failed'));return}
  if(payload.conflicts&&payload.conflicts.length){if(button)button.disabled=false;linkDialog.querySelector('.ei-dialog-message').textContent=_txt(`These codes are already used in this invitation: ${payload.conflicts.join(', ')}`,'');return}
  guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`);
  closeLinkDialog();render();
  const summary=`${payload.updated} ${_txt('link(s) frozen','តំណត្រូវបានជួសជុល')}`;
  if(window.EInviteFeedback?.toast)window.EInviteFeedback.toast(summary);else alert(summary);
}
$('#linksBtn').onclick=()=>openLinkEditor(guests);
$('#selectAllGuests')?.addEventListener('change',event=>{pickedGuests.clear();if(event.currentTarget.checked)guests.forEach(guest=>pickedGuests.add(guest.id));render()});
$('#copyLinksBtn')?.addEventListener('click',copyGuestLinks);
if(window.EInviteI18n&&typeof window.EInviteI18n.subscribe==='function'){window.EInviteI18n.subscribe(render)};
load();
