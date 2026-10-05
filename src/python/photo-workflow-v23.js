(()=>{
'use strict';
const VERSION='23.5.3';
if(window.EInvitePhotoWorkflow?.version===VERSION)return;
const registry=window.EInviteCommandRegistry,bridge=window.EInviteEditorBridge,stage=document.querySelector('#stage');
if(!registry||!bridge||!stage)return;
if(!document.querySelector('link[data-v23-photo-workflow]')){const link=document.createElement('link');link.rel='stylesheet';link.href='photo-workflow-v23.css';link.dataset.v23PhotoWorkflow='1';document.head.append(link)}
const $=(selector,root=document)=>root.querySelector(selector),$$=(selector,root=document)=>[...root.querySelectorAll(selector)];
const clone=value=>{try{return structuredClone(value)}catch{return JSON.parse(JSON.stringify(value))}};
const clamp=(value,min,max,fallback)=>{const number=Number(value);return Math.max(min,Math.min(max,Number.isFinite(number)?number:fallback))};
const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const originalOpen=window.openEInvitePhotoEditor;
const cleanup=[],unregister=[];
let dialog=null,session=null,lookClipboard=null,destroyed=false;
const feedback=window.EInviteFeedback||Object.freeze({toast:(message,tone='info')=>{window.uiToast?.(message,tone==='error'?'!':'✓');return true}});
const NUMBER_FIELDS=Object.freeze({
 imageBrightness:[20,200,100],imageContrast:[20,200,100],imageSaturation:[0,250,100],imageVibrance:[-100,100,0],imageTemperature:[-100,100,0],imageGamma:[.25,3,1],imageCurveShadows:[-100,100,0],imageCurveHighlights:[-100,100,0],imageGrayscale:[0,100,0],imageSepia:[0,100,0],imageBlur:[0,20,0],imageHue:[-180,180,0],imageSharpen:[0,100,0],imageLevelsBlack:[0,80,0],imageLevelsWhite:[20,100,100],imagePerspectiveX:[-60,60,0],imagePerspectiveY:[-60,60,0],imageWarpX:[-30,30,0],imageWarpY:[-30,30,0],imageMaskFeather:[0,50,0],imageGradientMask:[0,100,0],imagePositionX:[0,100,50],imagePositionY:[0,100,50]
});
const STRING_FIELDS=Object.freeze({imageFit:['cover','contain'],imageMask:['none','circle','arch','diamond','hexagon','blob'],imageFrame:['none','white','gold','dark']});
const BOOLEAN_FIELDS=Object.freeze(['imageFlipX','imageFlipY']);
const ADJUSTMENT_FIELDS=Object.freeze(['imageBrightness','imageContrast','imageSaturation','imageVibrance','imageTemperature','imageGamma','imageCurveShadows','imageCurveHighlights','imageGrayscale','imageSepia','imageBlur','imageHue','imageSharpen','imageLevelsBlack','imageLevelsWhite']);
const LOOK_FIELDS=Object.freeze([...ADJUSTMENT_FIELDS,'imageAdjustmentLayers','imageMaskFeather','imageGradientMask']);
const PHOTO_FIELDS=Object.freeze([...Object.keys(NUMBER_FIELDS),...Object.keys(STRING_FIELDS),...BOOLEAN_FIELDS,'imageAdjustmentLayers']);
const PRESETS=Object.freeze([
 {id:'original',label:'Original',description:'Neutral source look',values:{}},
 {id:'natural',label:'Natural',description:'Balanced and clean',values:{imageBrightness:103,imageContrast:104,imageSaturation:104,imageVibrance:8,imageTemperature:1}},
 {id:'portrait',label:'Portrait',description:'Gentle skin and detail',values:{imageBrightness:106,imageContrast:98,imageSaturation:103,imageVibrance:10,imageTemperature:5,imageCurveShadows:8,imageCurveHighlights:-5,imageBlur:.15}},
 {id:'celebration',label:'Celebration',description:'Colorful event energy',values:{imageBrightness:105,imageContrast:112,imageSaturation:122,imageVibrance:24,imageTemperature:4,imageCurveHighlights:6}},
 {id:'golden-hour',label:'Golden hour',description:'Warm evening glow',values:{imageBrightness:106,imageContrast:105,imageSaturation:112,imageVibrance:12,imageTemperature:28,imageSepia:8,imageCurveShadows:6}},
 {id:'candlelight',label:'Candlelight',description:'Warm ceremonial mood',values:{imageBrightness:101,imageContrast:108,imageSaturation:106,imageTemperature:38,imageSepia:14,imageCurveShadows:10,imageCurveHighlights:-8}},
 {id:'vivid',label:'Vivid',description:'Strong color and contrast',values:{imageBrightness:103,imageContrast:120,imageSaturation:138,imageVibrance:28,imageCurveHighlights:5}},
 {id:'film',label:'Soft film',description:'Muted editorial finish',values:{imageBrightness:105,imageContrast:94,imageSaturation:88,imageVibrance:-8,imageTemperature:10,imageSepia:7,imageCurveShadows:12,imageCurveHighlights:-10,imageGamma:1.06}},
 {id:'mono',label:'Monochrome',description:'Classic black and white',values:{imageBrightness:104,imageContrast:118,imageSaturation:100,imageGrayscale:100,imageCurveShadows:5,imageCurveHighlights:8}},
 {id:'soft',label:'Soft',description:'Light romantic finish',values:{imageBrightness:110,imageContrast:88,imageSaturation:94,imageVibrance:-4,imageTemperature:6,imageBlur:.35,imageCurveHighlights:-8}}
]);
const BASIC_CONTROLS=Object.freeze([
 ['imageBrightness','Brightness',20,200,1,'%'],['imageContrast','Contrast',20,200,1,'%'],['imageSaturation','Saturation',0,250,1,'%'],['imageVibrance','Vibrance',-100,100,1,''],['imageTemperature','Temperature',-100,100,1,''],['imageBlur','Blur',0,20,.1,'px']
]);
const ADVANCED_CONTROLS=Object.freeze([
 ['imageGamma','Gamma',.25,3,.05,''],['imageCurveShadows','Shadows',-100,100,1,''],['imageCurveHighlights','Highlights',-100,100,1,''],['imageLevelsBlack','Black point',0,80,1,''],['imageLevelsWhite','White point',20,100,1,'%'],['imageHue','Hue',-180,180,1,'°'],['imageSepia','Sepia',0,100,1,'%'],['imageGrayscale','Grayscale',0,100,1,'%']
]);
function on(target,type,handler,options){target?.addEventListener?.(type,handler,options);cleanup.push(()=>target?.removeEventListener?.(type,handler,options))}
function canvasMap(documentState,canvasId=bridge.getActiveCanvasId?.()||'hero'){
 if(canvasId==='hero')return documentState?.objects||{};
 const pageId=String(canvasId).replace(/^page:/,'');
 return(documentState?.designPages||[]).find(page=>String(page.id)===pageId)?.objects||{};
}
function selectedImageContext(){
 const canvasId=bridge.getActiveCanvasId?.()||'hero',map=canvasMap(bridge.getState?.()||{},canvasId),id=(bridge.getSelectedIds?.()||[]).find(candidate=>{const item=map[candidate];return item?.type==='image'||item?.objectType==='image'});
 if(!id)return null;
 const node=stage.querySelector(`.object[data-id="${CSS.escape(String(id))}"]`);
 return node?{id:String(id),canvasId,node,object:map[id]}:null;
}
function defaultValue(key){return NUMBER_FIELDS[key]?.[2]??(key==='imageAdjustmentLayers'?[]:key==='imageFit'?'cover':key==='imageMask'||key==='imageFrame'?'none':false)}
function normalizePhoto(source={}){
 const output={};
 for(const[key,[min,max,fallback]]of Object.entries(NUMBER_FIELDS))output[key]=clamp(source[key],min,max,fallback);
 for(const[key,allowed]of Object.entries(STRING_FIELDS)){const value=String(source[key]??defaultValue(key));output[key]=allowed.includes(value)?value:defaultValue(key)}
 for(const key of BOOLEAN_FIELDS)output[key]=source[key]===true||source[key]==='true';
 let layers=source.imageAdjustmentLayers;
 if(typeof layers==='string'){try{layers=JSON.parse(layers)}catch{layers=[]}}
 output.imageAdjustmentLayers=Array.isArray(layers)?clone(layers).slice(0,40):[];
 return output;
}
function neutralAdjustments(){const output={};for(const key of ADJUSTMENT_FIELDS)output[key]=defaultValue(key);output.imageAdjustmentLayers=[];return output}
function blendValue(key,target,intensity){const start=Number(defaultValue(key)),end=Number(target),ratio=clamp(intensity,0,100,100)/100;return start+(end-start)*ratio}
function presetById(id){return PRESETS.find(preset=>preset.id===id)||PRESETS[0]}
function applyPresetToDraft(id,intensity=100){
 if(!session)return;
 const preset=presetById(id),next={...session.draft,...neutralAdjustments()};
 for(const[key,value]of Object.entries(preset.values))if(NUMBER_FIELDS[key])next[key]=blendValue(key,value,intensity);
 session.draft=normalizePhoto(next);session.presetId=preset.id;session.intensity=clamp(intensity,0,100,100);renderSession();
}
function applyImageVisual(image,state){
 if(!image)return;
 image.style.objectFit=state.imageFit||'cover';image.style.objectPosition=`${state.imagePositionX}% ${state.imagePositionY}%`;
 image.style.filter=window.EInviteRenderer?.imageFilterStyle?.(state)||'';
 image.style.transform=window.EInviteRenderer?.imageTransformStyle?.(state)||`scaleX(${state.imageFlipX?-1:1}) scaleY(${state.imageFlipY?-1:1})`;
 const masks={none:'none',circle:'ellipse(50% 50% at 50% 50%)',arch:'inset(0 round 48% 48% 12% 12%)',diamond:'polygon(50% 0,100% 50%,50% 100%,0 50%)',hexagon:'polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%)',blob:'polygon(50% 0,78% 8%,96% 35%,91% 72%,66% 100%,31% 94%,6% 68%,0 32%,22% 7%)'};
 const frames={none:['0','transparent'],white:['8px','#ffffff'],gold:['8px','#c79b42'],dark:['8px','#201b1b']},frame=frames[state.imageFrame]||frames.none;
 image.style.clipPath=masks[state.imageMask]||'none';image.style.padding=frame[0];image.style.background=frame[1];image.style.boxSizing='border-box';
 image.style.removeProperty('mask-image');image.style.removeProperty('-webkit-mask-image');
 const maskStyle=window.EInviteRenderer?.imageMaskStyle?.(state)||'';
 for(const declaration of maskStyle.split(';')){const[key,...rest]=declaration.split(':');if(key&&rest.length)image.style.setProperty(key.trim(),rest.join(':').trim())}
}
function writeNodeState(node,state){
 if(!node)return;
 for(const key of PHOTO_FIELDS){const value=state[key];node.dataset[key]=key==='imageAdjustmentLayers'?JSON.stringify(value||[]):String(value)}
 const image=node.querySelector('img');applyImageVisual(image,state);
 try{window.applyObjectVisualStyle?.(node)}catch{}
 applyImageVisual(image,state);
}
function differenceCount(a,b){return PHOTO_FIELDS.reduce((count,key)=>JSON.stringify(a?.[key])===JSON.stringify(b?.[key])?count:count+1,0)}
function operationSummary(state){
 const neutral=normalizePhoto({}),labels={imageBrightness:'Brightness',imageContrast:'Contrast',imageSaturation:'Saturation',imageVibrance:'Vibrance',imageTemperature:'Temperature',imageGamma:'Gamma',imageCurveShadows:'Shadows',imageCurveHighlights:'Highlights',imageGrayscale:'Grayscale',imageSepia:'Sepia',imageBlur:'Blur',imageHue:'Hue',imageSharpen:'Sharpen',imageLevelsBlack:'Black point',imageLevelsWhite:'White point',imagePositionX:'Crop X',imagePositionY:'Crop Y'};
 const operations=[];
 for(const[key,label]of Object.entries(labels))if(Number(state[key])!==Number(neutral[key]))operations.push(`${label}: ${Number(state[key]).toFixed(Number(state[key])%1?2:0)}`);
 if(state.imageFit!=='cover')operations.push(`Fit: ${state.imageFit}`);if(state.imageMask!=='none')operations.push(`Mask: ${state.imageMask}`);if(state.imageFrame!=='none')operations.push(`Frame: ${state.imageFrame}`);if(state.imageFlipX)operations.push('Flip horizontal');if(state.imageFlipY)operations.push('Flip vertical');
 return operations.slice(0,40);
}
function sliderMarkup(definition){const[key,label,min,max,step,suffix]=definition;return`<label class="v23-photo-slider"><span>${esc(label)}</span><input type="range" data-photo-key="${key}" min="${min}" max="${max}" step="${step}"><output data-output-for="${key}" data-suffix="${esc(suffix)}"></output></label>`}
function ensureDialog(){
 if(dialog)return dialog;
 dialog=document.createElement('dialog');dialog.id='v23PhotoWorkflow';dialog.className='v23-photo-workflow v23-command-surface';dialog.innerHTML=`<div class="v23-photo-shell"><section class="v23-photo-preview"><header><span data-preview-label>Edited preview</span><button type="button" data-compare aria-pressed="false">Hold for before</button></header><div class="v23-photo-preview-frame"><img alt="Photo editing preview"></div><p data-preview-status aria-live="polite"></p></section><aside class="v23-photo-panel"><header><div><small>Non-destructive editor</small><h2>Edit photo</h2></div><button type="button" data-close aria-label="Close">×</button></header><div class="v23-photo-scroll"><section><div class="v23-photo-section-title"><strong>Looks</strong><label>Intensity <input type="range" data-preset-intensity min="0" max="100" step="1" value="100"><output data-intensity-output>100%</output></label></div><div class="v23-photo-presets" role="listbox" aria-label="Photo looks">${PRESETS.map(preset=>`<button type="button" data-photo-preset="${preset.id}" role="option" aria-selected="false"><span><img alt=""><b>${esc(preset.label)}</b><small>${esc(preset.description)}</small></span></button>`).join('')}</div></section><section><strong>Adjust</strong><div class="v23-photo-sliders">${BASIC_CONTROLS.map(sliderMarkup).join('')}</div></section><details><summary>Advanced adjustments</summary><div class="v23-photo-sliders">${ADVANCED_CONTROLS.map(sliderMarkup).join('')}</div></details><section><strong>Crop, mask, and frame</strong><div class="v23-photo-composition"><label>Fit<select data-photo-select="imageFit"><option value="cover">Crop to fill</option><option value="contain">Show full image</option></select></label><label>Mask<select data-photo-select="imageMask"><option value="none">None</option><option value="circle">Circle</option><option value="arch">Arch</option><option value="diamond">Diamond</option><option value="hexagon">Hexagon</option><option value="blob">Blob</option></select></label><label>Frame<select data-photo-select="imageFrame"><option value="none">None</option><option value="white">White</option><option value="gold">Gold</option><option value="dark">Dark</option></select></label>${sliderMarkup(['imagePositionX','Crop X',0,100,1,'%'])}${sliderMarkup(['imagePositionY','Crop Y',0,100,1,'%'])}${sliderMarkup(['imageMaskFeather','Mask feather',0,50,1,'%'])}${sliderMarkup(['imageGradientMask','Bottom fade',0,100,1,'%'])}</div><div class="v23-photo-tool-row"><button type="button" data-photo-action="flip-x">Flip horizontal</button><button type="button" data-photo-action="flip-y">Flip vertical</button><button type="button" data-photo-action="reset-composition">Reset crop/frame</button></div></section><details><summary>Perspective and warp</summary><div class="v23-photo-sliders">${sliderMarkup(['imagePerspectiveX','Perspective X',-60,60,1,'°'])}${sliderMarkup(['imagePerspectiveY','Perspective Y',-60,60,1,'°'])}${sliderMarkup(['imageWarpX','Warp X',-30,30,1,'°'])}${sliderMarkup(['imageWarpY','Warp Y',-30,30,1,'°'])}</div></details><section><strong>Reusable look</strong><div class="v23-photo-tool-row"><button type="button" data-photo-action="copy-look">Copy look</button><button type="button" data-photo-action="paste-look">Paste look</button><button type="button" data-photo-action="reset-adjustments">Reset adjustments</button></div></section></div><footer><span data-change-count>No pending changes</span><div><button type="button" data-close>Cancel</button><button type="button" class="primary" data-apply>Apply photo edits</button></div></footer></aside></div>`;
 document.body.append(dialog);
 dialog.querySelectorAll('[data-close]').forEach(button=>button.addEventListener('click',()=>{closeSession();dialog.close()}));
 dialog.addEventListener('cancel',event=>{event.preventDefault();closeSession();dialog.close()});
 dialog.addEventListener('input',handleInput);
 dialog.addEventListener('change',handleInput);
 dialog.addEventListener('click',handleClick);
 const compare=$('[data-compare]',dialog);compare.addEventListener('pointerdown',()=>showBefore(true));['pointerup','pointercancel','pointerleave'].forEach(type=>compare.addEventListener(type,()=>showBefore(false)));compare.addEventListener('keydown',event=>{if(event.key===' '||event.key==='Enter'){event.preventDefault();showBefore(true)}});compare.addEventListener('keyup',event=>{if(event.key===' '||event.key==='Enter'){event.preventDefault();showBefore(false)}});
 $('[data-apply]',dialog).addEventListener('click',commitSession);
 return dialog;
}
function showBefore(value){
 if(!session)return;session.comparing=!!value;const state=value?session.original:session.draft;writeNodeState(session.node,state);applyImageVisual($('.v23-photo-preview img',dialog),state);$('[data-compare]',dialog).setAttribute('aria-pressed',String(!!value));$('[data-preview-label]',dialog).textContent=value?'Before this edit':'Edited preview';
}
function handleInput(event){
 if(!session)return;
 const intensity=event.target.closest('[data-preset-intensity]');if(intensity){applyPresetToDraft(session.presetId==='custom'?'original':session.presetId,Number(intensity.value));return}
 const slider=event.target.closest('[data-photo-key]');if(slider){const[key,min,max]=[slider.dataset.photoKey,Number(slider.min),Number(slider.max)];session.draft[key]=clamp(slider.value,min,max,defaultValue(key));session.presetId='custom';renderSession();return}
 const select=event.target.closest('[data-photo-select]');if(select){session.draft[select.dataset.photoSelect]=select.value;session.presetId='custom';renderSession()}
}
function handleClick(event){
 if(!session)return;
 const preset=event.target.closest('[data-photo-preset]');if(preset){applyPresetToDraft(preset.dataset.photoPreset,100);return}
 const action=event.target.closest('[data-photo-action]')?.dataset.photoAction;if(!action)return;
 if(action==='flip-x')session.draft.imageFlipX=!session.draft.imageFlipX;
 else if(action==='flip-y')session.draft.imageFlipY=!session.draft.imageFlipY;
 else if(action==='reset-composition')Object.assign(session.draft,{imageFit:'cover',imagePositionX:50,imagePositionY:50,imageMask:'none',imageFrame:'none',imageFlipX:false,imageFlipY:false,imagePerspectiveX:0,imagePerspectiveY:0,imageWarpX:0,imageWarpY:0,imageMaskFeather:0,imageGradientMask:0});
 else if(action==='reset-adjustments')Object.assign(session.draft,neutralAdjustments());
 else if(action==='copy-look'){lookClipboard=copyLookData(session.draft);feedback.toast('Photo look copied');}
 else if(action==='paste-look'){if(!lookClipboard){feedback.toast('Copy a photo look first','error');return}Object.assign(session.draft,clone(lookClipboard));feedback.toast('Photo look previewed');}
 session.presetId='custom';renderSession();
}
function renderSession(){
 if(!session||!dialog)return;
 session.draft=normalizePhoto(session.draft);writeNodeState(session.node,session.draft);
 const source=session.source||session.node.querySelector('img')?.src||'',preview=$('.v23-photo-preview img',dialog);if(preview.src!==source)preview.src=source;applyImageVisual(preview,session.draft);
 for(const button of $$('[data-photo-preset]',dialog)){const preset=presetById(button.dataset.photoPreset),selected=button.dataset.photoPreset===session.presetId;button.setAttribute('aria-selected',String(selected));const image=$('img',button);if(image.src!==source)image.src=source;applyImageVisual(image,normalizePhoto({...session.original,...neutralAdjustments(),...preset.values,imageFit:'cover',imagePositionX:50,imagePositionY:50,imageMask:'none',imageFrame:'none',imageFlipX:false,imageFlipY:false,imageMaskFeather:0,imageGradientMask:0}))}
 for(const input of $$('[data-photo-key]',dialog)){const key=input.dataset.photoKey;input.value=String(session.draft[key]);const output=$(`[data-output-for="${CSS.escape(key)}"]`,input.closest('label')||dialog);if(output)output.textContent=`${Number(session.draft[key]).toFixed(Number(session.draft[key])%1?2:0)}${output.dataset.suffix||''}`}
 for(const select of $$('[data-photo-select]',dialog))select.value=session.draft[select.dataset.photoSelect];
 const intensity=$('[data-preset-intensity]',dialog);intensity.value=String(session.intensity);intensity.disabled=session.presetId==='custom';$('[data-intensity-output]',dialog).textContent=session.presetId==='custom'?'Custom':`${Math.round(session.intensity)}%`;
 const count=differenceCount(session.original,session.draft);$('[data-change-count]',dialog).textContent=count?`${count} pending change${count===1?'':'s'}`:'No pending changes';$('[data-preview-status]',dialog).textContent=session.presetId==='custom'?'Custom photo adjustments':`${presetById(session.presetId).label} look at ${Math.round(session.intensity)}%`;
 $('[data-photo-action="paste-look"]',dialog).disabled=!lookClipboard;
}
function copyLookData(source){const normalized=normalizePhoto(source),result={};for(const key of LOOK_FIELDS)result[key]=clone(normalized[key]);return result}
function applyLookToObject(target,look){if(!target)return false;const normalized=copyLookData(look);for(const key of LOOK_FIELDS)target[key]=clone(normalized[key]);target.imageEditOperations=operationSummary(normalizePhoto(target));return true}
function projectLookToNode(node,look){if(!node)return false;const base=normalizePhoto(node.dataset||{}),next={...base,...copyLookData(look)};writeNodeState(node,next);return true}
function commitSession(){
 if(!session)return false;
 const current=session,finalState=normalizePhoto(current.draft),changes=differenceCount(current.original,finalState);
 if(!changes){current.committed=true;session=null;dialog.close();return true}
 try{
  bridge.transact('Apply photo edits',documentState=>{const target=canvasMap(documentState,current.canvasId)[current.id];if(!target)throw Error('The edited image is no longer available.');for(const key of PHOTO_FIELDS)target[key]=clone(finalState[key]);target.imageEditOperations=operationSummary(finalState)},{capture:false});
  current.committed=true;session=null;bridge.select?.([current.id]);dialog.close();feedback.toast('Photo edits applied');return true;
 }catch(error){feedback.toast(error?.message||'Unable to apply photo edits','error');return false}
}
function closeSession(){
 const current=session;session=null;if(!current)return;
 if(!current.committed&&current.node?.isConnected)writeNodeState(current.node,current.original);
 current.opener?.focus?.();
}
function open(){
 const context=selectedImageContext();if(!context){feedback.toast('Select one image first','error');return false}
 ensureDialog();if(dialog.open){closeSession();dialog.close()}
 const original=normalizePhoto(context.object||context.node.dataset),source=context.object?.src||context.node.querySelector('img')?.src||'';
 session={...context,original,draft:clone(original),source,presetId:'custom',intensity:100,comparing:false,committed:false,opener:document.activeElement};
 renderSession();dialog.showModal();setTimeout(()=> $('[data-photo-preset]',dialog)?.focus(),0);return true;
}
function resetSelected(){
 const context=selectedImageContext();if(!context)return false;
 bridge.transact('Reset photo adjustments',documentState=>{const target=canvasMap(documentState,context.canvasId)[context.id];if(!target)return;Object.assign(target,neutralAdjustments());target.imageEditOperations=[]},{capture:false});feedback.toast('Photo adjustments reset');return true;
}
function copySelectedLook(){const context=selectedImageContext();if(!context)return false;lookClipboard=copyLookData(context.object);feedback.toast('Photo look copied');return true}
function pasteSelectedLook(){
 const context=selectedImageContext();if(!context||!lookClipboard)return false;
 bridge.transact('Paste photo look',documentState=>{const target=canvasMap(documentState,context.canvasId)[context.id];if(!target)return;applyLookToObject(target,lookClipboard)},{capture:false});feedback.toast('Photo look pasted');return true;
}
function registerCommands(){
 unregister.push(...registry.registerMany([
  {id:'image.editPhoto',title:'Edit selected photo',category:'Photo',keywords:['filter','crop','preset','adjust','image'],bindings:{standard:[],canva:[],photoshop:[]},enabled:()=>!!selectedImageContext(),run:open},
  {id:'image.copyLook',title:'Copy photo look',category:'Photo',keywords:['style','filter','adjustments'],bindings:{standard:[],canva:[],photoshop:[]},enabled:()=>!!selectedImageContext(),run:copySelectedLook},
  {id:'image.pasteLook',title:'Paste photo look',category:'Photo',keywords:['style','filter','adjustments'],bindings:{standard:[],canva:[],photoshop:[]},enabled:()=>!!selectedImageContext()&&!!lookClipboard,run:pasteSelectedLook},
  {id:'image.resetAdjustments',title:'Reset photo adjustments',category:'Photo',keywords:['original','clear','filter'],bindings:{standard:[],canva:[],photoshop:[]},enabled:()=>!!selectedImageContext(),run:resetSelected}
 ]));
}
function installEntryPoints(){
 window.openEInvitePhotoEditor=open;
 const button=$('#openPhotoEditor');if(button){button.onclick=null;button.dataset.commandId='image.editPhoto';button.title='Edit selected photo'}
 document.dispatchEvent(new CustomEvent('einvite:selection-changed',{detail:{source:'photo-workflow'}}));
}
function init(){if(destroyed)return;registerCommands();installEntryPoints();document.body.classList.add('photo-workflow-v23')}
window.EInvitePhotoWorkflow=Object.freeze({version:VERSION,open,resetSelected,copySelectedLook,pasteSelectedLook,normalizeLook:copyLookData,extractLook:copyLookData,applyLookToObject,projectLookToNode,get lookFields(){return[...LOOK_FIELDS]},get presets(){return clone(PRESETS)},get hasCopiedLook(){return!!lookClipboard}});
window.EInviteLifecycle?.add?.(()=>{destroyed=true;cleanup.splice(0).forEach(dispose=>{try{dispose()}catch{}});unregister.splice(0).forEach(dispose=>{try{dispose()}catch{}});if(session&&!session.committed&&session.node?.isConnected)writeNodeState(session.node,session.original);dialog?.remove();if(window.openEInvitePhotoEditor===open)window.openEInvitePhotoEditor=originalOpen;delete window.EInvitePhotoWorkflow});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
