;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const page=document.body?.dataset.page||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''));
if(document.body&&!document.body.dataset.page)document.body.dataset.page=page;
/* V55 (dispatch Group 2): the previous dashboard-home layer is retired. It injected a
   fixed 76px rail, a marketing hero ("What will you create today?"), a second search
   field and an English-only quick-create row, and it hid the real .dash-head. The shell
   now owns the welcome row, the filter row and the card grid; dashboard-polish.js owns
   the loading / empty / error states. See docs/reviews/redesign-report.md. */
function dashboard(){ /* retired in v55 */ }
function materials(){
  const head=$('.library-head'),upload=$('.upload-box');if(!head||!upload)return;
  const toggle=document.createElement('button');toggle.type='button';toggle.className='material-upload-toggle primary';toggle.innerHTML='<span>⇧</span> Upload files';head.append(toggle);upload.hidden=true;
  toggle.onclick=()=>{upload.hidden=!upload.hidden;toggle.innerHTML=upload.hidden?'<span>⇧</span> Upload files':'<span>×</span> Close upload';if(!upload.hidden)setTimeout(()=>$('#uploadFile')?.focus(),50)};
  const grid=$('#grid');
  const observer=new MutationObserver(()=>{
    const empty=$('.empty-library',grid);if(empty&&/Authentication required/i.test(empty.textContent)&&!empty.querySelector('.material-auth-action')){const a=document.createElement('a');a.href='dashboard.html';a.className='material-auth-action';a.innerHTML='<button type="button" class="primary">Sign in to use materials</button>';empty.append(a)}
  });observer.observe(grid,{childList:true,subtree:true});
}
function editor(){
  const main=$('body.studio-experience>main'),rail=$('.studio-tool-rail'),host=$('.studio-pane-host'),stage=$('#stage');if(!main||!rail||!host||!stage)return;
  if(!$('[data-studio-tab="text"]',rail)){
    const elementsBtn=$('[data-studio-tab="elements"]',rail);
    const b=document.createElement('button');b.type='button';b.className='studio-rail-button';b.dataset.studioTab='text';b.innerHTML='<span class="studio-nav-icon">T</span><span>Text</span>';b.title='Text, fonts and typography';rail.insertBefore(b,elementsBtn||null);
    const pane=document.createElement('section');pane.className='studio-pane studio-text-pane';pane.dataset.studioPane='text';pane.innerHTML=`
      <div class="studio-pane-heading"><div><small>Create</small><h1>Text</h1></div></div>
      <label class="refine-text-search"><span>⌕</span><input type="search" placeholder="Search fonts and combinations"></label>
      <button type="button" class="refine-add-text">T &nbsp; Add a text box</button>
      <button type="button" class="refine-magic-write">✦ Magic invitation writing</button>
      <section class="refine-text-section"><div><h3>Default text styles</h3></div><div class="refine-text-presets">
        <button class="refine-text-preset heading" data-refine-text="heading">Add a heading</button>
        <button class="refine-text-preset subheading" data-refine-text="subheading">Add a subheading</button>
        <button class="refine-text-preset body" data-refine-text="body">Add a little bit of body text</button>
        <button class="refine-text-preset khmer" data-refine-text="khmer" lang="km">សិរីមង្គលអាពាហ៍ពិពាហ៍</button>
      </div></section>
      <section class="refine-text-section"><div><h3>Fonts</h3><small>Search · Khmer · Favorites</small></div><button type="button" class="refine-browse-fonts">Browse all fonts</button></section>
      <section class="refine-text-section"><div><h3>Font combinations</h3><small>Quick invitation styles</small></div><div class="refine-font-combos">
        <button class="refine-font-combo" data-combo="gold"><span style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
        <button class="refine-font-combo" data-combo="modern"><span style="font-family:Arial,sans-serif;font-weight:800">TITLE<br><i>HEADING</i></span><small>Modern contrast</small></button>
        <button class="refine-font-combo" data-combo="romance"><span style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
        <button class="refine-font-combo" data-combo="khmer"><span lang="km" style="font-family:'Noto Serif Khmer','Khmer OS Muol Light',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
      </div></section>`;
    host.append(pane);
    function activate(id){
      $$('[data-studio-tab]',rail).forEach(x=>x.classList.toggle('active',x.dataset.studioTab===id));
      $$('[data-studio-pane]',host).forEach(x=>x.classList.toggle('active',x.dataset.studioPane===id));
      localStorage.setItem('einvite-editor-left-tab',id);applyMode();
    }
    b.onclick=()=>activate('text');
    $('.refine-add-text',pane).onclick=()=>$('#addText')?.click();
    $$('.refine-text-preset',pane).forEach(btn=>btn.onclick=()=>{const source=$(`[data-text-preset="${btn.dataset.refineText}"]`);if(source)source.click();else $('#addText')?.click()});
    $('.refine-browse-fonts',pane).onclick=()=>$('.ei-font-launch')?.click();
    $('.refine-magic-write',pane).onclick=()=>{const ebtn=$('[data-studio-tab="event"]',rail);ebtn?.click();setTimeout(()=>$('#eiAiStudio textarea,.ei-ai-studio textarea')?.focus(),80)};
    const comboMap={gold:{font:'serif-georgia',size:48,color:'#b48a20',text:'Golden Hour'},modern:{font:'sans-arial',size:44,color:'#202127',text:'Your Celebration'},romance:{font:'serif-georgia',size:46,color:'#426b52',text:'Bride & Groom'},khmer:{font:"noto-serif-khmer",size:38,color:'#9b6b13',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍'}};
    $$('.refine-font-combo',pane).forEach(btn=>btn.onclick=()=>{const c=comboMap[btn.dataset.combo];$('#addText')?.click();setTimeout(()=>{const sel=$('.object.selected,.object.multi-selected');if(!sel)return;const content=sel.querySelector('.content');if(content)content.textContent=c.text;sel.dataset.font=c.font;sel.dataset.fontSize=String(c.size);sel.dataset.color=c.color;try{applyObjectVisualStyle(sel);save()}catch{}},40)});
    $('.refine-text-search input',pane).oninput=e=>{const q=e.target.value.toLowerCase();$$('.refine-text-preset,.refine-font-combo',pane).forEach(x=>x.hidden=!!q&&!x.textContent.toLowerCase().includes(q))};
  }
  function applyMode(){ /* centralized elsewhere */ }
  const openInspector=()=>{if(innerWidth<=1180&&$('.object.selected,.object.multi-selected',stage))document.body.classList.add('inspector-open')};
  stage.addEventListener('pointerup',()=>setTimeout(openInspector,0));
  document.addEventListener('keydown',e=>{if(e.key==='Escape')document.body.classList.remove('inspector-open')});
  const inspector=$('.right');if(inspector&&!inspector.querySelector('.refine-inspector-close')){const c=document.createElement('button');c.type='button';c.className='refine-inspector-close';c.textContent='×';c.title='Close inspector';c.onclick=()=>document.body.classList.remove('inspector-open');inspector.prepend(c)}
}
if(page==='dashboard')dashboard();
if(page==='materials')materials();
if(page==='index')setTimeout(editor,0);
})();