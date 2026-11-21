// Royals Attack Stats: site Worker. Serves the app out of the D1 database (binding DB).
// Updates arrive from GitHub through royals-updater. /admin is a manual fallback (needs the ADMIN_PASSWORD secret).
const LOADER = 'l1';
const PART = 50000;
let appCache = null, appChecked = 0;
async function loadApp(db) {
  if (appCache && Date.now() - appChecked < 15000) return appCache;
  await db.prepare('CREATE TABLE IF NOT EXISTS appmeta (k TEXT PRIMARY KEY, v TEXT NOT NULL)').run();
  await db.prepare('CREATE TABLE IF NOT EXISTS apppart (ver TEXT NOT NULL, i INTEGER NOT NULL, d TEXT NOT NULL, PRIMARY KEY (ver, i))').run();
  const m = await db.prepare("SELECT v FROM appmeta WHERE k = 'cur'").first();
  appChecked = Date.now();
  if (!m) return (appCache = null);
  const cur = JSON.parse(m.v);
  if (appCache && appCache.ver === cur.ver) return appCache;
  const rows = (await db.prepare('SELECT d FROM apppart WHERE ver = ?1 ORDER BY i').bind(cur.ver).all()).results || [];
  if (rows.length !== cur.n) return appCache;
  try { const b = JSON.parse(rows.map(r => r.d).join('')); b.ver = cur.ver; appCache = b; } catch (e) {}
  return appCache;
}
const NOCACHE = { 'cache-control': 'no-cache', 'x-content-type-options': 'nosniff' };
const fromB64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const te = new TextEncoder();
async function sha(s) { return new Uint8Array(await crypto.subtle.digest('SHA-256', te.encode(s))); }
async function passOk(req, env) {
  if (!env.ADMIN_PASSWORD) return 'nopass';
  const a = await sha(req.headers.get('x-admin-password') || ''), b = await sha(String(env.ADMIN_PASSWORD));
  let d = 0; for (let i = 0; i < a.length; i++) d |= a[i] ^ b[i];
  return d === 0 ? 'ok' : 'bad';
}
const json = (o, s) => new Response(JSON.stringify(o), { status: s || 200, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
const ALMOST = '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Almost ready</title><body style="font:18px system-ui;padding:32px;text-align:center"><h2>Almost ready</h2><p>The app is being installed. Check back in a few minutes.</p>';
const ADMIN = '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Royals update</title><body style="font:16px system-ui;max-width:520px;margin:24px auto;padding:0 16px"><h2>Install an update</h2><p>Updates normally arrive from GitHub on their own. Use this only as a backup.</p><input id=p type=password placeholder="Admin password" style="width:100%;padding:12px;margin:6px 0"><input id=f type=file accept=".html" style="width:100%;padding:12px;margin:6px 0"><button id=b style="width:100%;padding:14px;font-size:18px">Install</button><p id=m></p><script>b.onclick=async()=>{const x=f.files[0];if(!x){m.textContent="Pick royals-stats-update.html first";return}m.textContent="Installing...";const r=await fetch("/admin/upload",{method:"POST",headers:{"x-admin-password":p.value},body:await x.text()});const j=await r.json().catch(()=>({}));m.textContent=r.ok?"Installed "+j.build:"Failed: "+(j.error||r.status)}</script>';
async function install(db, bundle) {
  const text = JSON.stringify(bundle), ver = String(bundle.build).replace(/[^A-Za-z0-9]/g, '').slice(0, 14) + Date.now().toString(36);
  const n = Math.ceil(text.length / PART);
  for (let i = 0; i < n; i += 8) {
    const st = [];
    for (let j = i; j < Math.min(n, i + 8); j++) st.push(db.prepare('INSERT OR REPLACE INTO apppart (ver, i, d) VALUES (?1, ?2, ?3)').bind(ver, j, text.slice(j * PART, (j + 1) * PART)));
    await db.batch(st);
  }
  const rows = (await db.prepare('SELECT d FROM apppart WHERE ver = ?1 ORDER BY i').bind(ver).all()).results || [];
  if (rows.length !== n || rows.map(r => r.d).join('') !== text) { await db.prepare('DELETE FROM apppart WHERE ver = ?1').bind(ver).run(); throw new Error('readback_mismatch'); }
  await db.prepare('INSERT OR REPLACE INTO appmeta (k, v) VALUES (?1, ?2)').bind('cur', JSON.stringify({ ver, n })).run();
  await db.prepare('DELETE FROM apppart WHERE ver != ?1').bind(ver).run();
  appCache = null; appChecked = 0;
}
export default {
  async fetch(req, env) {
    const url = new URL(req.url), p = url.pathname;
    if (!env.DB) return new Response('Database not connected', { status: 500 });
    if (p === '/admin') return new Response(ADMIN, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } });
    if (p === '/admin/upload' && req.method === 'POST') {
      const ok = await passOk(req, env);
      if (ok === 'nopass') return json({ error: 'Admin password is not set on this site' }, 403);
      if (ok !== 'ok') return json({ error: 'Wrong password' }, 401);
      const html = await req.text();
      const m = /<meta name="app-id" content="royals-attack-stats">/.test(html), v = /<meta name="app-version" content="([^"]*)"/.exec(html);
      if (!m || !v || html.length < 1000) return json({ error: 'That is not a Royals Stats update file' }, 400);
      const cur = await loadApp(env.DB);
      if (!cur) return json({ error: 'Nothing installed yet to reuse icons from' }, 409);
      const b = Object.assign({}, cur); delete b.ver; b.html = html; b.build = v[1];
      try { await install(env.DB, b); } catch (e) { return json({ error: String(e.message || e) }, 500); }
      return json({ ok: true, build: v[1] });
    }
    const app = await loadApp(env.DB);
    if (p === '/api/health') {
      const g = await env.DB.prepare("SELECT v FROM appmeta WHERE k = 'ghlast'").first().catch(() => null);
      return json({ ok: !!app, app: 'royals', build: app ? app.build : null, loader: LOADER, updater: g ? JSON.parse(g.v) : null });
    }
    if (!app) return new Response(ALMOST, { status: 503, headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } });
    const png = (b64) => new Response(fromB64(b64), { headers: { 'content-type': 'image/png', 'cache-control': 'public, max-age=3600' } });
    if (p === '/' || p === '/index.html') return new Response(app.html, { headers: Object.assign({ 'content-type': 'text/html; charset=utf-8' }, NOCACHE) });
    if (p === '/sw.js') return new Response(app.sw, { headers: Object.assign({ 'content-type': 'application/javascript; charset=utf-8' }, NOCACHE) });
    if (p === '/manifest.webmanifest') return new Response(app.manifest, { headers: Object.assign({ 'content-type': 'application/manifest+json' }, NOCACHE) });
    if (p === '/icon.svg') return new Response(app.icon_svg, { headers: { 'content-type': 'image/svg+xml', 'cache-control': 'public, max-age=3600' } });
    if (p === '/icon-192.png') return png(app.i192);
    if (p === '/icon-512.png') return png(app.i512);
    if (p === '/apple-touch-icon.png') return png(app.apple);
    const f = app.files && app.files[p];
    if (f) return new Response(fromB64(f.b64), { headers: { 'content-type': f.type, 'cache-control': 'public, max-age=3600' } });
    return new Response('Not found', { status: 404 });
  }
};
