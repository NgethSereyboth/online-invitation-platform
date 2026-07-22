(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!$('#stage')) return;
const dispatchInput=el=>{el.dispatchEvent(new Event('input',{bubbles:true}))};
const safe=(v='')=>String(v);
const makeButton=(text,title)=>{const b=document.createElement('button');b.type='button';b.textContent=text;b.title=title||text;return b};
const raw={section:$('#sectionOrder'),schedule:$('#scheduleText'),scheduleKm:$('#scheduleTextKm'),venues:$('#venuesText'),venuesKm:$('#venuesTextKm')};
Object.values(raw).forEach(el=>el?.closest('label')?.classList.add('ei-raw-field'));

function parseSchedule(){
  const en=(raw.schedule?.value||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map(line=>{const [time,...rest]=line.split('|');return{time:(time||'').trim(),title:rest.join('|').trim()}});
  const km=(raw.scheduleKm?.value||'').split(/\r?\n/).map(x=>x.trim()).map(line=>{const [time,...rest]=line.split('|');return{time:(time||'').trim(),titleKm:rest.join('|').trim()}});
  return en.map((x,i)=>({...x,titleKm:km[i]?.titleKm||''}));
}
function writeSchedule(items){
  raw.schedule.value=items.map(x=>`${safe(x.time)} | ${safe(x.title)}`).join('\n');
  raw.scheduleKm.value=items.map(x=>`${safe(x.time)} | ${safe(x.titleKm)}`).join('\n');
  dispatchInput(raw.schedule);
}
function parseVenues(){
  const en=(raw.venues?.value||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map(line=>{const parts=line.split('|').map(x=>x.trim());return{name:parts[0]||'',address:parts[1]||'',mapUrl:parts.slice(2).join('|').trim()}});
  const km=(raw.venuesKm?.value||'').split(/\r?\n/).map(x=>x.trim()).map(line=>{const parts=line.split('|').map(x=>x.trim());return{nameKm:parts[0]||'',addressKm:parts.slice(1).join('|').trim()}});
  return en.map((x,i)=>({...x,nameKm:km[i]?.nameKm||'',addressKm:km[i]?.addressKm||''}));
}
function writeVenues(items){
  raw.venues.value=items.map(x=>`${safe(x.name)} | ${safe(x.address)} | ${safe(x.mapUrl)}`).join('\n');
  raw.venuesKm.value=items.map(x=>`${safe(x.nameKm)} | ${safe(x.addressKm)}`).join('\n');
  dispatchInput(raw.venues);
}
function parseSections(){return(raw.section?.value||'').split(/\r?\n|,/).map(x=>x.trim()).filter(Boolean)}
function writeSections(items){raw.section.value=items.join('\n');dispatchInput(raw.section)}

function builderShell(title,description,addLabel){const host=document.createElement('section');host.className='ei-builder';host.innerHTML=`<div class="ei-builder-head"><div><h3>${title}</h3><p>${description}</p></div></div><div class="ei-builder-list"></div>`;if(addLabel){const add=makeButton(`+ ${addLabel}`);host.querySelector('.ei-builder-head').append(add);host.addButton=add}return host}

const scheduleHost=builderShell('Schedule builder','Add, edit, and reorder event timeline items visually.','Add item');scheduleHost.classList.add('ei-schedule-builder');scheduleHost.dataset.scheduleBuilder='';
raw.schedule?.closest('label')?.parentNode?.insertBefore(scheduleHost,raw.schedule.closest('label').nextSibling);
function renderSchedule(){
  let items=parseSchedule();const list=$('.ei-builder-list',scheduleHost);list.textContent='';
  if(!items.length){const empty=document.createElement('div');empty.className='ei-builder-empty';empty.textContent='No schedule items yet.';list.append(empty)}
  items.forEach((item,index)=>{
    const card=document.createElement('article');card.className='ei-builder-card';card.draggable=true;card.dataset.index=index;
    card.innerHTML=`<div class="ei-builder-row"><button type="button" class="ei-builder-handle" title="Drag to reorder">⋮⋮</button><strong>Schedule item ${index+1}</strong><div class="ei-builder-actions"></div></div><div class="ei-builder-grid"><label>Time<input data-key="time" value=""></label><label>English title<input data-key="title" value=""></label></div><div class="ei-builder-grid"><label>Khmer time<input data-key="timeKm" value=""></label><label>Khmer title<input class="khmer-input" data-key="titleKm" value=""></label></div>`;
    card.querySelector('[data-key="time"]').value=item.time||'';card.querySelector('[data-key="timeKm"]').value=item.time||'';card.querySelector('[data-key="title"]').value=item.title||'';card.querySelector('[data-key="titleKm"]').value=item.titleKm||'';
    const actions=$('.ei-builder-actions',card),up=makeButton('↑','Move earlier'),down=makeButton('↓','Move later'),del=makeButton('×','Remove');del.className='danger';actions.append(up,down,del);
    const sync=()=>{const next=parseSchedule();next[index]={time:card.querySelector('[data-key="time"]').value.trim()||card.querySelector('[data-key="timeKm"]').value.trim(),title:card.querySelector('[data-key="title"]').value,titleKm:card.querySelector('[data-key="titleKm"]').value};writeSchedule(next)};
    card.querySelectorAll('input').forEach(input=>input.addEventListener('input',()=>{if(input.dataset.key==='time')card.querySelector('[data-key="timeKm"]').value=input.value;sync()}));
    up.onclick=()=>{const next=parseSchedule();if(index<=0)return;[next[index-1],next[index]]=[next[index],next[index-1]];writeSchedule(next);renderSchedule()};
    down.onclick=()=>{const next=parseSchedule();if(index>=next.length-1)return;[next[index+1],next[index]]=[next[index],next[index+1]];writeSchedule(next);renderSchedule()};
    del.onclick=async()=>{if(!(await uiConfirm('Remove this schedule item?',{title:'Remove schedule item',danger:true,confirmText:'Remove'})))return;const next=parseSchedule();next.splice(index,1);writeSchedule(next);renderSchedule()};
    card.addEventListener('dragstart',e=>{card.classList.add('dragging');e.dataTransfer.setData('text/plain',String(index));e.dataTransfer.effectAllowed='move'});card.addEventListener('dragend',()=>card.classList.remove('dragging'));card.addEventListener('dragover',e=>{e.preventDefault();card.classList.add('drag-over')});card.addEventListener('dragleave',()=>card.classList.remove('drag-over'));card.addEventListener('drop',e=>{e.preventDefault();card.classList.remove('drag-over');const from=Number(e.dataTransfer.getData('text/plain')),to=index;if(!Number.isInteger(from)||from===to)return;const next=parseSchedule(),[moved]=next.splice(from,1);next.splice(to,0,moved);writeSchedule(next);renderSchedule()});
    list.append(card)
  })
}
scheduleHost.addButton.onclick=()=>{const items=parseSchedule();items.push({time:'',title:'',titleKm:''});writeSchedule(items);renderSchedule();setTimeout(()=>scheduleHost.querySelector('.ei-builder-card:last-child input')?.focus(),0)};

const venueHost=builderShell('Additional venue builder','Create multiple named locations with bilingual details and map links.','Add venue');venueHost.classList.add('ei-venue-builder');venueHost.dataset.venueBuilder='';
raw.venues?.closest('label')?.parentNode?.insertBefore(venueHost,raw.venues.closest('label').nextSibling);
function renderVenues(){
  const items=parseVenues(),list=$('.ei-builder-list',venueHost);list.textContent='';
  if(!items.length){const empty=document.createElement('div');empty.className='ei-builder-empty';empty.textContent='No additional venues. The primary venue above is still used.';list.append(empty)}
  items.forEach((item,index)=>{
    const card=document.createElement('article');card.className='ei-builder-card';card.draggable=true;card.innerHTML=`<div class="ei-builder-row"><button type="button" class="ei-builder-handle" title="Drag to reorder">⋮⋮</button><strong>Venue ${index+1}</strong><div class="ei-builder-actions"></div></div><div class="ei-builder-grid"><label>English name<input data-key="name"></label><label>English address<input data-key="address"></label></div><div class="ei-builder-grid"><label>Khmer name<input class="khmer-input" data-key="nameKm"></label><label>Khmer address<input class="khmer-input" data-key="addressKm"></label></div><div class="ei-builder-grid"><label>Map URL<input data-key="mapUrl" type="url" placeholder="https://maps.google.com/..."></label><span></span></div>`;
    ['name','address','nameKm','addressKm','mapUrl'].forEach(key=>card.querySelector(`[data-key="${key}"]`).value=item[key]||'');
    const actions=$('.ei-builder-actions',card),up=makeButton('↑','Move earlier'),down=makeButton('↓','Move later'),del=makeButton('×','Remove');del.className='danger';actions.append(up,down,del);
    card.querySelectorAll('input').forEach(input=>input.addEventListener('input',()=>{const next=parseVenues();const current=next[index]||{};['name','address','nameKm','addressKm','mapUrl'].forEach(key=>current[key]=card.querySelector(`[data-key="${key}"]`).value);next[index]=current;writeVenues(next)}));
    up.onclick=()=>{const next=parseVenues();if(index<=0)return;[next[index-1],next[index]]=[next[index],next[index-1]];writeVenues(next);renderVenues()};down.onclick=()=>{const next=parseVenues();if(index>=next.length-1)return;[next[index+1],next[index]]=[next[index],next[index+1]];writeVenues(next);renderVenues()};del.onclick=async()=>{if(!(await uiConfirm('Remove this additional venue?',{title:'Remove venue',danger:true,confirmText:'Remove'})))return;const next=parseVenues();next.splice(index,1);writeVenues(next);renderVenues()};
    card.addEventListener('dragstart',e=>{card.classList.add('dragging');e.dataTransfer.setData('text/plain',String(index))});card.addEventListener('dragend',()=>card.classList.remove('dragging'));card.addEventListener('dragover',e=>{e.preventDefault();card.classList.add('drag-over')});card.addEventListener('dragleave',()=>card.classList.remove('drag-over'));card.addEventListener('drop',e=>{e.preventDefault();card.classList.remove('drag-over');const from=Number(e.dataTransfer.getData('text/plain')),to=index;if(!Number.isInteger(from)||from===to)return;const next=parseVenues(),[moved]=next.splice(from,1);next.splice(to,0,moved);writeVenues(next);renderVenues()});list.append(card)
  })
}
venueHost.addButton.onclick=()=>{const items=parseVenues();items.push({name:'',address:'',mapUrl:'',nameKm:'',addressKm:''});writeVenues(items);renderVenues();setTimeout(()=>venueHost.querySelector('.ei-builder-card:last-child input')?.focus(),0)};

const sectionLabels={gallery:['▦','Gallery'],video:['▶','Featured video'],countdown:['◷','Countdown'],schedule:['≡','Schedule'],custom:['◇','Custom blocks'],venue:['⌖','Venue'],contact:['☎','Contact'],wishes:['♡','Guest wishes'],rsvp:['✓','RSVP']};
const sectionHost=builderShell('Guest-page structure','Drag functional sections and visual pages into the exact published order.');sectionHost.classList.add('ei-section-order-builder');sectionHost.dataset.sectionOrderBuilder='';
raw.section?.closest('label')?.parentNode?.insertBefore(sectionHost,raw.section.closest('label').nextSibling);
function labelForToken(token){if(sectionLabels[token])return{icon:sectionLabels[token][0],label:sectionLabels[token][1],detail:'Functional section'};if(token.startsWith('page:')){const id=token.slice(5),page=(window.state?.designPages||[]).find(x=>x.id===id);return{icon:'▣',label:page?.name||'Visual page',detail:'Free-form visual page'}}return{icon:'•',label:token,detail:'Section'}}
function renderSections(){const items=parseSections(),list=$('.ei-builder-list',sectionHost);list.textContent='';items.forEach((token,index)=>{const meta=labelForToken(token),card=document.createElement('article');card.className='ei-builder-card ei-builder-section-card';card.draggable=true;card.innerHTML=`<button type="button" class="ei-builder-handle" title="Drag to reorder">⋮⋮</button><div class="ei-section-token"><span class="ei-section-icon"></span><div><strong></strong><small></small></div></div><div class="ei-builder-actions"></div>`;card.querySelector('.ei-section-icon').textContent=meta.icon;card.querySelector('strong').textContent=meta.label;card.querySelector('small').textContent=meta.detail;const actions=$('.ei-builder-actions',card),up=makeButton('↑','Move earlier'),down=makeButton('↓','Move later');actions.append(up,down);up.onclick=()=>{const next=parseSections();if(index<=0)return;[next[index-1],next[index]]=[next[index],next[index-1]];writeSections(next);renderSections()};down.onclick=()=>{const next=parseSections();if(index>=next.length-1)return;[next[index+1],next[index]]=[next[index],next[index+1]];writeSections(next);renderSections()};card.addEventListener('dragstart',e=>{card.classList.add('dragging');e.dataTransfer.setData('text/plain',String(index))});card.addEventListener('dragend',()=>card.classList.remove('dragging'));card.addEventListener('dragover',e=>{e.preventDefault();card.classList.add('drag-over')});card.addEventListener('dragleave',()=>card.classList.remove('drag-over'));card.addEventListener('drop',e=>{e.preventDefault();card.classList.remove('drag-over');const from=Number(e.dataTransfer.getData('text/plain')),to=index;if(!Number.isInteger(from)||from===to)return;const next=parseSections(),[moved]=next.splice(from,1);next.splice(to,0,moved);writeSections(next);renderSections()});list.append(card)})}

function refreshAll(){renderSchedule();renderVenues();renderSections()}
window.addEventListener('einvite:state-applied',refreshAll);window.addEventListener('einvite:structure-changed',refreshAll);
let lastSnapshot='';setInterval(()=>{const snapshot=[raw.section?.value,raw.schedule?.value,raw.scheduleKm?.value,raw.venues?.value,raw.venuesKm?.value].join('\u0001');if(snapshot!==lastSnapshot){lastSnapshot=snapshot;refreshAll()}},700);
refreshAll();
})();
