(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const page=window.__EINVITE_PAGE||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''))||'dashboard';
document.body.dataset.page=page;

function wireAuthLayouts(){
  if(page==='dashboard'){
    const login=$('#loginView');
    if(login && !login.querySelector('.canvas-auth-panel')){
      const title=$('h1',login)?.textContent||'Welcome back';
      const intro=$('p',login)?.textContent||'Sign in to manage your invitations.';
      const email=$('#email',login), password=$('#password',login), button=$('#loginBtn',login);
      const forgot=login.querySelector('a[href="reset.html"]');
      const hint=login.querySelector('.hint');
      const panel=document.createElement('div'); panel.className='canvas-auth-panel';
      const visual=document.createElement('div'); visual.className='canvas-auth-visual';
      visual.innerHTML=`<div><span class="canvas-auth-badge">✦ Invitation Studio</span></div>
        <div><h1>Design invitations that feel premium, personal, and alive.</h1><p>A creative workspace inspired by modern design tools, specialized for invitation websites, guest management, RSVP, Khmer dates, music, galleries, and event publishing.</p></div>
        <div class="canvas-auth-bullets">
          <div><span>1</span><div><strong>Design like a studio</strong><small>Canva-like creation flow with invitation-first templates, layered editing, animations, and polished publishing.</small></div></div>
          <div><span>2</span><div><strong>Run the event</strong><small>Publish links, manage guests, collect RSVPs, generate QR codes, and review analytics in one platform.</small></div></div>
          <div><span>3</span><div><strong>Built for Cambodia</strong><small>Khmer/English content, Khmer lunar dates, YouTube music, elegant wedding styling, and mobile-friendly guest viewing.</small></div></div>
        </div>`;
      const formWrap=document.createElement('div');
      formWrap.innerHTML=`<div class="canvas-auth-tabs"><button type="button" data-mode="signin" class="active">Sign in</button><button type="button" data-mode="register">Create account</button></div>
        <div><h2>${title}</h2><p>${intro}</p></div>
        <div class="canvas-auth-form"></div>
        <div class="canvas-auth-status"></div>`;
      const formHost=$('.canvas-auth-form',formWrap), status=$('.canvas-auth-status',formWrap);
      const confirmWrap=document.createElement('label'); confirmWrap.hidden=true; confirmWrap.innerHTML='Confirm password<input id="confirmPasswordRegister" type="password" autocomplete="new-password" minlength="8">';
      const options=document.createElement('div'); options.className='canvas-auth-actions';
      options.innerHTML=`<div class="canvas-auth-links"><a href="reset.html">Forgot password?</a><span class="canvas-auth-note">The local demo still works when the development backend is offline.</span></div>`;
      [email?.closest('label'), password?.closest('label')].forEach(el=>{ if(el) formHost.append(el);});
      formHost.append(confirmWrap);
      if(button) { button.classList.add('primary'); button.textContent='Sign in'; options.prepend(button); }
      if(forgot?.parentElement) forgot.parentElement.remove();
      if(hint) hint.remove();
      panel.append(formWrap, options, status);
      login.textContent=''; login.append(visual,panel);
      let mode='signin';
      const switchMode=(next)=>{
        mode=next; $$('[data-mode]',formWrap).forEach(b=>b.classList.toggle('active',b.dataset.mode===next));
        confirmWrap.hidden=next!=='register';
        if(button) button.textContent=next==='register'?'Create account':'Sign in';
        $('h2',formWrap).textContent=next==='register'?'Create account':'Welcome back';
        $('p',formWrap).textContent=next==='register'?'Create a clean workspace for managing invitations, templates, guests, and published events.':'Sign in to continue working on invitations, templates, materials, and guest management.';
        status.textContent='';
      };
      $$('[data-mode]',formWrap).forEach(b=>b.onclick=()=>switchMode(b.dataset.mode));
      const handle=async()=>{
        const em=email?.value.trim()||'', pw=password?.value||'', cp=$('#confirmPasswordRegister')?.value||'';
        if(!/^.+@.+\..+$/.test(em)) return status.textContent='Enter a valid email address.';
        if(pw.length<8) return status.textContent='Use a password of at least 8 characters.';
        if(mode==='register' && pw!==cp) return status.textContent='The passwords do not match.';
        status.textContent=mode==='register'?'Creating account…':'Signing in…';
        button && (button.disabled=true);
        try{
          const endpoint=mode==='register'?'/api/auth/register':'/api/auth/login';
          let result=null;
          try{
            const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:em,password:pw})});
            const data=await r.json().catch(()=>({}));
            if(r.ok){ result=data; }
            else if(mode==='signin') throw new Error(data.error||'Sign in failed');
            else throw new Error(data.error||'Account creation failed');
          }catch(err){
            if(mode==='signin' && /Failed to fetch|NetworkError|fetch/i.test(String(err))){
              localStorage.setItem('sovan-account-v1',JSON.stringify({id:crypto.randomUUID(),email:em,role:'customer',plan:'Free'}));
              location.reload(); return;
            }
            if(mode==='register' && /Failed to fetch|NetworkError|fetch/i.test(String(err))){
              localStorage.setItem('sovan-account-v1',JSON.stringify({id:crypto.randomUUID(),email:em,role:'customer',plan:'Free'}));
              location.reload(); return;
            }
            throw err;
          }
          if(result?.token) localStorage.setItem('sovan-auth-token',result.token);
          if(result?.user) localStorage.setItem('sovan-account-v1',JSON.stringify(result.user));
          else localStorage.setItem('sovan-account-v1',JSON.stringify({id:crypto.randomUUID(),email:em,role:'customer',plan:'Free'}));
          location.reload();
        }catch(error){
          status.textContent=error.message||'Authentication failed.';
        }finally{button && (button.disabled=false)}
      };
      button && (button.onclick=handle);
      password?.addEventListener('keydown',e=>{if(e.key==='Enter') handle()});
      $('#confirmPasswordRegister')?.addEventListener('keydown',e=>{if(e.key==='Enter') handle()});
    }
  }
  if(page==='reset'){
    const main=$('.auth-page');
    if(main && !main.querySelector('.canvas-auth-visual')){
      const visual=document.createElement('div'); visual.className='canvas-auth-visual';
      visual.innerHTML=`<div><span class="canvas-auth-badge">✦ Secure access</span></div>
        <div><h2>Recover account access cleanly and safely.</h2><p>Reset links, account verification, and password changes follow the same modern system used throughout the platform.</p></div>
        <div class="canvas-auth-bullets"><div><span>✓</span><div><strong>Simple request flow</strong><small>Request a reset link using the email tied to the account.</small></div></div><div><span>✓</span><div><strong>Clean confirmation step</strong><small>Choose a new password with a clear, minimal form.</small></div></div></div>`;
      const panel=document.createElement('div'); panel.className='canvas-auth-panel';
      const request=$('#requestView',main), confirm=$('#confirmView',main);
      panel.append(request,confirm); main.prepend(visual); main.append(panel);
    }
  }
  if(page==='verify'){
    const main=$('.verify-page');
    if(main && !main.querySelector('.canvas-auth-visual')){
      const heading=main.querySelector('h1'), status=$('#status',main), action=main.querySelector('a');
      const visual=document.createElement('div'); visual.className='canvas-auth-visual';
      visual.innerHTML=`<div><span class="canvas-auth-badge">✦ Account security</span></div>
        <div><h2>One more step to confirm your email.</h2><p>Verification keeps invitation accounts safer and improves trust for guest communications, sharing, and account recovery.</p></div>`;
      const panel=document.createElement('div'); panel.className='canvas-auth-panel';
      if(heading){heading.textContent='Email verification';panel.append(heading)}
      if(status)panel.append(status);
      if(action)panel.append(action);
      main.prepend(visual);main.append(panel);
    }
  }
}

function enhanceMaterialsPage(){
  if(page!=='materials')return;
  const box=$('.upload-box'),input=$('#uploadFile'),button=$('#uploadBtn');
  if(!box||!input||!button||box.querySelector('.canvas-upload-drop'))return;
  const drop=document.createElement('div');drop.className='canvas-upload-drop';drop.tabIndex=0;drop.innerHTML=`<div class="canvas-upload-icon">⇧</div><div><strong>Drop files here</strong><span>Upload photos, audio, or video — multiple files supported</span></div><button type="button">Browse files</button>`;
  box.insertBefore(drop,box.querySelector('.upload-row'));
  const browse=drop.querySelector('button');browse.onclick=()=>input.click();
  const setFiles=files=>{const valid=[...files].filter(file=>file&&file.size);if(!valid.length)return;const dt=new DataTransfer();valid.forEach(file=>dt.items.add(file));input.files=dt.files;drop.querySelector('strong').textContent=`${valid.length} file${valid.length===1?'':'s'} ready`;drop.querySelector('span').textContent=valid.map(file=>file.name).slice(0,3).join(' · ')+(valid.length>3?` +${valid.length-3} more`:'');};
  input.addEventListener('change',()=>setFiles(input.files));
  ['dragenter','dragover'].forEach(type=>drop.addEventListener(type,e=>{e.preventDefault();drop.classList.add('drag-over')}));
  ['dragleave','drop'].forEach(type=>drop.addEventListener(type,e=>{e.preventDefault();drop.classList.remove('drag-over')}));
  drop.addEventListener('drop',e=>setFiles(e.dataTransfer.files));
  drop.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();input.click()}});
  document.addEventListener('paste',e=>{if(['INPUT','TEXTAREA'].includes(document.activeElement?.tagName))return;const files=[...e.clipboardData.items].filter(x=>x.kind==='file').map(x=>x.getAsFile()).filter(Boolean);if(files.length){e.preventDefault();setFiles(files);window.uiToast?.(`${files.length} pasted file${files.length===1?'':'s'} ready to upload`,'⇧')}});
}

function editorEnhancements(){
  const stage=$('#stage'); if(!stage) return;
  const header=document.querySelector('body>header');
  if(header && !header.querySelector('.canvas-header-more')){
    const saveState=$('#saveState'),serverState=$('#serverState');
    if(saveState||serverState){const status=document.createElement('div');status.className='canvas-header-status';if(saveState)status.append(saveState);if(serverState)status.append(serverState);const before=$('#studioCommandBtn')||$('#previewBtn');header.insertBefore(status,before)}
    const undo=$('#undoBtn'),redo=$('#redoBtn'),preview=$('#previewBtn'),publish=$('#publishBtn'),actions=$('#studioCommandBtn'),check=$('#studioCheckBtn');
    if(undo){undo.innerHTML='↶';undo.setAttribute('aria-label','Undo');undo.title='Undo (Ctrl/Cmd+Z)';undo.classList.add('canvas-icon-button')}
    if(redo){redo.innerHTML='↷';redo.setAttribute('aria-label','Redo');redo.title='Redo (Ctrl/Cmd+Shift+Z)';redo.classList.add('canvas-icon-button')}
    if(actions)actions.textContent='Actions';if(check)check.textContent='Check';if(preview)preview.textContent='Preview';if(publish)publish.textContent='Publish';
    const more=document.createElement('div');more.className='canvas-header-more';more.innerHTML='<button type="button" class="canvas-header-more-trigger" aria-label="More editor actions" aria-expanded="false">•••</button><div class="canvas-header-more-menu" hidden><strong>Project</strong></div>';
    header.append(more);const menu=$('.canvas-header-more-menu',more),trigger=$('.canvas-header-more-trigger',more);
    [$('#backupBtn'),$('#restoreBtn')].filter(Boolean).forEach(btn=>menu.append(btn));
    trigger.onclick=()=>{menu.hidden=!menu.hidden;trigger.setAttribute('aria-expanded',String(!menu.hidden))};
    document.addEventListener('pointerdown',e=>{if(!more.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
  }
  const activeObjects=()=>$$('.object.selected,.object.multi-selected').filter(x=>x.isConnected);
  const saveNow=()=>{ try{ typeof save==='function' && save(); }catch{} };
  const applyItems=(items)=>{ items.forEach(item=>{ try{ typeof applyObjectVisualStyle==='function' && applyObjectVisualStyle(item);}catch{} }); try{ typeof updateSelectionBounds==='function'&&updateSelectionBounds(); }catch{}; try{ typeof refreshSelectionUI==='function'&&refreshSelectionUI(); }catch{}; };
  const setSelectionIfNeeded=(obj)=>{ try{ if(!obj.classList.contains('selected')&&!obj.classList.contains('multi-selected')) typeof select==='function' && select(obj,false);}catch{} };
  const objectPane=$('[data-inspector-pane="object"]')||$('#properties')?.parentElement;
  const toast=(m,icon='✦')=>{ if(window.uiToast) window.uiToast(m,icon); else console.info(m); };
  const selectedOne=()=>activeObjects()[0]||null;
  const stagePercentFrame=(item)=>{
    if(!item)return{x:0,y:0,w:0,h:0,r:0};
    const sr=stage.getBoundingClientRect(),ir=item.getBoundingClientRect();
    return{x:(ir.left-sr.left)/sr.width*100,y:(ir.top-sr.top)/sr.height*100,w:ir.width/sr.width*100,h:ir.height/sr.height*100,r:Number(item.dataset.rotation||0)};
  };
  if(objectPane && !$('#canvasPlusTransform')){
    const block=document.createElement('section');block.className='final-advanced-inspector';block.id='canvasPlusTransform';
    block.innerHTML=`<div class="final-panel-title"><div><small>Transform</small><h2>Position & size</h2></div><span class="final-beta">Precise</span></div>
      <div class="canvas-transform-grid">
        <label>X %<input id="canvasTransformX" type="number" step="0.1"></label>
        <label>Y %<input id="canvasTransformY" type="number" step="0.1"></label>
        <label>W %<input id="canvasTransformW" type="number" step="0.1" min="1" max="100"></label>
        <label>H %<input id="canvasTransformH" type="number" step="0.1" min="1" max="100"></label>
        <label>Rotate°<input id="canvasTransformR" type="number" step="1" min="-360" max="360"></label>
        <label class="canvas-lock-ratio"><span>Keep ratio</span><input id="canvasTransformLockRatio" type="checkbox"></label>
      </div>
      <div class="canvas-transform-actions"><button type="button" data-transform-action="center">Center</button><button type="button" data-transform-action="fill-width">Fill width</button><button type="button" data-transform-action="reset-rotation">Reset rotation</button></div>`;
    objectPane.prepend(block);
    const ids={x:'canvasTransformX',y:'canvasTransformY',w:'canvasTransformW',h:'canvasTransformH',r:'canvasTransformR'};
    let ratio=1,updating=false;
    const refreshTransform=()=>{const item=selectedOne();block.classList.toggle('is-disabled',!item);if(!item)return;const f=stagePercentFrame(item);ratio=f.w/Math.max(.001,f.h);updating=true;Object.entries(ids).forEach(([key,id])=>{const map={x:f.x,y:f.y,w:f.w,h:f.h,r:f.r};$('#'+id).value=Number(map[key]).toFixed(key==='r'?0:1)});updating=false};
    const applyTransform=(key,value)=>{if(updating)return;const item=selectedOne();if(!item)return;let v=Number(value);if(!Number.isFinite(v))return;const frame=stagePercentFrame(item),lock=$('#canvasTransformLockRatio').checked;
      if(key==='x')item.style.left=`${Math.max(0,Math.min(100-frame.w,v))}%`;
      if(key==='y')item.style.top=`${Math.max(0,Math.min(100-frame.h,v))}%`;
      if(key==='w'){v=Math.max(1,Math.min(100,v));item.style.width=`${v}%`;if(lock)item.style.height=`${Math.max(1,Math.min(100,v/Math.max(.001,ratio)))}%`}
      if(key==='h'){v=Math.max(1,Math.min(100,v));item.style.height=`${v}%`;if(lock)item.style.width=`${Math.max(1,Math.min(100,v*ratio))}%`}
      if(key==='r'){item.dataset.rotation=String(v);item.style.transform=`rotate(${v}deg)`}
      applyItems([item]);saveNow();refreshTransform();
    };
    Object.entries(ids).forEach(([key,id])=>$('#'+id).addEventListener('change',e=>applyTransform(key,e.target.value)));
    block.addEventListener('click',e=>{const action=e.target.closest('[data-transform-action]')?.dataset.transformAction,item=selectedOne();if(!action||!item)return;const f=stagePercentFrame(item);if(action==='center'){item.style.left=`${(50-f.w/2).toFixed(2)}%`;item.style.top=`${(50-f.h/2).toFixed(2)}%`}if(action==='fill-width'){item.style.left='5%';item.style.width='90%'}if(action==='reset-rotation'){item.dataset.rotation='0';item.style.transform='rotate(0deg)'}applyItems([item]);saveNow();refreshTransform()});
    const obs=new MutationObserver(refreshTransform);obs.observe(stage,{subtree:true,attributes:true,attributeFilter:['class','style','data-rotation']});document.addEventListener('pointerup',()=>setTimeout(refreshTransform,0),true);refreshTransform();
  }
  const eventPane=$('[data-studio-pane="event"]');
  if(eventPane && !$('#canvasSmartWriter')){
    const assistant=document.createElement('section');assistant.className='canvas-smart-assistant';assistant.id='canvasSmartWriter';
    assistant.innerHTML=`<div class="final-panel-title"><div><small>AI assistant</small><h2>Invitation writing</h2></div><span class="final-beta">Smart</span></div>
      <label>Tone<select id="canvasSmartTone"><option value="formal">Formal & elegant</option><option value="romantic">Romantic</option><option value="modern">Modern & warm</option><option value="concise">Short & clean</option><option value="business">Business formal</option></select></label>
      <div class="canvas-ai-grid"><button type="button" id="canvasGenerateCopy">Generate wording</button><button type="button" id="canvasKhmerFormal">Khmer formal wording</button><button type="button" id="canvasSuggestPalette">Suggest palette</button><button type="button" id="canvasAutoHero">Auto polish hero</button></div>
      <p class="canvas-ai-hint">These built-in smart tools work offline. A future production AI provider can replace or extend them without changing the invitation document model.</p>`;
    const heading=eventPane.querySelector('.studio-pane-heading');heading?.after(assistant);
    const value=id=>$('#'+id)?.value?.trim()||'';
    const fire=(id,v)=>{const el=$('#'+id);if(!el)return;el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}))};
    const englishCopy=(tone)=>{const names=value('names')||'the hosts',date=value('date'),venue=value('venue');const datePart=date?` on ${new Date(date+'T00:00:00').toLocaleDateString(undefined,{year:'numeric',month:'long',day:'numeric'})}`:'';const venuePart=venue?` at ${venue}`:'';const map={
      formal:`Together with our families, ${names} request the honor of your presence as we celebrate this meaningful occasion${datePart}${venuePart}. Your presence would make the day truly memorable.`,
      romantic:`With joyful hearts and the people we love most, ${names} invite you to share in a beautiful celebration of love, laughter, and new beginnings${datePart}${venuePart}.`,
      modern:`We are celebrating, and we would love to have you there. Join ${names}${datePart}${venuePart} for good moments, great company, and a day worth remembering.`,
      concise:`Please join ${names} for a special celebration${datePart}${venuePart}. We would be honored to celebrate with you.`,
      business:`You are cordially invited to join us for a special event hosted by ${names}${datePart}${venuePart}. We look forward to welcoming you.`};return map[tone]||map.formal};
    $('#canvasGenerateCopy').onclick=()=>{fire('message',englishCopy($('#canvasSmartTone').value));toast('Invitation wording generated.','✦')};
    $('#canvasKhmerFormal').onclick=()=>{const names=value('namesKm')||value('names')||'យើងខ្ញុំ';const venue=value('venueKm')||value('venue');fire('messageKm',`យើងខ្ញុំ ${names} និងក្រុមគ្រួសារ សូមគោរពអញ្ជើញលោកអ្នក និងក្រុមគ្រួសារ ចូលរួមជាភ្ញៀវកិត្តិយសក្នុងពិធីដ៏មានអត្ថន័យរបស់យើង${venue?` ដែលប្រារព្ធនៅ ${venue}`:''}។ វត្តមានដ៏ថ្លៃថ្លារបស់លោកអ្នក គឺជាកិត្តិយស និងសេចក្តីរីករាយដ៏ធំធេងសម្រាប់យើងខ្ញុំ។`);toast('Khmer formal wording generated.','ក')};
    $('#canvasSuggestPalette').onclick=()=>{const tone=$('#canvasSmartTone').value,presets={formal:['#80512a','#fffaf2','#3a2d25','#9a6a2c'],romantic:['#a64f6a','#fff5f7','#422f36','#b7607a'],modern:['#6758c8','#f7f7ff','#26243a','#7e6ee5'],concise:['#27354a','#f8fafc','#202631','#566b88'],business:['#173a63','#f5f8fc','#172333','#315c8c']},p=presets[tone]||presets.formal;fire('accent',p[0]);fire('paletteBackground',p[1]);fire('paletteText',p[2]);fire('paletteHeading',p[3]);const preset=$('#palettePreset');if(preset){preset.value='custom';preset.dispatchEvent(new Event('change',{bubbles:true}))}toast('A matching palette was suggested.','◐')};
    $('#canvasAutoHero').onclick=()=>{const objects=$$('.object',stage);if(!objects.length)return toast('Add some hero elements first.');const texts=objects.filter(o=>o.dataset.objectType==='text'||o.dataset.objectType==='decoration'),images=objects.filter(o=>o.dataset.objectType==='image');texts.forEach((o,i)=>{const w=Math.min(84,Math.max(44,stagePercentFrame(o).w));o.style.width=`${w}%`;o.style.left=`${(50-w/2).toFixed(1)}%`;o.style.top=`${10+i*13}%`;if(i===0){o.dataset.fontSize=String(Math.max(42,Number(o.dataset.fontSize||48)));o.dataset.fontWeight='700'}});images.forEach((o,i)=>{if(i>1)return;o.style.left=i?'56%':'8%';o.style.top='48%';o.style.width='36%';o.style.height='300px';o.dataset.imageFrame=o.dataset.imageFrame||'white';o.dataset.shadowBlur='20'});applyItems(objects);saveNow();toast('Hero layout polished.','✦')};
  }
  const designPane=$('[data-inspector-pane="theme"]');
  if(designPane && !$('#canvasBackgroundStudio')){
    const section=document.createElement('section');section.className='final-advanced-inspector';section.id='canvasBackgroundStudio';
    section.innerHTML=`<div class="final-panel-title"><div><small>Canvas background</small><h2>Gradient & texture</h2></div><span class="final-beta">Design</span></div>
      <label>Background mode<select id="canvasBgMode"><option value="none">Use template / palette</option><option value="solid">Custom solid</option><option value="gradient">Gradient</option></select></label>
      <div class="final-two-col"><label>Start<input id="canvasBgStart" type="color" value="#fff8f2"></label><label>End<input id="canvasBgEnd" type="color" value="#ead8d0"></label></div>
      <label>Gradient angle <span id="canvasBgAngleValue">135°</span><input id="canvasBgAngle" type="range" min="0" max="360" value="135"></label>
      <label>Texture<select id="canvasBgTexture"><option value="none">None</option><option value="paper">Soft paper</option><option value="soft-grain">Fine grain</option><option value="dots">Dot pattern</option><option value="grid">Editorial grid</option></select></label>
      <label>Texture strength <span id="canvasBgTextureValue">18%</span><input id="canvasBgTextureOpacity" type="range" min="0" max="60" value="18"></label>
      <div class="canvas-bg-presets"><button type="button" data-bg-preset="ivory">Ivory paper</button><button type="button" data-bg-preset="rose">Rose glow</button><button type="button" data-bg-preset="midnight">Midnight</button><button type="button" data-bg-preset="emerald">Garden</button></div>`;
    const head=designPane.querySelector('.studio-inspector-heading');head?.after(section);
    const els={mode:$('#canvasBgMode'),start:$('#canvasBgStart'),end:$('#canvasBgEnd'),angle:$('#canvasBgAngle'),texture:$('#canvasBgTexture'),opacity:$('#canvasBgTextureOpacity')};
    function textureImages(texture,opacity){const a=Math.max(0,Math.min(60,Number(opacity||18)))/100,ink=`rgba(255,255,255,${(a*.45).toFixed(3)})`,shade=`rgba(0,0,0,${(a*.24).toFixed(3)})`;if(texture==='dots')return[`radial-gradient(circle at 1px 1px,${ink} 1px,transparent 1.4px)`,'18px 18px'];if(texture==='grid')return[`linear-gradient(${ink} 1px,transparent 1px),linear-gradient(90deg,${ink} 1px,transparent 1px)`,'28px 28px'];if(texture==='paper')return[`radial-gradient(circle at 20% 20%,${ink},transparent 30%),radial-gradient(circle at 78% 64%,${shade},transparent 34%),linear-gradient(115deg,transparent,${ink},transparent)`,'auto'];if(texture==='soft-grain')return[`radial-gradient(circle at 12% 18%,${ink} 0 1px,transparent 1.5px),radial-gradient(circle at 72% 68%,${shade} 0 1px,transparent 1.6px)`,'7px 7px,9px 9px'];return['','auto']}
    const render=()=>{const mode=els.mode.value,start=els.start.value,end=els.end.value,angle=Number(els.angle.value),texture=els.texture.value,opacity=Number(els.opacity.value);stage.dataset.backgroundMode=mode;stage.dataset.backgroundStart=start;stage.dataset.backgroundEnd=end;stage.dataset.backgroundAngle=String(angle);stage.dataset.backgroundTexture=texture;stage.dataset.backgroundTextureOpacity=String(opacity);$('#canvasBgAngleValue').textContent=`${angle}°`;$('#canvasBgTextureValue').textContent=`${opacity}%`;const images=[];if(mode==='gradient')images.push(`linear-gradient(${angle}deg,${start},${end})`);const [tex,size]=textureImages(texture,opacity);if(tex)images.push(tex);if(mode==='solid'){stage.style.backgroundColor=start;stage.style.backgroundImage=tex||'none';stage.style.backgroundSize=size}else if(mode==='gradient'){stage.style.backgroundColor=start;stage.style.backgroundImage=images.join(',');stage.style.backgroundSize=size}else{const preset=$('#palettePreset')?.value||'template';stage.style.backgroundColor=preset!=='template'?($('#paletteBackground')?.value||''):'';stage.style.backgroundImage=tex||'';stage.style.backgroundSize=size}saveNow()};
    const refresh=()=>{els.mode.value=stage.dataset.backgroundMode||'none';els.start.value=stage.dataset.backgroundStart||'#fff8f2';els.end.value=stage.dataset.backgroundEnd||'#ead8d0';els.angle.value=stage.dataset.backgroundAngle||'135';els.texture.value=stage.dataset.backgroundTexture||'none';els.opacity.value=stage.dataset.backgroundTextureOpacity||'18';$('#canvasBgAngleValue').textContent=`${els.angle.value}°`;$('#canvasBgTextureValue').textContent=`${els.opacity.value}%`};
    Object.values(els).forEach(el=>el.addEventListener(el.type==='range'||el.type==='color'?'input':'change',render));
    section.addEventListener('click',e=>{const preset=e.target.closest('[data-bg-preset]')?.dataset.bgPreset;if(!preset)return;const map={ivory:['solid','#f8f1e6','#f8f1e6',135,'paper',20],rose:['gradient','#fff4f4','#e9c3cd',135,'soft-grain',16],midnight:['gradient','#171321','#4c3868',145,'soft-grain',20],emerald:['gradient','#eff8f1','#b9d9c7',135,'paper',18]},v=map[preset];[els.mode.value,els.start.value,els.end.value,els.angle.value,els.texture.value,els.opacity.value]=['gradient',v[1],v[2],String(v[3]),v[4],String(v[5])];if(preset==='ivory')els.mode.value='solid';render();toast(`${e.target.textContent} background applied.`,'◐')});
    refresh();
  }

  if(objectPane && !$('#canvasPlusTextBox')){
    const textBox=document.createElement('section');textBox.className='final-advanced-inspector';textBox.id='canvasPlusTextBox';
    textBox.innerHTML=`<div class="final-panel-title"><div><small>Text box</small><h2>Flow & spacing</h2></div></div>
      <label>Vertical alignment<select id="canvasTextVertical"><option value="top">Top</option><option value="middle">Middle</option><option value="bottom">Bottom</option></select></label>
      <label>Inner padding <span id="canvasTextPaddingValue">8px</span><input id="canvasTextPadding" type="range" min="0" max="64" step="1" value="8"></label>
      <div class="canvas-pro-grid"><button type="button" data-text-fit="tight">Tight box</button><button type="button" data-text-fit="comfortable">Comfortable</button><button type="button" data-text-fit="wide">Wide title</button></div>`;
    objectPane.append(textBox);
    const textSelection=()=>activeObjects().filter(item=>['text','decoration'].includes(item.dataset.objectType));
    const syncTextBox=()=>{const item=textSelection()[0];textBox.hidden=!item;if(!item)return;$('#canvasTextVertical').value=item.dataset.textVerticalAlign||'middle';$('#canvasTextPadding').value=String(Number(item.dataset.textPadding??8));$('#canvasTextPaddingValue').textContent=`${$('#canvasTextPadding').value}px`;};
    $('#canvasTextVertical').onchange=e=>{const items=textSelection();items.forEach(item=>item.dataset.textVerticalAlign=e.target.value);applyItems(items);saveNow();};
    $('#canvasTextPadding').oninput=e=>{const items=textSelection();items.forEach(item=>item.dataset.textPadding=e.target.value);$('#canvasTextPaddingValue').textContent=`${e.target.value}px`;applyItems(items);saveNow();};
    textBox.addEventListener('click',e=>{const b=e.target.closest('[data-text-fit]');if(!b)return;const items=textSelection();if(!items.length)return;items.forEach(item=>{if(b.dataset.textFit==='tight'){item.dataset.textPadding='2';item.dataset.lineHeight='1.05'}else if(b.dataset.textFit==='comfortable'){item.dataset.textPadding='12';item.dataset.lineHeight='1.35'}else{item.dataset.textPadding='8';item.dataset.lineHeight='1.15';item.style.width='82%';item.style.left='9%'}});applyItems(items);saveNow();syncTextBox();});
    const textBoxObserver=new MutationObserver(syncTextBox);textBoxObserver.observe(stage,{subtree:true,attributes:true,attributeFilter:['class','data-text-vertical-align','data-text-padding']});document.addEventListener('pointerup',()=>setTimeout(syncTextBox,0),true);syncTextBox();
  }

  if(objectPane && !$('#canvasPlusTextPlacement')){
    const block=document.createElement('section'); block.className='final-advanced-inspector'; block.id='canvasPlusTextPlacement';
    block.innerHTML=`<div class="final-panel-title"><div><small>Placement</small><h2>Quick position</h2></div></div>
      <div class="canvas-pro-grid">
        <button type="button" data-place="tl">Top left</button>
        <button type="button" data-place="tc">Top center</button>
        <button type="button" data-place="tr">Top right</button>
        <button type="button" data-place="cl">Center left</button>
        <button type="button" data-place="cc">Center</button>
        <button type="button" data-place="cr">Center right</button>
        <button type="button" data-place="bl">Bottom left</button>
        <button type="button" data-place="bc">Bottom center</button>
        <button type="button" data-place="br">Bottom right</button>
      </div>`;
    objectPane.append(block);
    block.addEventListener('click',e=>{
      const btn=e.target.closest('[data-place]'); if(!btn) return;
      const items=activeObjects(); if(!items.length) return;
      const srect=stage.getBoundingClientRect();
      items.forEach(item=>{
        const rect=item.getBoundingClientRect();
        const w=rect.width/srect.width*100, h=rect.height/srect.height*100;
        const [v,hz]=[btn.dataset.place[0],btn.dataset.place[1]];
        let left=2, top=2;
        if(hz==='c') left=50-w/2; else if(hz==='r') left=98-w;
        if(v==='c') top=50-h/2; else if(v==='b') top=98-h;
        item.style.left=`${Math.max(0,Math.min(100-w,left))}%`;
        item.style.top=`${Math.max(0,Math.min(100-h,top))}%`;
      });
      applyItems(items); saveNow();
    });
  }
  if(objectPane && !$('#canvasPlusAiTools')){
    const block=document.createElement('section'); block.className='final-advanced-inspector'; block.id='canvasPlusAiTools';
    block.innerHTML=`<div class="final-panel-title"><div><small>AI tools</small><h2>Photo assist</h2></div><span class="final-beta">Beta</span></div>
      <div class="canvas-ai-grid">
        <button type="button" id="aiBgCut">Auto bg cut</button>
        <button type="button" id="aiBgRestore">Restore image</button>
        <button type="button" id="aiEnhance">Magic enhance</button>
        <button type="button" id="aiSoftPortrait">Portrait soften</button>
        <button type="button" id="aiReplaceImage">Replace image</button>
        <button type="button" id="aiResetPhoto">Reset edits</button>
        <button type="button" id="aiFlipX">Flip horizontal</button>
        <button type="button" id="aiFlipY">Flip vertical</button>
      </div>
      <label class="canvas-photo-hue">Hue <span id="aiHueValue">0°</span><input id="aiHue" type="range" min="-180" max="180" step="1" value="0"></label>
      <div class="canvas-ai-hint">Local smart helpers run in the browser. Background cut works best on simple backgrounds; all photo adjustments remain editable and are preserved in published invitations.</div>`;
    objectPane.append(block);

    const toast=(m)=>{ if(window.uiToast) window.uiToast(m,'✦'); else alert(m); };
    const selectedImage=()=>activeObjects()[0]?.querySelector?.('img')||null;
    const syncSelectedImageSrc=(src)=>{ const item=activeObjects()[0]; if(!item||!src) return; const img=item.querySelector('img'); if(img) img.src=src; item.dataset.src=src; try{ if(window.state?.objects?.[item.dataset.id]) window.state.objects[item.dataset.id].src=src; }catch{} applyItems([item]); saveNow(); };
    function averageCorners(data,w,h){
      const picks=[[0,0],[w-1,0],[0,h-1],[w-1,h-1],[Math.floor(w*.5),0],[0,Math.floor(h*.5)],[w-1,Math.floor(h*.5)],[Math.floor(w*.5),h-1]];
      const acc=[0,0,0]; let count=0;
      picks.forEach(([x,y])=>{const i=(y*w+x)*4; if(data[i+3]>16){acc[0]+=data[i]; acc[1]+=data[i+1]; acc[2]+=data[i+2]; count++;}});
      return acc.map(v=>count?Math.round(v/count):255);
    }
    function dist(i,data,bg){const dr=data[i]-bg[0], dg=data[i+1]-bg[1], db=data[i+2]-bg[2]; return Math.sqrt(dr*dr+dg*dg+db*db);}
    async function cutBackground(){
      const item=activeObjects()[0]; const img=selectedImage(); if(!item||!img) return toast('Select one image first.');
      try{ if(img.decode) await img.decode(); }catch{}
      const source=img.src; if(!item.dataset.originalSrc) item.dataset.originalSrc=source;
      const max=900; const scale=Math.min(1,max/Math.max(img.naturalWidth||img.width, img.naturalHeight||img.height));
      const w=Math.max(8,Math.round((img.naturalWidth||img.width)*scale)); const h=Math.max(8,Math.round((img.naturalHeight||img.height)*scale));
      const canvas=document.createElement('canvas'); canvas.width=w; canvas.height=h; const ctx=canvas.getContext('2d',{willReadFrequently:true});
      ctx.drawImage(img,0,0,w,h); const id=ctx.getImageData(0,0,w,h), data=id.data; const bg=averageCorners(data,w,h); const visited=new Uint8Array(w*h); const stack=[];
      for(let x=0;x<w;x++){ stack.push(x,0,x,h-1); }
      for(let y=1;y<h-1;y++){ stack.push(0,y,w-1,y); }
      const threshold=44;
      while(stack.length){
        const y=stack.pop(), x=stack.pop(); const pos=y*w+x; if(visited[pos]) continue; visited[pos]=1; const i=pos*4; if(data[i+3]<10 || dist(i,data,bg)<=threshold){ data[i+3]=0; if(x>0) stack.push(x-1,y); if(x<w-1) stack.push(x+1,y); if(y>0) stack.push(x,y-1); if(y<h-1) stack.push(x,y+1);} }
      for(let i=0;i<data.length;i+=4){ const d=dist(i,data,bg); if(data[i+3]>0 && d < threshold+16){ data[i+3]=Math.max(0,Math.min(255, Math.round((d-threshold)/16*255))); } }
      ctx.putImageData(id,0,0);
      const localResult=canvas.toDataURL('image/png');
      const token=localStorage.getItem('sovan-auth-token'),inviteId=localStorage.getItem('sovan-active-invite');
      if(token&&inviteId){
        try{
          const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png',.96));
          if(blob){
            const cutFile=new File([blob],'background-cut.png',{type:'image/png',lastModified:Date.now()});
            const result=window.EInviteUpload?.upload
              ? await window.EInviteUpload.upload(inviteId,cutFile,{token,name:'background-cut.png'})
              : await (async()=>{const response=await fetch(`/api/invitations/${encodeURIComponent(inviteId)}/assets/raw`,{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'image/png','X-File-Name':'background-cut.png'},body:blob});const payload=await response.json().catch(()=>({}));if(!response.ok)throw Error(payload.error||'The cutout could not be saved to the material library');return payload})();
            if(result?.url){syncSelectedImageSrc(result.url);toast('Background cut applied and stored.');return}
          }
        }catch{}
      }
      syncSelectedImageSrc(localResult);toast('Background cut applied locally.');
    }
    const selectedPhotoObject=()=>{const item=activeObjects()[0];return item?.dataset.objectType==='image'?item:null};
    const syncPhotoControls=()=>{const item=selectedPhotoObject();const hue=$('#aiHue');if(hue){hue.value=String(Number(item?.dataset.imageHue||0));$('#aiHueValue').textContent=`${hue.value}°`;block.classList.toggle('canvas-photo-disabled',!item)}};
    $('#aiBgCut').onclick=cutBackground;
    $('#aiBgRestore').onclick=()=>{ const item=selectedPhotoObject(); if(!item?.dataset.originalSrc) return toast('No original image is stored yet.'); syncSelectedImageSrc(item.dataset.originalSrc); toast('Original image restored.'); };
    $('#aiEnhance').onclick=()=>{ const item=selectedPhotoObject(); if(!item) return toast('Select an image first.'); item.dataset.imageBrightness='106'; item.dataset.imageContrast='114'; item.dataset.imageSaturation='114'; item.dataset.imageSepia='6'; item.dataset.imageBlur='0'; applyItems([item]); saveNow(); toast('Magic enhance applied.'); };
    $('#aiSoftPortrait').onclick=()=>{ const item=selectedPhotoObject(); if(!item) return toast('Select an image first.'); item.dataset.imageBrightness='104'; item.dataset.imageContrast='102'; item.dataset.imageSaturation='108'; item.dataset.imageBlur='0.4'; item.dataset.imageSepia='4'; applyItems([item]); saveNow(); toast('Portrait soften applied.'); };
    $('#aiFlipX').onclick=()=>{const item=selectedPhotoObject();if(!item)return toast('Select an image first.');item.dataset.imageFlipX=item.dataset.imageFlipX==='true'?'false':'true';applyItems([item]);saveNow();toast('Horizontal flip updated.');};
    $('#aiFlipY').onclick=()=>{const item=selectedPhotoObject();if(!item)return toast('Select an image first.');item.dataset.imageFlipY=item.dataset.imageFlipY==='true'?'false':'true';applyItems([item]);saveNow();toast('Vertical flip updated.');};
    $('#aiHue').oninput=e=>{const item=selectedPhotoObject();if(!item)return;item.dataset.imageHue=e.target.value;$('#aiHueValue').textContent=`${e.target.value}°`;applyItems([item]);saveNow();};
    $('#aiResetPhoto').onclick=()=>{const item=selectedPhotoObject();if(!item)return toast('Select an image first.');Object.assign(item.dataset,{imageBrightness:'100',imageContrast:'100',imageSaturation:'100',imageGrayscale:'0',imageSepia:'0',imageBlur:'0',imageHue:'0',imageFlipX:'false',imageFlipY:'false'});applyItems([item]);saveNow();syncPhotoControls();toast('Photo adjustments reset.');};
    $('#aiReplaceImage').onclick=()=>{const item=selectedPhotoObject();if(!item)return toast('Select an image first.');if(typeof openMaterialPicker!=='function')return toast('Material picker is unavailable.');openMaterialPicker('Replace selected image',(url,asset)=>{if(!item.dataset.originalSrc)item.dataset.originalSrc=item.querySelector('img')?.src||'';syncSelectedImageSrc(url);item.dataset.alt=asset?.name||item.dataset.alt||'Invitation image';const img=item.querySelector('img');if(img)img.alt=item.dataset.alt;saveNow();toast('Image replaced.');});};
    const photoObserver=new MutationObserver(syncPhotoControls);photoObserver.observe(stage,{subtree:true,attributes:true,attributeFilter:['class','data-image-hue']});document.addEventListener('pointerup',()=>setTimeout(syncPhotoControls,0),true);syncPhotoControls();
  }

  const elementsPane=$('[data-studio-pane="elements"]');
  if(elementsPane && !$('#canvasExtraElements')){
    const section=document.createElement('section');section.className='canvas-extra-elements';section.id='canvasExtraElements';
    const items=[['✧','Fine sparkle'],['✦','Four-point star'],['✺','Ceremonial sun'],['❦','Flourish'],['❧','Leaf flourish'],['✿','Flower'],['❀','Bloom'],['♡','Outline heart'],['♥','Heart'],['∞','Forever'],['♛','Crown'],['◇','Diamond'],['◈','Gem'],['— ✦ —','Divider'],['I · II · III','Roman divider'],['“','Quote'],['◯◯','Rings'],['☾','Moon'],['☼','Sun'],['✾','Lotus mark'],['⌁','Wave'],['×','Minimal cross'],['+','Minimal plus'],['•','Editorial dot']];
    section.innerHTML=`<div class="final-panel-title"><div><small>More assets</small><h2>Invitation symbols</h2></div><span class="final-beta">${items.length}</span></div><div class="canvas-extra-grid"></div>`;
    const grid=$('.canvas-extra-grid',section);
    const addGlyph=(glyph,name)=>{try{const id='symbol-'+Date.now()+'-'+Math.random().toString(36).slice(2,6),obj=createObject(id,'decoration'),content=obj.querySelector('.content');content.textContent=glyph;obj.dataset.fontSize=glyph.length>4?'30':'64';obj.dataset.color=$('#accent')?.value||'#9d4555';obj.style.left='34%';obj.style.top='38%';obj.style.width=glyph.length>4?'190px':'130px';obj.style.height='110px';stage.append(obj);clearSelection();setSelection([obj]);applyItems([obj]);saveNow();toast(`${name} added.`)}catch{}};
    items.forEach(([glyph,name])=>{const b=document.createElement('button');b.type='button';b.innerHTML=`<span>${glyph}</span><small>${name}</small>`;b.onclick=()=>addGlyph(glyph,name);grid.append(b)});
    elementsPane.append(section);
  }

  // Direct inline text editing: double-click a text object and type on the canvas.
  stage.addEventListener('dblclick',e=>{
    const object=e.target.closest('.text-object,.decoration-object');if(!object)return;const content=object.querySelector('.content');if(!content)return;
    e.preventDefault();e.stopPropagation();setSelectionIfNeeded(object);content.contentEditable='true';content.spellcheck=true;content.classList.add('canvas-inline-editing');content.focus();
    const range=document.createRange();range.selectNodeContents(content);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
    const finish=()=>{content.contentEditable='false';content.classList.remove('canvas-inline-editing');content.removeEventListener('blur',finish);saveNow();};
    content.addEventListener('blur',finish);
    content.addEventListener('keydown',function keyHandler(ev){if(ev.key==='Escape'){ev.preventDefault();content.blur();content.removeEventListener('keydown',keyHandler)}if((ev.metaKey||ev.ctrlKey)&&ev.key==='Enter'){ev.preventDefault();content.blur();content.removeEventListener('keydown',keyHandler)}});
  },true);

  const addTextObject=()=>{
    try{
      if(typeof createObject!=="function") return;
      const id="text-"+Date.now()+"-"+Math.random().toString(36).slice(2,7);
      const obj=createObject(id,"text");
      const content=obj.querySelector(".content"); if(content) content.textContent="New text";
      obj.style.left="16%"; obj.style.top="18%"; obj.style.width="52%"; obj.style.height="110px";
      obj.dataset.fontSize="34"; obj.dataset.color=window.state?.accent||"#9d4555";
      stage.append(obj);
      try{typeof clearSelection==="function"&&clearSelection(); typeof setSelection==="function"&&setSelection([obj]);}catch{}
      applyItems([obj]); saveNow();
    }catch{}
  };

  // Photoshop-like shortcuts
  document.addEventListener('keydown',e=>{
    const tag=document.activeElement?.tagName; const typing=/INPUT|TEXTAREA|SELECT/.test(tag)||document.activeElement?.isContentEditable;
    const key=e.key.toLowerCase(); const mod=e.ctrlKey||e.metaKey;
    if(typing) return;
    if(key==='v' && !mod && !e.altKey){ e.preventDefault(); document.body.dataset.activeTool='move'; toast('Move tool','V'); }
    if(mod && key==='a'){ e.preventDefault(); try{ typeof setSelection==='function'&&setSelection($$('.object',stage)); }catch{} return; }
    if(mod && key==='g' && !e.shiftKey){ e.preventDefault(); $('#groupObjects')?.click(); return; }
    if(mod && key==='g' && e.shiftKey){ e.preventDefault(); $('#ungroupObjects')?.click(); return; }
    if(mod && key==='t'){ e.preventDefault(); $('#canvasTransformX')?.focus(); $('#canvasPlusTransform')?.scrollIntoView({behavior:'smooth',block:'nearest'}); return; }
    if(key==='h' && !mod && !e.altKey){ e.preventDefault(); $('#panToggle')?.click(); return; }
    if(key==='t' && !mod && !e.altKey){ e.preventDefault(); try{ addTextObject(); }catch{} }
    if(key==='r' && !mod && !e.altKey){ e.preventDefault(); try{ typeof addDesignElement==='function' && addDesignElement('rectangle'); }catch{} }
    if(key==='o' && !mod && !e.altKey){ e.preventDefault(); try{ typeof addDesignElement==='function' && addDesignElement('circle'); }catch{} }
    if(key==='l' && !mod && !e.altKey){ e.preventDefault(); try{ typeof addDesignElement==='function' && addDesignElement('line'); }catch{} }
    if(mod && key==='j'){ e.preventDefault(); try{ typeof duplicateSelection==='function' && duplicateSelection(); }catch{} }
    if(mod && (e.key==='='||e.key==='+')){ e.preventDefault(); $('#zoomIn')?.click(); }
    if(mod && e.key==='-'){ e.preventDefault(); $('#zoomOut')?.click(); }
    if(mod && key==='0'){ e.preventDefault(); $('#fitCanvas')?.click(); }
    if(key==='[' && !mod){ e.preventDefault(); $('#sendBackward')?.click(); }
    if(key===']' && !mod){ e.preventDefault(); $('#bringForward')?.click(); }
  });

  const shortcutGrid=$('.ui-shortcut-grid');
  if(shortcutGrid && !shortcutGrid.querySelector('[data-canvas-plus-shortcuts]')){
    const extras=document.createElement('div');extras.dataset.canvasPlusShortcuts='1';extras.style.display='contents';extras.innerHTML=`
      <div class="ui-shortcut-row"><span>Move tool</span><kbd>V</kbd></div>
      <div class="ui-shortcut-row"><span>Text tool</span><kbd>T</kbd></div>
      <div class="ui-shortcut-row"><span>Hand tool</span><kbd>H</kbd></div>
      <div class="ui-shortcut-row"><span>Rectangle / Circle / Line</span><kbd>R / O / L</kbd></div>
      <div class="ui-shortcut-row"><span>Duplicate while dragging</span><kbd>Alt + Drag</kbd></div>
      <div class="ui-shortcut-row"><span>Duplicate selection</span><kbd>Ctrl / Cmd + J</kbd></div>
      <div class="ui-shortcut-row"><span>Select all objects</span><kbd>Ctrl / Cmd + A</kbd></div>
      <div class="ui-shortcut-row"><span>Group / Ungroup</span><kbd>Ctrl/Cmd + G / Shift + G</kbd></div>
      <div class="ui-shortcut-row"><span>Constrain move / resize</span><kbd>Shift + Drag</kbd></div>
      <div class="ui-shortcut-row"><span>Transform fields</span><kbd>Ctrl / Cmd + T</kbd></div>
      <div class="ui-shortcut-row"><span>Layer backward / forward</span><kbd>[ / ]</kbd></div>
      <div class="ui-shortcut-row"><span>Zoom / fit</span><kbd>Ctrl/Cmd + +/- / 0</kbd></div>`;shortcutGrid.append(extras);
  }

  // Alt-drag duplicate
  let dragState=null;
  stage.addEventListener('pointerdown',e=>{
    if(e.button!==0 || !e.altKey) return;
    const obj=e.target.closest('.object'); if(!obj || obj.dataset.locked==='true') return;
    if(e.target.closest('.resize-handle') || e.target.closest('.rotate-handle')) return;
    setSelectionIfNeeded(obj);
    e.preventDefault(); e.stopPropagation();
    try{ typeof duplicateSelection==='function' && duplicateSelection(); }catch{}
    const items=activeObjects(); if(!items.length) return;
    const srect=stage.getBoundingClientRect();
    dragState={pointerId:e.pointerId,startX:e.clientX,startY:e.clientY,srect,items,frames:new Map(items.map(item=>{const rect=item.getBoundingClientRect();return[item,{left:parseFloat(item.style.left)||((rect.left-srect.left)/srect.width*100),top:parseFloat(item.style.top)||((rect.top-srect.top)/srect.height*100),width:rect.width/srect.width*100,height:rect.height/srect.height*100}] }))};
    obj.setPointerCapture?.(e.pointerId);
  },true);
  const moveAltDrag=(e)=>{
    if(!dragState || dragState.pointerId!==e.pointerId) return;
    e.preventDefault();
    const dx=(e.clientX-dragState.startX)/dragState.srect.width*100, dy=(e.clientY-dragState.startY)/dragState.srect.height*100;
    dragState.items.forEach(item=>{const f=dragState.frames.get(item); item.style.left=`${Math.max(0,Math.min(100-f.width, f.left+dx))}%`; item.style.top=`${Math.max(0,Math.min(100-f.height, f.top+dy))}%`;});
    try{ typeof updateSelectionBounds==='function'&&updateSelectionBounds(); }catch{}
  };
  stage.addEventListener('pointermove',moveAltDrag,true);
  const endAltDrag=(e)=>{ if(!dragState || dragState.pointerId!==e.pointerId) return; saveNow(); dragState=null; };
  stage.addEventListener('pointerup',endAltDrag,true); stage.addEventListener('pointercancel',()=>{dragState=null},true);
}

wireAuthLayouts();
enhanceMaterialsPage();
editorEnhancements();
})();
