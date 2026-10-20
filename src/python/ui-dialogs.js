(()=>{
'use strict';
const ensureStack=()=>{let stack=document.querySelector('.ei-toast-stack');if(!stack){stack=document.createElement('div');stack.className='ei-toast-stack';stack.setAttribute('aria-live','polite');document.body.append(stack)}return stack};
function toast(message,options={}){
  const text=String(message??'');if(!text)return;
  const stack=ensureStack(),item=document.createElement('div');item.className=`ei-toast ${options.type||''}`.trim();
  const icon=options.icon||(options.type==='error'?'!':options.type==='success'?'✓':'✦');
  item.innerHTML=`<span class="ei-toast-icon"></span><strong></strong><button type="button" aria-label="Dismiss">×</button>`;
  item.querySelector('.ei-toast-icon').textContent=icon;item.querySelector('strong').textContent=text;
  const close=()=>{if(item.classList.contains('out'))return;item.classList.add('out');setTimeout(()=>item.remove(),190)};item.querySelector('button').onclick=close;stack.append(item);setTimeout(close,Math.max(1500,Number(options.duration||3600)));return item
}
function buildDialog({title='Please confirm',message='',icon='✦',input=false,value='',multiline=false,confirmText='Continue',cancelText='Cancel',danger=false,selectOptions=null}={}){
  const dialog=document.createElement('dialog');dialog.className='ei-dialog';
  dialog.innerHTML=`<form method="dialog" class="ei-dialog-card"><div class="ei-dialog-head"><span class="ei-dialog-icon"></span><div><h2></h2><p class="ei-dialog-message"></p></div></div><div class="ei-dialog-input" hidden><label>Value</label></div><div class="ei-dialog-actions"><button type="button" data-cancel></button><button type="submit" value="confirm" data-confirm></button></div></form>`;
  dialog.querySelector('.ei-dialog-icon').textContent=icon;dialog.querySelector('h2').textContent=title;dialog.querySelector('.ei-dialog-message').textContent=message;dialog.querySelector('[data-cancel]').textContent=cancelText;const confirm=dialog.querySelector('[data-confirm]');confirm.textContent=confirmText;confirm.classList.add(danger?'ei-danger':'ei-primary');
  let field=null;if(input){const host=dialog.querySelector('.ei-dialog-input');host.hidden=false;if(selectOptions&&selectOptions.length){const wrap=document.createElement('label');wrap.textContent='Type';field=document.createElement('select');selectOptions.forEach(({value:v,label})=>{const o=document.createElement('option');o.value=v;o.textContent=label;field.append(o)});field.value=value;host.append(field)}else{field=document.createElement(multiline?'textarea':'input');field.value=value??'';field.autocomplete='off';host.append(field)}}
  document.body.append(dialog);return{dialog,field}
}
function uiConfirm(message,options={}){return new Promise(resolve=>{const{dialog}=buildDialog({title:options.title||'Confirm action',message,icon:options.icon||'?',confirmText:options.confirmText||'Confirm',cancelText:options.cancelText||'Cancel',danger:options.danger===true});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(false)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(false)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'));dialog.showModal();setTimeout(()=>dialog.querySelector('[data-confirm]')?.focus(),0)})}
function uiPrompt(message,defaultValue='',options={}){return new Promise(resolve=>{const{dialog,field}=buildDialog({title:options.title||'Enter a value',message,icon:options.icon||'✎',input:true,value:defaultValue,multiline:options.multiline===true,confirmText:options.confirmText||'Save',cancelText:options.cancelText||'Cancel',selectOptions:Array.isArray(options.selectOptions)?options.selectOptions:null});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(null)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(null)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'?field.value:null));dialog.showModal();setTimeout(()=>{field.focus();field.select?.()},0)})}
function uiAlert(message,options={}){toast(message,{...options,type:options.type||(/error|failed|invalid|could not|unable/i.test(String(message))?'error':options.type)});return Promise.resolve()}
window.uiToast=window.uiToast||toast;window.uiAlert=uiAlert;window.uiConfirm=uiConfirm;window.uiPrompt=uiPrompt;
window.alert=(message)=>{uiAlert(message)};
// Custom-units engine (owner decision, CANVA-UI §5, accepted 2026-10-20): the
// poster size prompts accept px (default), in, cm — plus inch/inches and ft —
// converting at 96 px per CSS inch (cm via 96/2.54). Shared by the editor
// custom canvas-size prompt (app.js) and the Template Studio custom poster
// size prompt (templates.js); lives here because both route bundles already
// load ui-dialogs.js before their consumer modules.
window.EInvitePosterUnits=Object.freeze({
 PX_PER:{in:96,cm:96/2.54,ft:1152},
 parse(value){
  const s=String(value||'').toLowerCase().replace(/×|,|\]/g,'x');
  const m=/(\d+(?:\.\d+)?)\s*(in|inch|inches|"|cm|centimeters?|ft|feet|')?\s*x\s*(\d+(?:\.\d+)?)\s*(in|inch|inches|"|cm|centimeters?|ft|feet|')?/.exec(s);
  if(!m)return null;
  // "24 x 36 in" — one trailing unit applies to BOTH sides; two units stay per-side.
  return {w:m[1],wu:m[2]||m[4],h:m[3],hu:m[4]||m[2]};
 },
 toPx(number,unit){
  const per=this.PX_PER[String(unit||'').replace(/inches|"/g,'in').replace(/centimeters?/,'cm').replace(/feet|'/g,'ft')];
  return per?number*per:number // bare numbers stay px
 }
});
})();
