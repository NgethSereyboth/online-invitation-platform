import {readFileSync} from 'node:fs';
const file=process.argv[2];
const t0=Number(process.argv[3]||0),t1=Number(process.argv[4]||140),minDur=Number(process.argv[5]||2);
const buf=readFileSync(file);
const text=(buf.length>2&&buf[1]===0x00&&buf[0]!==0x00)||(buf[0]===0xFF&&buf[1]===0xFE)?buf.toString('utf16le'):buf.toString('utf8');
const lines=text.replace(/^\uFEFF/,'').split(/\r?\n/);
const sections={};
let cur=null;
for(const ln of lines){
  if(/^SNAP-TRACE-BY-NAME/.test(ln)){cur='by';continue}
  if(/^SNAP-TRACE-TIMELINE/.test(ln)){cur='tl';continue}
  if(/^SNAP-TRACE-EVENTS/.test(ln)){cur='ev';continue}
  if(/^SNAP-TRACE-FC/.test(ln)){cur='fc';continue}
  if(/^SNAP-MARKS|^SNAP-FRAMES|^SNAP-LT|^CENSUS|^bigFrames|^longTasks|^PD-|^WRITES|^MO |^\[run-with-server\]/.test(ln)){cur=null;continue}
  if(cur)(sections[cur]=sections[cur]||[]).push(ln);
}
const tl=(sections.tl||[]).map(l=>{const p=l.split('\t');if(p.length<3)return null;const t=Number(p[0]);if(!isFinite(t))return null;return{t,line:l};}).filter(Boolean);
const inWin=tl.filter(r=>r.t>=t0&&r.t<=t1);
const dur=l=>{const p=l.split('\t');return Number(p[2])||0};
console.log(`# window ${t0}..${t1}  entries=${inWin.length}`);
for(const r of inWin.sort((a,b)=>a.t-b.t)){
  if(dur(r.line)>=minDur)console.log(r.t.toFixed(1)+'\t'+r.line.split('\t').slice(1).join(' '));
}
const agg=new Map();
for(const r of inWin){const d=dur(r.line);const n=r.line.split('\t')[1];agg.set(n,(agg.get(n)||0)+d)}
console.log('--- by name (us total) ---');
console.log([...agg.entries()].sort((a,b)=>b[1]-a[1]).slice(0,20).map(([k,v])=>`${v}\t${k}`).join('\n'));
if(sections.ev){
  console.log('--- EVENTS ---');
  for(const l of sections.ev){const p=l.split('\t');const t=Number(p[0]);if(isFinite(t))console.log(l)}
}
if(sections.fc){
  console.log('--- FC >=2ms ---');
  for(const l of sections.fc){const p=l.split('\t');const d=Number(p[0]);if(isFinite(d)&&d>=2000)console.log(l)}
}
// invalidation instants + ULT waves near the window
const raw=text.split(/\r?\n/);
const inval=new Map();
const ult=[];
for(const ln of lines){
  const p=ln.split('\t');
  const t=Number(p[0]);if(!isFinite(t))continue;
}
