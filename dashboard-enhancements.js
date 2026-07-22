/* Professional template discovery enhancements. Loaded after dashboard.js. */
const builtInFavoriteKey = 'sovan-builtin-template-favorites-v1';
let previewTemplateItem = null;

function readBuiltInFavorites(){
  try{return new Set(JSON.parse(localStorage.getItem(builtInFavoriteKey)||'[]'))}catch{return new Set()}
}
function writeBuiltInFavorites(set){localStorage.setItem(builtInFavoriteKey,JSON.stringify([...set]))}
function templateDoc(item){
  if(item.kind==='user'||item.kind==='market') return item.document||{};
  try{return builtInDocument('Your Event',item.category==='Business'?'Business':item.category||'Wedding',item.id)}catch{return {fields:{names:item.name},palette:{background:'#fff7f3',text:'#342c26',heading:'#9d4555'},designPages:[],objects:{}}}
}
function stripMarkup(value){const div=document.createElement('div');div.innerHTML=String(value||'');return div.textContent||div.innerText||''}
function templatePalette(doc,item){
  const palette=doc?.palette||{};
  const tone={rose:['#fff7f3','#412e32','#9d4555'],gold:['#fffaf0','#3c2b18','#9b6b13'],emerald:['#eff8f2','#263c34','#1f7158'],midnight:['#0f0d16','#f0ebf8','#bca7ff'],ivory:['#f7f4ed','#293444','#213b5a'],custom:['#f5f1ff','#3d3151','#6d4bc3']}[item?.tone]||['#fff7f3','#342c26','#9d4555'];
  return {background:palette.background||tone[0],text:palette.text||tone[1],heading:palette.heading||doc?.accent||tone[2],accent:doc?.accent||palette.heading||tone[2]}
}
function templateTitle(doc,item){
  const title=doc?.objects?.title?.html||doc?.fields?.names||item?.name||'Invitation';
  return stripMarkup(title).slice(0,55)
}
function liveThumbnail(item){
  const doc=templateDoc(item),p=templatePalette(doc,item),title=templateTitle(doc,item);
  const imageObject=Object.values(doc?.objects||{}).find(o=>o?.type==='image'&&o?.src);
  const bg=imageObject?.src?`background-image:linear-gradient(#fff8,#fff8),url('${escapeHtml(imageObject.src)}');background-size:cover;background-position:center;`:'';
  return `<div class="template-live-thumb" style="--thumb-bg:${p.background};--thumb-text:${p.text};--thumb-heading:${p.heading};--thumb-accent:${p.accent};${bg}"><span class="mini-dot a"></span><span class="mini-dot b"></span><span class="mini-frame"></span><strong class="mini-title">${escapeHtml(title)}</strong></div>`
}
function allTemplateItemsEnhanced(){
  const favorites=readBuiltInFavorites();
  return [
    ...templateCatalog.map(t=>({...t,kind:'builtin',favorite:favorites.has(t.id)})),
    ...userTemplates.map(t=>({
      id:`user:${t.id}`,sourceId:t.id,name:t.name,category:t.category||'Wedding',tone:'custom',
      description:t.description||`Your reusable complete invitation · ${(t.document?.designPages||[]).length} visual pages`,
      tags:t.tags||[],pages:(t.document?.designPages||[]).length,kind:'user',document:t.document,
      favorite:!!t.favorite,currentVersion:t.currentVersion||1,updatedAt:t.updatedAt
    })),
    ...marketTemplates.map(t=>({
      id:`market:${t.id}`,sourceId:t.id,name:t.name,category:t.category||'Wedding',tone:'custom',
      description:t.description||`Shared marketplace template · ${(t.document?.designPages||[]).length} visual pages`,
      tags:t.tags||[],pages:(t.document?.designPages||[]).length,kind:'market',document:t.document,
      favorite:readBuiltInFavorites().has(`market:${t.id}`),currentVersion:t.currentVersion||1,updatedAt:t.updatedAt
    }))
  ]
}
allTemplateItems = allTemplateItemsEnhanced;

async function toggleTemplateFavorite(item){
  if(item.kind==='builtin'||item.kind==='market'){
    const favorites=readBuiltInFavorites(),key=item.kind==='market'?`market:${item.sourceId}`:item.id;favorites.has(key)?favorites.delete(key):favorites.add(key);writeBuiltInFavorites(favorites)
  }else if(server){
    const updated=await request(`/api/templates/${item.sourceId}`,{method:'PUT',body:JSON.stringify({favorite:!item.favorite})});
    const index=userTemplates.findIndex(x=>x.id===item.sourceId);if(index>=0)userTemplates[index]=updated
  }else{
    const index=userTemplates.findIndex(x=>x.id===item.sourceId);if(index>=0){userTemplates[index].favorite=!item.favorite;localStorage.setItem(localTemplatesKey,JSON.stringify(userTemplates))}
  }
  renderTemplateChoices()
}

renderTemplateChoices = function(){
  const q=($('#templateSearch').value||'').trim().toLowerCase(),selected=$('#newTemplate').value;
  let items=allTemplateItems().filter(t=>{
    const filterOk=templateFilter==='all'||(templateFilter==='mine'&&t.kind==='user')||(templateFilter==='marketplace'&&t.kind==='market')||(templateFilter==='favorites'&&t.favorite)||t.category===templateFilter;
    return filterOk&&(!q||`${t.name} ${t.description} ${(t.tags||[]).join(' ')}`.toLowerCase().includes(q))
  });
  const grid=$('#templateChoices');grid.innerHTML='';if(!items.length)grid.innerHTML='<div class="template-empty">No templates match this filter.</div>';
  items.forEach(t=>{
    const card=document.createElement('div');card.className=`template-choice${selected===t.id?' active':''}`;card.tabIndex=0;card.setAttribute('role','button');card.dataset.templateChoice=t.id;card.dataset.tone=t.tone||'custom';
    card.innerHTML=`${liveThumbnail(t)}<div class="template-meta"><strong>${escapeHtml(t.name)}</strong><small>${escapeHtml(t.description||'Reusable invitation design')}</small></div><div class="template-choice-actions"><button type="button" class="favorite${t.favorite?' active':''}" title="${t.favorite?'Remove from favorites':'Add to favorites'}">★</button></div><button type="button" class="preview-card-btn">Preview</button>`;
    card.querySelector('.favorite').onclick=async e=>{e.stopPropagation();try{await toggleTemplateFavorite(t)}catch(error){alert(error.message)}};
    card.querySelector('.preview-card-btn').onclick=e=>{e.stopPropagation();openTemplatePreview(t)};
    if(t.kind==='user'){
      const remove=document.createElement('button');remove.type='button';remove.className='custom-template-remove';remove.title='Delete template';remove.textContent='×';
      remove.onclick=async e=>{e.stopPropagation();if(!(await uiConfirm(`Delete template “${t.name}”?`,{title:'Delete template',danger:true,confirmText:'Delete'})))return;try{if(server)await request(`/api/templates/${t.sourceId}`,{method:'DELETE'});else{userTemplates=userTemplates.filter(x=>x.id!==t.sourceId);localStorage.setItem(localTemplatesKey,JSON.stringify(userTemplates))}await loadTemplates();if($('#newTemplate').value===t.id)$('#newTemplate').value='rose';renderTemplateChoices()}catch(error){alert(error.message)}};card.append(remove)
    }
    card.onclick=()=>{$('#newTemplate').value=t.id;renderTemplateChoices();updateTemplateSummary(t)};
    card.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();card.click()}};grid.append(card)
  });
  const active=items.find(t=>t.id===selected)||allTemplateItems().find(t=>t.id===selected);if(active)updateTemplateSummary(active)
};

updateTemplateSummary = function(t){
  const version=t.kind==='user'?` · Version ${t.currentVersion||1}`:'';
  $('#templateSummary').textContent=`${t.name} · ${t.category} · ${t.pages||0} visual page${Number(t.pages||0)===1?'':'s'}${version} · ${t.kind==='user'?'Saved by you':t.kind==='market'?'Shared marketplace template':'Built-in professional template'}`
};

function previewObjectMarkup(obj){
  if(!obj||typeof obj!=='object')return'';
  const style=`left:${obj.left||'10%'};top:${obj.top||'10%'};width:${obj.width||'80%'};height:${obj.height||'80px'};position:absolute;transform:rotate(${Number(obj.rotation||0)}deg);opacity:${Number(obj.opacity||1)};color:${obj.color||'#342c26'};font-family:${obj.font||'Georgia,serif'};font-size:${Math.max(8,Math.min(34,Number(obj.fontSize||22)))}px;text-align:${obj.textAlign||'center'};overflow:hidden;`;
  if(obj.type==='image'&&obj.src)return `<img src="${escapeHtml(obj.src)}" alt="" style="${style}object-fit:cover;border-radius:${Number(obj.borderRadius||0)}px">`;
  if(obj.type==='shape')return `<span style="${style}background:${obj.fillColor||'#d9a6ad'};border-radius:${obj.shapeKind==='circle'?'50%':Number(obj.borderRadius||0)+'px'}"></span>`;
  if(obj.type==='decoration')return `<span style="${style}display:flex;align-items:center;justify-content:center">${escapeHtml(stripMarkup(obj.html||'✦'))}</span>`;
  if(obj.type==='text'||obj.html)return `<div style="${style}">${escapeHtml(stripMarkup(obj.html||''))}</div>`;
  return''
}
function previewPageMarkup(page,master){
  const bg=page.useMasterBackground&&master?.enabled?master:page;const image=bg?.backgroundImage?`background-image:linear-gradient(rgba(0,0,0,${Number(bg.backgroundOverlay||0)/100}),rgba(0,0,0,${Number(bg.backgroundOverlay||0)/100})),url('${escapeHtml(bg.backgroundImage)}');background-size:${bg.backgroundSize||'cover'};background-position:center;`:'';
  const title=page.name||'Visual page';
  return `<div class="template-preview-page" style="--page-bg:${escapeHtml(bg?.background||'#fff')};${image}"><div><strong>${escapeHtml(title)}</strong><small style="display:block;margin-top:6px;opacity:.7">${Object.keys(page.objects||{}).length} design objects</small></div></div>`
}
function openTemplatePreview(item){
  previewTemplateItem=item;const doc=templateDoc(item),p=templatePalette(doc,item),pages=doc.designPages||[],title=templateTitle(doc,item),heroObjects=Object.values(doc.objects||{}).slice(0,24).map(previewObjectMarkup).join('');
  $('#templatePreviewBody').innerHTML=`<div class="template-preview-shell"><div class="template-preview-phone"><div class="template-preview-screen" style="--p-bg:${p.background};--p-text:${p.text};--p-heading:${p.heading}"><section class="template-preview-hero"><h2>${escapeHtml(title)}</h2>${heroObjects}</section><div class="template-preview-pages">${pages.map(page=>previewPageMarkup(page,doc.masterPageStyle)).join('')}<div class="template-preview-page"><div><strong>Event sections</strong><small style="display:block;margin-top:6px;opacity:.7">${(doc.sectionOrder||[]).filter(x=>!String(x).startsWith('page:')).join(' · ')||'Flexible sections'}</small></div></div></div></div></div><div class="template-preview-info"><p class="invite-kicker">${escapeHtml(item.category||'Invitation')} template</p><h2>${escapeHtml(item.name)}</h2><p>${escapeHtml(item.description||'Reusable invitation design')}</p><div class="template-preview-tags">${(item.tags||[]).map(tag=>`<span>${escapeHtml(tag)}</span>`).join('')}</div><div class="template-preview-features"><div class="template-preview-feature"><strong>${pages.length}</strong><br><small>Visual pages</small></div><div class="template-preview-feature"><strong>${Object.keys(doc.objects||{}).length}</strong><br><small>Hero objects</small></div><div class="template-preview-feature"><strong>${item.kind==='user'||item.kind==='market'?'Version '+(item.currentVersion||1):'Curated'}</strong><br><small>${item.kind==='user'?'Your template':item.kind==='market'?'Shared template':'Built-in design'}</small></div><div class="template-preview-feature"><strong>${doc.languageMode==='both'?'Bilingual ready':'Flexible'}</strong><br><small>Content system</small></div></div><div class="preview-page-list">${pages.map((page,i)=>`<div><span>${i+1}. ${escapeHtml(page.name||'Visual page')}</span><small>${escapeHtml(page.preset||'custom')}</small></div>`).join('')}</div></div></div>`;
  $('#templatePreviewDialog').showModal()
}

$('#closeTemplatePreview').onclick=()=>$('#templatePreviewDialog').close();
$('#usePreviewTemplate').onclick=()=>{if(!previewTemplateItem)return;$('#newTemplate').value=previewTemplateItem.id;updateTemplateSummary(previewTemplateItem);renderTemplateChoices();$('#templatePreviewDialog').close()};
$('#templateSearch').oninput=renderTemplateChoices;
document.querySelectorAll('[data-template-filter]').forEach(b=>b.onclick=()=>{templateFilter=b.dataset.templateFilter;document.querySelectorAll('[data-template-filter]').forEach(x=>x.classList.toggle('active',x===b));renderTemplateChoices()});
