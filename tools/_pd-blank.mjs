import {createRequire} from 'node:module';
const require = createRequire(new URL('./playwright-check/package.json', import.meta.url));
const {chromium} = require('playwright');
const extra = (process.env.PD_EXTRA_ARGS||'').split(';').filter(Boolean);
const browser = await chromium.launch({...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}), ...(extra.length?{args:extra}:{})});
const page = await browser.newPage({viewport:{width:1366,height:900}});
await page.goto('about:blank');
const bench = () => page.evaluate(()=>{const t0=performance.now();let x=0;const M=7**8;for(let i=0;i<1e7;i++)x=(x+i*3)%M;const t1=performance.now();return Math.round((t1-t0)*10)/10});
if(process.env.PD_BLANK_BURN){
  const t0=Date.now();let n=0,sum=0;
  while(Date.now()-t0<12000){const js=await bench();sum+=js;n++;console.log('BURN js='+js+' t='+(Date.now()-t0))}
  console.log('BURN n='+n+' avg='+(sum/n).toFixed(1));
  await browser.close();
  process.exit(0);
}
for (let k=0;k<18;k++){
  const t = Math.round(await page.evaluate(()=>performance.now()));
  const js = await bench();
  const vis = await page.evaluate(()=>({v:document.visibilityState,f:document.hasFocus(),ow:window.outerWidth>0,ih:window.innerHeight}));
  console.log('BLANK-BENCH t='+t+' js='+js+' vis='+JSON.stringify(vis));
  await page.waitForTimeout(350);
}
await browser.close();
