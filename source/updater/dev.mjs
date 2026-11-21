// Local stand-in for the royalstest Worker: real loader.mjs + SQLite in place of D1.
import http from 'node:http';
import fs from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import loader from './loader.mjs';
const s=new DatabaseSync(':memory:');
const prep=(sql)=>{let args=[];const o={bind(...a){args=a;return o},async run(){s.prepare(sql).run(...args);return{}},async first(){return s.prepare(sql).get(...args)||null},async all(){return{results:s.prepare(sql).all(...args)}},_x(){s.prepare(sql).run(...args)}};return o};
const env={DB:{prepare:prep,async batch(st){for(const x of st)x._x();return[]}},ADMIN_PASSWORD:'pw'};
const text=fs.readFileSync('../dist/app.json','utf8');
s.exec('CREATE TABLE appmeta (k TEXT PRIMARY KEY, v TEXT NOT NULL); CREATE TABLE apppart (ver TEXT NOT NULL, i INTEGER NOT NULL, d TEXT NOT NULL, PRIMARY KEY (ver, i))');
const n=Math.ceil(text.length/50000);for(let i=0;i<n;i++)s.prepare('INSERT INTO apppart VALUES (?,?,?)').run('dev',i,text.slice(i*50000,(i+1)*50000));
s.prepare('INSERT INTO appmeta VALUES (?,?)').run('cur',JSON.stringify({ver:'dev',n}));
http.createServer(async (req,res)=>{
  const chunks=[];for await(const c of req)chunks.push(c);
  const body=chunks.length?Buffer.concat(chunks):undefined;
  const h=new Headers();for(const [k,v] of Object.entries(req.headers))if(typeof v==='string')h.set(k,v);
  h.set('cf-connecting-ip','127.0.0.1');
  const r=await loader.fetch(new Request('http://localhost:8787'+req.url,{method:req.method,headers:h,body:['GET','HEAD'].includes(req.method)?undefined:body}),env);
  const out={};r.headers.forEach((v,k)=>out[k]=v);
  res.writeHead(r.status,out);res.end(Buffer.from(await r.arrayBuffer()));
}).listen(8787,()=>console.log('dev on 8787'));
