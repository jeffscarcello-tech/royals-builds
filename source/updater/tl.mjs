import { DatabaseSync } from 'node:sqlite';
import loader from './loader.mjs';
let F=0;const chk=(n,c)=>{console.log((c?'PASS ':'FAIL ')+n);if(!c)F++};
const s=new DatabaseSync(':memory:');
const prep=(sql)=>{let args=[];const o={bind(...a){args=a;return o},async run(){s.prepare(sql).run(...args);return{}},async first(){return s.prepare(sql).get(...args)||null},async all(){return{results:s.prepare(sql).all(...args)}},_x(){s.prepare(sql).run(...args)}};return o};
const env={DB:{prepare:prep,async batch(st){for(const x of st)x._x();return[]}}};
const K='0123456789abcdef0123456789abcdef',K2='ffffffffffffffffffffffffffffffff';
const call=(m,code,{key,body,ip,q,raw}={})=>loader.fetch(new Request('https://x/api/live/'+code+(q||''),{method:m,headers:Object.assign({'content-type':'application/json'},key?{'x-write-key':key}:{},{'cf-connecting-ip':ip||'1.1.1.1'}),body:raw!==undefined?raw:(body?JSON.stringify(body):undefined)}),env);
const data={app:'royals',status:'final',p:{v:1}};
let r=await call('PUT','ABC234',{key:K,body:{rev:1,data}});chk('put new',r.status===200);
r=await call('GET','ABC234');let j=await r.json();chk('get',r.status===200&&j.rev===1&&j.data.app==='royals');
chk('cors on get',r.headers.get('access-control-allow-origin')==='*');
r=await call('GET','ABC234',{q:'?rev=1'});chk('unchanged',(await r.json()).unchanged===true);
r=await call('PUT','ABC234',{key:K2,body:{rev:5,data}});chk('wrong key 403',r.status===403);
r=await call('PUT','ABC234',{key:K,body:{rev:1,data:{app:'royals',status:'final',x:1}}});j=await r.json();chk('old rev ignored',r.status===200&&j.ignored);
r=await call('GET','ABC234');chk('old rev not saved',!(await r.json()).data.x);
r=await call('PUT','ABC234',{key:K,body:{rev:2,data:{app:'royals',status:'final',x:2}}});r=await call('GET','ABC234',{q:'?rev=1'});j=await r.json();chk('newer rev saved',j.rev===2&&j.data.x===2);
r=await call('PUT','ABC234',{key:'short',body:{rev:3,data}});chk('short key 400',r.status===400);
r=await call('PUT','ABC234',{key:K,raw:JSON.stringify({rev:3,data:{status:'final',pad:'x'.repeat(930000)}})});chk('too big 413',r.status===413);
r=await call('PUT','abc234',{key:K,body:{rev:1,data}});chk('bad code 400',r.status===400);
r=await call('PUT','ABC23O',{key:K,body:{rev:1,data}});chk('look-alike letter rejected',r.status===400);
r=await call('PUT','ABC235',{key:K,body:{rev:1,data:[1]}});chk('bad body 400',r.status===400);
r=await call('DELETE','ABC234',{key:K2});chk('delete wrong key 403',r.status===403);
r=await call('DELETE','ABC234',{key:K});chk('delete ok',r.status===200);
r=await call('GET','ABC234');chk('gone after delete',r.status===404);
r=await call('OPTIONS','ABC234');chk('options 204',r.status===204&&/PUT/.test(r.headers.get('access-control-allow-methods')));
// expiry: final 30 days, in progress 3 days
await call('PUT','EXP222',{key:K,body:{rev:1,data:{status:'live'}}});
let row=s.prepare("SELECT expires-updated AS d FROM live WHERE code='EXP222'").get();chk('in-progress keeps 3 days',row.d===3*86400000);
await call('PUT','FNQ222',{key:K,body:{rev:1,data}});
row=s.prepare("SELECT expires-updated AS d FROM live WHERE code='FNQ222'").get();chk('final keeps 30 days',row.d===30*86400000);
s.prepare("UPDATE live SET expires=1 WHERE code='FNQ222'").run();
r=await call('GET','FNQ222');chk('expired 404',r.status===404);
// rate limit: 40 new codes an hour per network
s.prepare('DELETE FROM livenew').run();
const codes=[];for(let i=0;i<41;i++){let c='';for(const ch of String(i).padStart(2,'0'))c+='ABCDEFGHJK'[+ch];codes.push('RT'+c+'ZZ')}
let st=[];for(let i=0;i<41;i++){r=await call('PUT',codes[i],{key:K,body:{rev:1,data},ip:'9.9.9.9'});st.push(r.status)}
chk('40 allowed then 429',st.slice(0,40).every(x=>x===200)&&st[40]===429);
r=await call('PUT',codes[0],{key:K,body:{rev:2,data},ip:'9.9.9.9'});chk('update not limited',r.status===200);
r=await call('PUT','THRSXY',{key:K,body:{rev:1,data},ip:'8.8.8.8'});chk('other network fine',r.status===200);
// 150 a day
s.prepare('DELETE FROM livenew').run();
const old=Date.now()-2*3600000;for(let i=0;i<150;i++)s.prepare('INSERT INTO livenew (ip,at) VALUES (?,?)').run('7.7.7.7',old);
r=await call('PUT','DAYQQQ',{key:K,body:{rev:1,data},ip:'7.7.7.7'});chk('150 a day limit',r.status===429);
// frame headers
const fr=(u)=>loader.fetch(new Request('https://x'+u),env);
r=await fr('/');chk('app refuses framing',r.headers.get('x-frame-options')==='DENY');
r=await fr('/?live=ABC234');chk('summary page may be framed',r.headers.get('x-frame-options')===null);
r=await fr('/admin');chk('admin refuses framing',r.headers.get('x-frame-options')==='DENY');
console.log('FAILS:',F);
