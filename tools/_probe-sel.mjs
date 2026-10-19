import {createRequire} from 'node:module';
import {BASE_URL} from './lib/repo.mjs';
const require = createRequire(new URL('./playwright-check/package.json', import.meta.url));
const {chromium} = require('playwright');
const browser = await chromium.launch(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {});
const page = await browser.newPage({viewport:{width:1366,height:900}});
const account = await page.request.post(`${BASE_URL}/api/auth/register`, {data:{
  email:`pd-probe-${Date.now()}@example.com`, password:'Motion-test-password-123!'}});
if (!account.ok()) throw Error(`Register: ${account.status()}`);
const objects = {};
for (let i=0;i<30;i++) objects[`motion-${i}`] = {
  type:i===0?'image':'shape', shapeKind:'rectangle', fillColor:'#3E7C6B',
  src:i===0?`data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="3000" height="2400"><rect width="3000" height="2400" fill="#3B6FB6"/></svg>')}`:'',
  left:`${8+(i%5)*17}%`, top:`${8+Math.floor(i/5)*13}%`, width:'12%', height:'55px',
  imagePositionX:50, imagePositionY:50, imageFit:'cover', zIndex:i+1, visible:true, locked:false, showInHero:true};
const response = await page.request.post(`${BASE_URL}/api/invitations`, {data:{
  slug:`pd-probe-${Date.now()}`, document:{eventType:'Wedding',fields:{names:'PD'},objects,designPages:[],sectionOrder:['schedule','venue','rsvp'],settings:{rsvpEnabled:true}}}});
if (!response.ok()) throw Error(`Invitation: ${response.status()}`);
const invite = await response.json();
await page.addInitScript(id=>localStorage.setItem('sovan-active-invite', String(id)), invite.id);
await page.goto(`${BASE_URL}/index.html?_perfdebug=1`, {waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>document.documentElement.dataset.editorReady==='true');
const dismiss=page.locator('#finalTourDismiss');
if(await dismiss.count() && await dismiss.isVisible())await dismiss.click();
await page.waitForFunction(()=>!!window.EInviteEditorCore && !!window.EInviteDirectManipulation && !!window.EInviteMotion);
await page.evaluate(async()=>{EInviteToolController.setTool('select',{announce:false});await new Promise(r=>setTimeout(r,300));EInviteCanvasViewController.fit();await new Promise(r=>setTimeout(r,450));});

const timeIt = (label, fn) => page.evaluate(fn, label);
for (let k=0;k<2;k++){
  const r = await page.evaluate(()=>{
    const out={};
    const t=(n,f)=>{const a=performance.now();f();out[n]=+(performance.now()-a).toFixed(1)};
    EInviteEditorBridge.select([]);
    t('selectEmptyToOne',()=>EInviteEditorBridge.select(['motion-6']));
    EInviteEditorBridge.select([]);
    t('selectEmptyToOneAgain',()=>EInviteEditorBridge.select(['motion-6']));
    EInviteEditorBridge.select([]);
    t('propsToggleOnly',()=>{const p=document.querySelector('#properties'),n=document.querySelector('#noSelection');n.hidden=true;p.hidden=false});
    t('forceLayout',()=>document.body.offsetHeight);
    EInviteEditorBridge.select([]);
    t('clearSel',()=>EInviteEditorBridge.select([]));
    return out;
  });
  console.log(JSON.stringify(r));
}
await browser.close();
