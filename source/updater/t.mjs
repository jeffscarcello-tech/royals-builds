import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';
import loader from './loader.mjs';
import updater from './updater.mjs';
let F=0;const chk=(n,c)=>{console.log((c?'PASS ':'FAIL ')+n);if(!c)F++};
function mkdb(){const s=new DatabaseSync(':memory:');
 const prep=(sql)=>{let args=[];const o={bind(...a){args=a;return o},
  async run(){s.prepare(sql).run(...args);return{}},
  async first(){return s.prepare(sql).get(...args)||null},
  async all(){return{results:s.prepare(sql).all(...args)}},
  _x(){s.prepare(sql).run(...args)}};return o};
 return{prepare:prep,async batch(st){for(const x of st)x._x();return[]}}}
const app=fs.readFileSync('../dist/app.json','utf8'), bt=fs.readFileSync('../dist/build.txt','utf8');
let fetchMode='ok';
globalThis.fetch=async(u)=>{u=String(u);
 if(fetchMode==='404')return new Response('',{status:404});
 if(u.includes('/test/build.txt'))return new Response(fetchMode==='mismatch'?'2026-99-99.9\n':bt);
 if(u.includes('/test/app.json'))return new Response(fetchMode==='wrong'?app.replace('"app": "royals"','"app": "darts"'):app);
 return new Response('',{status:404})};
const db=mkdb(),env={TEST_DB:db,DB:db,ADMIN_PASSWORD:'pw'};
const run=async()=>{await updater.scheduled({},env,{waitUntil:p=>p});await new Promise(r=>setTimeout(r,200));
 const g=await db.prepare("SELECT v FROM appmeta WHERE k='ghlast'").first();return JSON.parse(g.v).r};
fetchMode='404';chk('404 reports nothing_to_install',await run()==='nothing_to_install');
fetchMode='mismatch';chk('mismatch caught',await run()==='build_name_mismatch');
fetchMode='wrong';chk('wrong app caught',await run()==='wrong_app');
fetchMode='ok';let r=await run();chk('installs: '+r,r==='installed '+bt.trim());
r=await run();chk('second run up_to_date',r==='up_to_date');
const get=(p,o)=>loader.fetch(new Request('https://x'+p,o),env);
let x=await get('/');let t=await x.text();chk('/ serves html',x.status===200&&t.includes('app-version')&&t.includes(bt.trim())&&t.includes('apple-touch-icon.png?v='));
x=await get('/sw.js');t=await x.text();chk('sw cache name',t.includes('royals-stats-'+bt.trim()));
x=await get('/manifest.webmanifest');chk('manifest',(await x.json()).icons.length===3);
for(const p of['/icon-192.png','/icon-512.png','/apple-touch-icon.png']){x=await get(p);const b=new Uint8Array(await x.arrayBuffer());chk(p+' png',b[1]===0x50&&b[2]===0x4e)}
x=await get('/icon.svg');chk('svg',(await x.text()).startsWith('<svg'));
x=await get('/api/health');const h=await x.json();chk('health',h.ok&&h.build===bt.trim()&&h.updater.r.startsWith('up_to_date'));
x=await get('/nope');chk('404',x.status===404);
const html=fs.readFileSync('../out/royals-stats-update.html','utf8').replace(bt.trim(),'9999-01-01.1');
x=await get('/admin/upload',{method:'POST',body:html});chk('admin no pw 401',x.status===401);
x=await loader.fetch(new Request('https://x/admin/upload',{method:'POST',body:html}),{DB:db});chk('admin no secret 403',x.status===403);
x=await get('/admin/upload',{method:'POST',headers:{'x-admin-password':'pw'},body:'<html>'});chk('admin bad file 400',x.status===400);
x=await get('/admin/upload',{method:'POST',headers:{'x-admin-password':'pw'},body:html});chk('admin ok',x.status===200);
x=await get('/api/health');chk('admin build live',(await x.json()).build==='9999-01-01.1');
const fresh=(await import('./loader.mjs?fresh')).default;const empty=mkdb();x=await fresh.fetch(new Request('https://x/'),{DB:empty});chk('almost ready 503',x.status===503&&(await x.text()).includes('Almost ready'));
console.log('FAILS:',F);
