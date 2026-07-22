(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const editor=!!$('#stage')&&!!$('.studio-left-panel');

// ---------------------------------------------------------------------------
// Shared high-polish app behavior
// ---------------------------------------------------------------------------
document.documentElement.classList.add('final-ui-ready');

// Lightweight top navigation progress for internal page changes.
const progress=document.createElement('div'); progress.className='final-route-progress'; document.body.append(progress);
addEventListener('beforeunload',()=>progress.classList.add('active'));
document.addEventListener('click',e=>{
  const a=e.target.closest('a[href]'); if(!a||a.target==='_blank'||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
  try{const u=new URL(a.href,location.href);if(u.origin===location.origin&&u.href!==location.href)progress.classList.add('active')}catch{}
},true);

// Give major app surfaces a modern entrance without affecting guest invitations.
if(!document.body.classList.contains('guest')) requestAnimationFrame(()=>document.body.classList.add('final-page-entered'));

// Friendly empty states for tables/grids generated later.
const globalObserver=new MutationObserver(()=>{
  $$('.empty:not([data-final-empty])').forEach(el=>{el.dataset.finalEmpty='1';el.classList.add('final-empty-state')});
  $$('dialog:not([data-final-dialog])').forEach(el=>{el.dataset.finalDialog='1';el.classList.add('final-dialog')});
});
globalObserver.observe(document.body,{subtree:true,childList:true});

if(!editor)return;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const stage=$('#stage');
const objectPane=$('[data-inspector-pane="object"]');
const elementsPane=$('[data-studio-pane="elements"]');
const activeObjects=()=>$$('.object.selected,.object.multi-selected').filter(x=>x.isConnected);
const saveNow=()=>{try{typeof save==='function'&&save()}catch{}};
const applyNow=items=>{items.forEach(item=>{try{typeof applyObjectVisualStyle==='function'&&applyObjectVisualStyle(item)}catch{}});try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{};try{typeof refreshSelectionUI==='function'&&refreshSelectionUI()}catch{}};
const setData=(key,value,{apply=true}={})=>{const items=activeObjects();if(!items.length)return;items.forEach(item=>item.dataset[key]=String(value));if(apply)applyNow(items);saveNow();refreshAdvancedControls();refreshTimeline()};
const boolData=(key,value)=>setData(key,value?'true':'false');
const selectedType=()=>activeObjects()[0]?.dataset.objectType||'';
const safeText=node=>(node?.querySelector('.content')?.textContent||node?.dataset.alt||node?.dataset.objectType||'Object').trim().slice(0,38);
function toast(message,icon='✦'){
  if(typeof window.uiToast==='function')return window.uiToast(message,icon);
  let stack=$('.final-toast-stack');if(!stack){stack=document.createElement('div');stack.className='final-toast-stack';document.body.append(stack)}
  const t=document.createElement('div');t.className='final-toast';t.innerHTML=`<span>${icon}</span><b>${message}</b>`;stack.append(t);setTimeout(()=>{t.classList.add('out');setTimeout(()=>t.remove(),220)},1900)
}
function selectOnly(item){try{typeof clearSelection==='function'&&clearSelection();typeof setSelection==='function'&&setSelection([item])}catch{item.click()}setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0)}
function makeId(prefix='object'){return`${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`}

// ---------------------------------------------------------------------------
// Advanced effects inspector
// ---------------------------------------------------------------------------
const advanced=document.createElement('section'); advanced.className='final-advanced-inspector';
advanced.innerHTML=`
  <div class="final-panel-title"><div><small>Creative controls</small><h2>Effects & motion</h2></div><span class="final-beta">Advanced</span></div>
  <details open class="final-control-group" data-final-group="surface"><summary>Surface & blending</summary>
    <label class="final-toggle-row"><span>Object background</span><input id="finalBgEnabled" type="checkbox"></label>
    <div class="final-two-col"><label>Background<input id="finalBgColor" type="color" value="#ffffff"></label><label>Opacity <span id="finalBgOpacityValue">100%</span><input id="finalBgOpacity" type="range" min="0" max="100" value="100"></label></div>
    <label>Blend mode<select id="finalBlendMode"><option value="normal">Normal</option><option value="multiply">Multiply</option><option value="screen">Screen</option><option value="overlay">Overlay</option><option value="soft-light">Soft light</option><option value="darken">Darken</option><option value="lighten">Lighten</option></select></label>
  </details>
  <details class="final-control-group" data-final-group="shape"><summary>Gradient fill</summary>
    <label>Fill type<select id="finalFillMode"><option value="solid">Solid</option><option value="gradient">Gradient</option></select></label>
    <div class="final-two-col"><label>Start<input id="finalGradientStart" type="color" value="#d9a6ad"></label><label>End<input id="finalGradientEnd" type="color" value="#9d4555"></label></div>
    <label>Angle <span id="finalGradientAngleValue">135°</span><input id="finalGradientAngle" type="range" min="0" max="360" value="135"></label>
    <div class="final-gradient-preview" id="finalGradientPreview"></div>
  </details>
  <details class="final-control-group" data-final-group="text"><summary>Text effects</summary>
    <label>Transform<select id="finalTextTransform"><option value="none">As typed</option><option value="uppercase">UPPERCASE</option><option value="lowercase">lowercase</option><option value="capitalize">Capitalize</option></select></label>
    <label class="final-toggle-row"><span>Gradient text</span><input id="finalTextGradientEnabled" type="checkbox"></label>
    <div class="final-two-col"><label>Start<input id="finalTextGradientStart" type="color" value="#9d4555"></label><label>End<input id="finalTextGradientEnd" type="color" value="#b58a3a"></label></div>
    <label>Gradient angle <span id="finalTextGradientAngleValue">90°</span><input id="finalTextGradientAngle" type="range" min="0" max="360" value="90"></label>
    <div class="final-two-col"><label>Outline <span id="finalStrokeValue">0px</span><input id="finalStrokeWidth" type="range" min="0" max="8" step="0.5" value="0"></label><label>Outline color<input id="finalStrokeColor" type="color" value="#ffffff"></label></div>
    <div class="final-two-col"><label>Text shadow <span id="finalTextShadowValue">0px</span><input id="finalTextShadowBlur" type="range" min="0" max="40" value="0"></label><label>Shadow color<input id="finalTextShadowColor" type="color" value="#000000"></label></div>
    <div class="final-style-presets">
      <button type="button" data-final-text-style="luxury">Luxury Gold</button><button type="button" data-final-text-style="editorial">Editorial</button><button type="button" data-final-text-style="soft">Soft Glow</button><button type="button" data-final-text-style="minimal">Minimal</button>
    </div>
  </details>
  <details open class="final-control-group" data-final-group="motion"><summary>Motion timing</summary>
    <label>Animation delay <span id="finalDelayValue">0ms</span><input id="finalAnimationDelay" type="range" min="0" max="5000" step="50" value="0"></label>
    <div class="final-inline-actions"><button type="button" id="finalPreviewSelection">▶ Preview selected</button><button type="button" id="finalPreviewPage">▶ Preview page</button><button type="button" id="finalStagger">Stagger selected</button></div>
  </details>
  <details class="final-control-group" data-final-group="layout"><summary>Smart layout</summary>
    <div class="final-layout-grid"><button data-final-layout="horizontal">Horizontal stack</button><button data-final-layout="vertical">Vertical stack</button><button data-final-layout="grid">Smart grid</button><button data-final-layout="center">Center selection</button><button data-final-layout="equal-width">Equal width</button><button data-final-layout="equal-height">Equal height</button></div>
  </details>`;
if(objectPane)objectPane.append(advanced);

const controls={
 bgEnabled:$('#finalBgEnabled'),bgColor:$('#finalBgColor'),bgOpacity:$('#finalBgOpacity'),blend:$('#finalBlendMode'),fillMode:$('#finalFillMode'),gradientStart:$('#finalGradientStart'),gradientEnd:$('#finalGradientEnd'),gradientAngle:$('#finalGradientAngle'),textGradientEnabled:$('#finalTextGradientEnabled'),textGradientStart:$('#finalTextGradientStart'),textGradientEnd:$('#finalTextGradientEnd'),textGradientAngle:$('#finalTextGradientAngle'),strokeWidth:$('#finalStrokeWidth'),strokeColor:$('#finalStrokeColor'),textShadowBlur:$('#finalTextShadowBlur'),textShadowColor:$('#finalTextShadowColor'),textTransform:$('#finalTextTransform'),delay:$('#finalAnimationDelay')
};

function refreshAdvancedControls(){
  const item=activeObjects()[0],has=!!item,type=item?.dataset.objectType||'';
  advanced.classList.toggle('is-disabled',!has);
  $$('[data-final-group="shape"]',advanced).forEach(x=>x.hidden=type!=='shape');
  $$('[data-final-group="text"]',advanced).forEach(x=>x.hidden=!['text','decoration'].includes(type));
  if(!item)return;
  controls.bgEnabled.checked=item.dataset.backgroundEnabled==='true';controls.bgColor.value=item.dataset.backgroundColor||'#ffffff';controls.bgOpacity.value=item.dataset.backgroundOpacity??100;$('#finalBgOpacityValue').textContent=`${controls.bgOpacity.value}%`;controls.blend.value=item.dataset.blendMode||'normal';
  controls.fillMode.value=item.dataset.fillMode||'solid';controls.gradientStart.value=item.dataset.gradientStart||'#d9a6ad';controls.gradientEnd.value=item.dataset.gradientEnd||'#9d4555';controls.gradientAngle.value=item.dataset.gradientAngle||135;$('#finalGradientAngleValue').textContent=`${controls.gradientAngle.value}°`;$('#finalGradientPreview').style.background=`linear-gradient(${controls.gradientAngle.value}deg,${controls.gradientStart.value},${controls.gradientEnd.value})`;
  controls.textGradientEnabled.checked=item.dataset.textGradientEnabled==='true';controls.textGradientStart.value=item.dataset.textGradientStart||'#9d4555';controls.textGradientEnd.value=item.dataset.textGradientEnd||'#b58a3a';controls.textGradientAngle.value=item.dataset.textGradientAngle||90;$('#finalTextGradientAngleValue').textContent=`${controls.textGradientAngle.value}°`;controls.strokeWidth.value=item.dataset.textStrokeWidth||0;$('#finalStrokeValue').textContent=`${controls.strokeWidth.value}px`;controls.strokeColor.value=item.dataset.textStrokeColor||'#ffffff';controls.textShadowBlur.value=item.dataset.textShadowBlur||0;$('#finalTextShadowValue').textContent=`${controls.textShadowBlur.value}px`;controls.textShadowColor.value=item.dataset.textShadowColor||'#000000';controls.textTransform.value=item.dataset.textTransform||'none';controls.delay.value=item.dataset.animationDelay||0;$('#finalDelayValue').textContent=`${controls.delay.value}ms`;
}

controls.bgEnabled.onchange=e=>boolData('backgroundEnabled',e.target.checked);controls.bgColor.oninput=e=>setData('backgroundColor',e.target.value);controls.bgOpacity.oninput=e=>{$('#finalBgOpacityValue').textContent=`${e.target.value}%`;setData('backgroundOpacity',e.target.value)};controls.blend.onchange=e=>setData('blendMode',e.target.value);
controls.fillMode.onchange=e=>setData('fillMode',e.target.value);controls.gradientStart.oninput=e=>{setData('gradientStart',e.target.value);refreshAdvancedControls()};controls.gradientEnd.oninput=e=>{setData('gradientEnd',e.target.value);refreshAdvancedControls()};controls.gradientAngle.oninput=e=>{$('#finalGradientAngleValue').textContent=`${e.target.value}°`;setData('gradientAngle',e.target.value);refreshAdvancedControls()};
controls.textGradientEnabled.onchange=e=>boolData('textGradientEnabled',e.target.checked);controls.textGradientStart.oninput=e=>setData('textGradientStart',e.target.value);controls.textGradientEnd.oninput=e=>setData('textGradientEnd',e.target.value);controls.textGradientAngle.oninput=e=>{$('#finalTextGradientAngleValue').textContent=`${e.target.value}°`;setData('textGradientAngle',e.target.value)};controls.strokeWidth.oninput=e=>{$('#finalStrokeValue').textContent=`${e.target.value}px`;setData('textStrokeWidth',e.target.value)};controls.strokeColor.oninput=e=>setData('textStrokeColor',e.target.value);controls.textShadowBlur.oninput=e=>{$('#finalTextShadowValue').textContent=`${e.target.value}px`;setData('textShadowBlur',e.target.value)};controls.textShadowColor.oninput=e=>setData('textShadowColor',e.target.value);controls.textTransform.onchange=e=>setData('textTransform',e.target.value);controls.delay.oninput=e=>{$('#finalDelayValue').textContent=`${e.target.value}ms`;setData('animationDelay',e.target.value,{apply:false})};

const textStyles={
 luxury:{textGradientEnabled:'true',textGradientStart:'#7a5718',textGradientEnd:'#e9c86e',textGradientAngle:'90',textStrokeWidth:'0',textShadowBlur:'10',textShadowColor:'#5b3a0b',fontWeight:'700',letterSpacing:'1'},
 editorial:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'0',fontWeight:'400',fontStyle:'italic',letterSpacing:'0.5',textTransform:'none'},
 soft:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'18',textShadowColor:'#9d4555',fontWeight:'400',letterSpacing:'0'},
 minimal:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'0',fontWeight:'400',fontStyle:'normal',letterSpacing:'2',textTransform:'uppercase'}
};
$$('[data-final-text-style]').forEach(b=>b.onclick=()=>{const preset=textStyles[b.dataset.finalTextStyle];const items=activeObjects().filter(x=>['text','decoration'].includes(x.dataset.objectType));items.forEach(item=>Object.entries(preset).forEach(([k,v])=>item.dataset[k]=v));applyNow(items);saveNow();refreshAdvancedControls();toast(`${b.textContent.trim()} style applied`)});

// ---------------------------------------------------------------------------
// Animation preview and timeline
// ---------------------------------------------------------------------------
function keyframesFor(name){return({
 'fade-up':[{opacity:0,transform:'translateY(24px)'},{opacity:1,transform:'translateY(0)'}],
 'soft-zoom':[{opacity:0,transform:'scale(.9)'},{opacity:1,transform:'scale(1)'}],
 'slide-left':[{opacity:0,transform:'translateX(45px)'},{opacity:1,transform:'translateX(0)'}],
 'blur-in':[{opacity:0,filter:'blur(14px)'},{opacity:1,filter:'blur(0)'}],
 'bounce-in':[{opacity:0,transform:'scale(.72)'},{opacity:1,transform:'scale(1.05)',offset:.72},{opacity:1,transform:'scale(1)'}],
 'flip-in':[{opacity:0,transform:'rotateY(80deg)'},{opacity:1,transform:'rotateY(0)'}],
 'float':[{transform:'translateY(0)'},{transform:'translateY(-12px)'},{transform:'translateY(0)'}],
 none:[{opacity:1},{opacity:1}]
})[name]||[{opacity:0},{opacity:1}]}
function previewObjects(items){items.forEach(item=>{const duration=Math.max(300,Math.min(3000,Number(item.dataset.duration||900))),delay=Math.max(0,Math.min(5000,Number(item.dataset.animationDelay||0))),rotation=`rotate(${Number(item.dataset.rotation||0)}deg)`,frames=keyframesFor(item.dataset.animation||'fade-up').map(frame=>({...frame,transform:frame.transform?`${frame.transform} ${rotation}`:rotation}));item.animate(frames,{duration,delay,easing:'cubic-bezier(.2,.8,.2,1)',fill:'none',iterations:item.dataset.animation==='float'?2:1})})}
$('#finalPreviewSelection').onclick=()=>previewObjects(activeObjects());$('#finalPreviewPage').onclick=()=>previewObjects($$('.object'));$('#finalStagger').onclick=()=>{const items=activeObjects();if(items.length<2)return toast('Select two or more objects to stagger','!');items.sort((a,b)=>(parseFloat(a.style.top)||0)-(parseFloat(b.style.top)||0)||(parseFloat(a.style.left)||0)-(parseFloat(b.style.left)||0)).forEach((item,i)=>item.dataset.animationDelay=String(i*140));saveNow();refreshAdvancedControls();refreshTimeline();previewObjects(items);toast(`Staggered ${items.length} objects`)};

const timeline=document.createElement('section');timeline.className='final-timeline';timeline.innerHTML=`<div class="final-panel-title"><div><small>Sequence</small><h2>Motion timeline</h2></div><button id="finalTimelinePlay" type="button">▶ Play all</button></div><div id="finalTimelineRows"></div>`;if(objectPane)objectPane.append(timeline);
function refreshTimeline(){const host=$('#finalTimelineRows');if(!host)return;const items=$$('.object').sort((a,b)=>Number(a.style.zIndex||0)-Number(b.style.zIndex||0));host.innerHTML=items.length?'':'<p class="hint">Add objects to build a motion sequence.</p>';const maxEnd=Math.max(1000,...items.map(x=>Number(x.dataset.animationDelay||0)+Number(x.dataset.duration||900)));items.forEach(item=>{const row=document.createElement('button');row.type='button';row.className=`final-timeline-row${item.classList.contains('selected')||item.classList.contains('multi-selected')?' active':''}`;const delay=Number(item.dataset.animationDelay||0),duration=Number(item.dataset.duration||900);row.innerHTML=`<span class="final-timeline-icon">${item.dataset.objectType==='image'?'▣':item.dataset.objectType==='shape'?'□':'T'}</span><span class="final-timeline-name">${safeText(item)||'Object'}</span><span class="final-timeline-track"><i style="left:${delay/maxEnd*100}%;width:${Math.max(4,duration/maxEnd*100)}%"></i></span><small>${delay}ms</small>`;row.onclick=()=>selectOnly(item);host.append(row)})}
$('#finalTimelinePlay').onclick=()=>previewObjects($$('.object'));

// ---------------------------------------------------------------------------
// Smart layout helpers
// ---------------------------------------------------------------------------
function stagePercentFrame(item){return{left:parseFloat(item.style.left)||0,top:parseFloat(item.style.top)||0,width:item.getBoundingClientRect().width/stage.getBoundingClientRect().width*100,height:item.getBoundingClientRect().height/stage.getBoundingClientRect().height*100}}
function smartLayout(kind){const items=activeObjects().filter(x=>x.dataset.locked!=='true');if(!items.length)return toast('Select objects first','!');const frames=items.map(x=>({item:x,...stagePercentFrame(x)}));if(kind==='center'){const minL=Math.min(...frames.map(x=>x.left)),maxR=Math.max(...frames.map(x=>x.left+x.width)),minT=Math.min(...frames.map(x=>x.top)),maxB=Math.max(...frames.map(x=>x.top+x.height)),dx=50-(minL+maxR)/2,dy=50-(minT+maxB)/2;frames.forEach(x=>{x.item.style.left=`${x.left+dx}%`;x.item.style.top=`${x.top+dy}%`})}
 else if(kind==='horizontal'){const gap=3,total=frames.reduce((s,x)=>s+x.width,0)+gap*(frames.length-1),start=Math.max(4,(100-total)/2);let cur=start;frames.sort((a,b)=>a.left-b.left).forEach(x=>{x.item.style.left=`${cur}%`;x.item.style.top='45%';cur+=x.width+gap})}
 else if(kind==='vertical'){const gap=2,total=frames.reduce((s,x)=>s+x.height,0)+gap*(frames.length-1),start=Math.max(4,(100-total)/2);let cur=start;frames.sort((a,b)=>a.top-b.top).forEach(x=>{x.item.style.top=`${cur}%`;x.item.style.left=`${Math.max(4,(100-x.width)/2)}%`;cur+=x.height+gap})}
 else if(kind==='grid'){const cols=Math.ceil(Math.sqrt(frames.length)),gap=3,cell=(92-gap*(cols-1))/cols;frames.forEach((x,i)=>{const row=Math.floor(i/cols),col=i%cols;x.item.style.left=`${4+col*(cell+gap)}%`;x.item.style.top=`${8+row*22}%`;x.item.style.width=`${cell}%`})}
 else if(kind==='equal-width'){const w=Math.max(...frames.map(x=>x.width));frames.forEach(x=>x.item.style.width=`${w}%`)}
 else if(kind==='equal-height'){const h=Math.max(...frames.map(x=>x.height));frames.forEach(x=>x.item.style.height=`${h}%`)}
 try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{}saveNow();toast('Layout updated')}
$$('[data-final-layout]').forEach(b=>b.onclick=()=>smartLayout(b.dataset.finalLayout));

// ---------------------------------------------------------------------------
// Rich element library — specialized for invitations, not generic clipart.
// ---------------------------------------------------------------------------
const library=[
 {id:'flourish-1',name:'Classic flourish',cat:'Ornaments',glyph:'❦'},{id:'flourish-2',name:'Fine flourish',cat:'Ornaments',glyph:'❧'},{id:'sparkle-1',name:'Four-point sparkle',cat:'Ornaments',glyph:'✦'},{id:'sparkle-2',name:'Soft sparkle',cat:'Ornaments',glyph:'✧'},{id:'star-1',name:'Decorative star',cat:'Ornaments',glyph:'✶'},{id:'diamond-1',name:'Open diamond',cat:'Ornaments',glyph:'◇'},{id:'diamond-2',name:'Solid diamond',cat:'Ornaments',glyph:'◆'},
 {id:'heart-1',name:'Classic heart',cat:'Romance',glyph:'♥'},{id:'heart-2',name:'Outline heart',cat:'Romance',glyph:'♡'},{id:'rings',name:'Wedding rings',cat:'Romance',glyph:'◯◯'},{id:'infinity',name:'Forever mark',cat:'Romance',glyph:'∞'},{id:'love-spark',name:'Love sparkle',cat:'Romance',glyph:'♡ ✦ ♡'},
 {id:'leaf-1',name:'Botanical leaf',cat:'Botanical',glyph:'❧'},{id:'flower-1',name:'Flower mark',cat:'Botanical',glyph:'✿'},{id:'flower-2',name:'Elegant flower',cat:'Botanical',glyph:'❀'},{id:'petal',name:'Petal cluster',cat:'Botanical',glyph:'❋'},{id:'branch',name:'Leaf branch',cat:'Botanical',glyph:'☘'},
 {id:'crown',name:'Royal crown',cat:'Ceremonial',glyph:'♛'},{id:'royal',name:'Royal emblem',cat:'Ceremonial',glyph:'♔'},{id:'sun',name:'Ceremonial sun',cat:'Ceremonial',glyph:'☼'},{id:'blessing',name:'Blessing mark',cat:'Ceremonial',glyph:'✺'},{id:'lotus',name:'Lotus-inspired mark',cat:'Ceremonial',glyph:'✾'},
 {id:'quote',name:'Quote mark',cat:'Editorial',glyph:'“'},{id:'bullet',name:'Editorial bullet',cat:'Editorial',glyph:'•'},{id:'section',name:'Section divider',cat:'Editorial',glyph:'— ✦ —'},{id:'roman',name:'Roman divider',cat:'Editorial',glyph:'I · II · III'},
 {id:'rect',name:'Rectangle',cat:'Shapes',shape:'rectangle'},{id:'circle',name:'Circle',cat:'Shapes',shape:'circle'},{id:'line',name:'Line',cat:'Shapes',shape:'line'},{id:'panel',name:'Glass panel',cat:'Shapes',shape:'panel'},
 {id:'title-luxury',name:'Luxury title',cat:'Text styles',text:'YOUR CELEBRATION',preset:'luxury'},{id:'title-editorial',name:'Editorial title',cat:'Text styles',text:'A beautiful beginning',preset:'editorial'},{id:'khmer-title',name:'Khmer ceremonial title',cat:'Text styles',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍',preset:'khmer'},{id:'date-badge',name:'Date badge',cat:'Text styles',text:'27 · 12 · 2026',preset:'date'},
 {id:'khmer-diamond-row',name:'Khmer diamond row',cat:'Khmer motifs',glyph:'◇ ◆ ◇ ◆ ◇'},{id:'khmer-gold-divider',name:'Ceremonial divider',cat:'Khmer motifs',glyph:'✦ ◇ ✦'},{id:'khmer-lotus-row',name:'Lotus row',cat:'Khmer motifs',glyph:'✾  ✾  ✾'},{id:'khmer-blessing-row',name:'Blessing ornament',cat:'Khmer motifs',glyph:'✺ ✦ ✺'},{id:'khmer-temple-line',name:'Temple line',cat:'Khmer motifs',glyph:'⌂ ◇ ⌂'},{id:'khmer-royal-row',name:'Royal row',cat:'Khmer motifs',glyph:'♔  ◆  ♔'},
 {id:'confetti-1',name:'Confetti sparkle',cat:'Celebration',glyph:'✦ ✧ ✶ ✦'},{id:'party-stars',name:'Party stars',cat:'Celebration',glyph:'★ ☆ ★'},{id:'balloon-pair',name:'Balloon pair',cat:'Celebration',glyph:'◯  ◯'},{id:'gift-mark',name:'Gift mark',cat:'Celebration',glyph:'▣'},{id:'cake-mark',name:'Cake mark',cat:'Celebration',glyph:'♨'},{id:'music-notes',name:'Music notes',cat:'Celebration',glyph:'♪ ♫ ♪'},
 {id:'business-arrow',name:'Forward arrow',cat:'Business',glyph:'→'},{id:'business-grid',name:'Executive grid',cat:'Business',glyph:'□ □ □'},{id:'business-dots',name:'Modern dots',cat:'Business',glyph:'• • • •'},{id:'business-plus',name:'Modern plus',cat:'Business',glyph:'+  +  +'},{id:'business-chevron',name:'Chevron line',cat:'Business',glyph:'› › ›'},{id:'business-rule',name:'Executive rule',cat:'Business',glyph:'━━━'},
 {id:'corner-top-left',name:'Corner flourish',cat:'Borders',glyph:'⌜❦'},{id:'corner-top-right',name:'Reverse corner',cat:'Borders',glyph:'❦⌝'},{id:'thin-rule',name:'Thin divider',cat:'Borders',glyph:'────────'},{id:'diamond-rule',name:'Diamond divider',cat:'Borders',glyph:'── ◇ ──'},{id:'spark-rule',name:'Spark divider',cat:'Borders',glyph:'── ✦ ──'},{id:'dot-rule',name:'Dotted divider',cat:'Borders',glyph:'· · · · · ·'},
 {id:'leaf-pair',name:'Leaf pair',cat:'Botanical',glyph:'❧  ❧'},{id:'flower-row',name:'Flower row',cat:'Botanical',glyph:'❀ ✿ ❀'},{id:'garden-spark',name:'Garden sparkle',cat:'Botanical',glyph:'❧ ✦ ❧'},{id:'clover-row',name:'Clover row',cat:'Botanical',glyph:'☘ ☘ ☘'},{id:'small-bloom',name:'Small bloom',cat:'Botanical',glyph:'✽'},{id:'floral-divider',name:'Floral divider',cat:'Botanical',glyph:'❀ ─ ❀'},
 {id:'love-divider',name:'Heart divider',cat:'Romance',glyph:'── ♡ ──'},{id:'heart-cluster',name:'Heart cluster',cat:'Romance',glyph:'♡ ♥ ♡'},{id:'promise-mark',name:'Promise mark',cat:'Romance',glyph:'∞ ♡'},{id:'ring-divider',name:'Ring divider',cat:'Romance',glyph:'─ ◯◯ ─'},{id:'love-quote',name:'Love quote',cat:'Text styles',text:'A lifetime begins here',preset:'editorial'},{id:'thank-you',name:'Thank-you title',cat:'Text styles',text:'WITH LOVE & GRATITUDE',preset:'luxury'},
 {id:'circle-outline',name:'Circle outline',cat:'Shapes',shape:'circle'},{id:'soft-panel',name:'Soft panel',cat:'Shapes',shape:'panel'},{id:'wide-line',name:'Wide line',cat:'Shapes',shape:'line'},{id:'square-card',name:'Square card',cat:'Shapes',shape:'rectangle'}
];
const librarySection=document.createElement('section');librarySection.className='final-element-library';librarySection.innerHTML=`<div class="final-panel-title"><div><small>Invitation library</small><h2>Design elements</h2></div><span class="final-library-count"></span></div><div class="final-library-search"><span>⌕</span><input type="search" placeholder="Search ornaments, flowers, text…"></div><div class="final-library-cats"></div><div class="final-library-grid"></div>`;
if(elementsPane)elementsPane.insertBefore(librarySection,elementsPane.querySelector('.studio-pane-heading')?.nextSibling||elementsPane.firstChild);
let libraryCat='All',libraryQuery='';const favKey='einvite-element-favorites-v1',recentKey='einvite-element-recent-v1';let favorites=new Set(JSON.parse(localStorage.getItem(favKey)||'[]')),recent=JSON.parse(localStorage.getItem(recentKey)||'[]');
const cats=['All','Favorites','Recent',...new Set(library.map(x=>x.cat))];
function addCustomElement(item,drop){if(item.shape){if(typeof addDesignElement==='function')addDesignElement(item.shape);return}
 const type='decoration',obj=typeof createObject==='function'?createObject(makeId('library'),type):null;if(!obj)return;const content=obj.querySelector('.content');content.textContent=item.text||item.glyph||'✦';obj.dataset.color=(window.state?.accent||$('#accent')?.value||'#9d4555');obj.dataset.fontSize=item.text?'34':'64';obj.style.width=item.text?'76%':'150px';obj.style.height=item.text?'110px':'120px';obj.style.left=drop?`${drop.x}%`:(item.text?'12%':'32%');obj.style.top=drop?`${drop.y}%`:'38%';if(item.preset==='luxury'){obj.dataset.textGradientEnabled='true';obj.dataset.textGradientStart='#7a5718';obj.dataset.textGradientEnd='#e9c86e';obj.dataset.fontWeight='700';obj.dataset.letterSpacing='2'}if(item.preset==='editorial'){obj.dataset.fontStyle='italic';obj.dataset.font='Georgia,serif';obj.dataset.fontSize='38'}if(item.preset==='khmer'){obj.dataset.font="'Khmer OS Muol Light','Noto Serif Khmer',serif";obj.dataset.fontSize='34';obj.dataset.color='#a87616'}if(item.preset==='date'){obj.dataset.letterSpacing='4';obj.dataset.fontSize='26';obj.dataset.backgroundEnabled='true';obj.dataset.backgroundColor='#ffffff';obj.dataset.backgroundOpacity='78';obj.dataset.borderRadius='28'}applyObjectVisualStyle(obj);stage.append(obj);clearSelection();setSelection([obj]);saveNow();
 recent=[item.id,...recent.filter(x=>x!==item.id)].slice(0,10);localStorage.setItem(recentKey,JSON.stringify(recent));renderLibrary();toast(`${item.name} added`)}
function filteredLibrary(){return library.filter(x=>{if(libraryCat==='Favorites'&&!favorites.has(x.id))return false;if(libraryCat==='Recent'&&!recent.includes(x.id))return false;if(!['All','Favorites','Recent'].includes(libraryCat)&&x.cat!==libraryCat)return false;return!libraryQuery||`${x.name} ${x.cat}`.toLowerCase().includes(libraryQuery)})}
function renderLibrary(){const catHost=$('.final-library-cats',librarySection),grid=$('.final-library-grid',librarySection);catHost.innerHTML=cats.map(c=>`<button type="button" class="${c===libraryCat?'active':''}" data-cat="${c}">${c}</button>`).join('');catHost.querySelectorAll('button').forEach(b=>b.onclick=()=>{libraryCat=b.dataset.cat;renderLibrary()});const items=filteredLibrary();$('.final-library-count',librarySection).textContent=`${items.length} items`;grid.innerHTML='';items.forEach(item=>{const card=document.createElement('article');card.className='final-element-card';card.draggable=true;card.innerHTML=`<button type="button" class="final-fav ${favorites.has(item.id)?'active':''}" aria-label="Favorite">★</button><div class="final-element-preview">${item.shape?`<i class="shape-${item.shape}"></i>`:`<span>${item.text||item.glyph}</span>`}</div><strong>${item.name}</strong><small>${item.cat}</small>`;card.onclick=e=>{if(e.target.closest('.final-fav'))return;addCustomElement(item)};card.querySelector('.final-fav').onclick=e=>{e.stopPropagation();favorites.has(item.id)?favorites.delete(item.id):favorites.add(item.id);localStorage.setItem(favKey,JSON.stringify([...favorites]));renderLibrary()};card.ondragstart=e=>{e.dataTransfer.setData('application/x-einvite-library-item',item.id);e.dataTransfer.effectAllowed='copy'};grid.append(card)})}
$('.final-library-search input',librarySection).oninput=e=>{libraryQuery=e.target.value.trim().toLowerCase();renderLibrary()};renderLibrary();
stage.addEventListener('dragover',e=>{if(Array.from(e.dataTransfer.types||[]).includes('application/x-einvite-library-item')){e.preventDefault();stage.classList.add('final-library-drop')}});stage.addEventListener('dragleave',()=>stage.classList.remove('final-library-drop'));stage.addEventListener('drop',e=>{const id=e.dataTransfer.getData('application/x-einvite-library-item');if(!id)return;e.preventDefault();stage.classList.remove('final-library-drop');const r=stage.getBoundingClientRect(),item=library.find(x=>x.id===id);if(item)addCustomElement(item,{x:Math.max(0,Math.min(85,(e.clientX-r.left)/r.width*100)),y:Math.max(0,Math.min(85,(e.clientY-r.top)/r.height*100))})});

// ---------------------------------------------------------------------------
// Selection syncing
// ---------------------------------------------------------------------------
const observer=new MutationObserver(()=>{refreshAdvancedControls();refreshTimeline()});observer.observe(stage,{subtree:true,childList:true,attributes:true,attributeFilter:['class','data-animation-delay','data-fill-mode','data-text-gradient-enabled']});
document.addEventListener('pointerup',()=>setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0),true);document.addEventListener('keyup',()=>setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0),true);
refreshAdvancedControls();refreshTimeline();

// ---------------------------------------------------------------------------
// Mini onboarding / review tour
// ---------------------------------------------------------------------------
const tour=document.createElement('dialog');tour.className='final-tour';tour.innerHTML=`<form method="dialog"><button class="final-tour-close" aria-label="Close">×</button></form><div class="final-tour-art">✦</div><p class="invite-kicker">Creation Studio</p><h1>Design the invitation. Run the event.</h1><p>This workspace combines free-form visual creation with pages, animation, guest RSVP, publishing, Khmer dates and event operations.</p><div class="final-tour-grid"><article><b>1</b><strong>Create</strong><span>Drag elements, upload media and style every object.</span></article><article><b>2</b><strong>Build pages</strong><span>Mix free-form artboards with functional event sections.</span></article><article><b>3</b><strong>Animate</strong><span>Sequence motion with delay, duration and stagger controls.</span></article><article><b>4</b><strong>Publish</strong><span>Run the Design Check, publish a snapshot and manage guests.</span></article></div><div class="final-tour-actions"><button type="button" id="finalTourExplore">Explore studio</button><button type="button" id="finalTourDismiss" class="primary">Start creating</button></div>`;document.body.append(tour);
const tourKey='einvite-final-tour-seen-v1';function closeTour(){tour.close();localStorage.setItem(tourKey,'1')}$('#finalTourDismiss').onclick=closeTour;$('#finalTourExplore').onclick=()=>{closeTour();document.querySelector('[data-studio-tab="elements"]')?.click();setTimeout(()=>$('.final-element-library')?.scrollIntoView({behavior:'smooth'}),100)};
if(!localStorage.getItem(tourKey))setTimeout(()=>tour.showModal(),650);

// Add a tour button near shortcut help/status bar.
const status=$('.studio-statusbar>div:last-child');if(status){const b=document.createElement('button');b.type='button';b.className='final-tour-trigger';b.textContent='✦ Tour';b.onclick=()=>tour.showModal();status.prepend(b)}

// Keyboard: A opens elements library, Shift+P previews page motion.
document.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;if(e.key.toLowerCase()==='a'&&!e.ctrlKey&&!e.metaKey&&!e.altKey){document.querySelector('[data-studio-tab="elements"]')?.click();setTimeout(()=>$('.final-library-search input')?.focus(),0)}if(e.shiftKey&&e.key.toLowerCase()==='p'){e.preventDefault();previewObjects($$('.object'))}});

})();
