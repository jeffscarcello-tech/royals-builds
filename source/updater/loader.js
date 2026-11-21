// Royals Attack Stats: site Worker. Serves the app out of the D1 database (binding DB).
// Updates arrive from GitHub through royals-updater. /admin is a manual fallback (needs the ADMIN_PASSWORD secret).
const LOADER = 'l2';
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

// ---- game summary links: /api/live/:code (kept 30 days for a final game, 3 days otherwise) ----
const CORS = { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'GET, PUT, DELETE, OPTIONS', 'access-control-allow-headers': 'Content-Type, X-Write-Key', 'access-control-max-age': '86400' };
const LIVE_MAX = 900 * 1024;
const DAY = 86400000;
const hexOf = (b) => Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
async function liveEnsure(db) {
  await db.prepare('CREATE TABLE IF NOT EXISTS live (code TEXT PRIMARY KEY, rev INTEGER, key_hash TEXT, updated INTEGER, expires INTEGER, data TEXT)').run();
  await db.prepare('CREATE TABLE IF NOT EXISTS livenew (ip TEXT NOT NULL, at INTEGER NOT NULL)').run();
}
async function liveApi(req, env, code) {
  const db = env.DB;
  const lj = (o, s) => new Response(JSON.stringify(o), { status: s || 200, headers: Object.assign({ 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }, CORS) });
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
  if (!/^[A-HJKMNP-Z2-9]{6}$/.test(code)) return lj({ error: 'bad_code' }, 400);
  await liveEnsure(db);
  const now = Date.now();
  if (req.method === 'GET') {
    const row = await db.prepare('SELECT rev, updated, expires, data FROM live WHERE code = ?1').bind(code).first();
    if (!row || row.expires < now) return lj({ error: 'not_found' }, 404);
    const since = new URL(req.url).searchParams.get('rev');
    if (since !== null && String(row.rev) === since) return lj({ unchanged: true, rev: row.rev });
    return lj({ rev: row.rev, updated: row.updated, data: JSON.parse(row.data) });
  }
  if (req.method !== 'PUT' && req.method !== 'DELETE') return lj({ error: 'method_not_allowed' }, 405);
  const key = req.headers.get('x-write-key') || '';
  if (key.length < 16 || key.length > 200) return lj({ error: 'bad_key' }, 400);
  const kh = hexOf(await sha(key));
  const row = await db.prepare('SELECT rev, key_hash, expires FROM live WHERE code = ?1').bind(code).first();
  const exists = !!row && row.expires >= now;
  if (req.method === 'DELETE') {
    if (!exists) return lj({ ok: true, gone: true });
    if (row.key_hash !== kh) return lj({ error: 'wrong_key' }, 403);
    await db.prepare('DELETE FROM live WHERE code = ?1').bind(code).run();
    return lj({ ok: true });
  }
  if (+(req.headers.get('content-length') || 0) > LIVE_MAX) return lj({ error: 'too_big' }, 413);
  const text = await req.text();
  if (te.encode(text).length > LIVE_MAX) return lj({ error: 'too_big' }, 413);
  let body; try { body = JSON.parse(text); } catch (e) { return lj({ error: 'bad_json' }, 400); }
  const rev = body && body.rev, data = body && body.data;
  if (!Number.isSafeInteger(rev) || rev < 0 || !data || typeof data !== 'object' || Array.isArray(data)) return lj({ error: 'bad_body' }, 400);
  if (exists && row.key_hash !== kh) return lj({ error: 'code_taken' }, 403);
  if (exists && rev <= row.rev) return lj({ ok: true, ignored: true, rev: row.rev });
  if (!exists) {   // a new code: limit per network address (updates never count)
    const ip = req.headers.get('cf-connecting-ip') || 'unknown';
    const c = await db.prepare('SELECT COALESCE(SUM(CASE WHEN at > ?2 THEN 1 ELSE 0 END), 0) AS h, COUNT(*) AS d FROM livenew WHERE ip = ?1 AND at > ?3').bind(ip, now - 3600000, now - DAY).first();
    if ((c ? c.h : 0) >= 40 || (c ? c.d : 0) >= 150) return lj({ error: 'rate_limited' }, 429);
    await db.prepare('INSERT INTO livenew (ip, at) VALUES (?1, ?2)').bind(ip, now).run();
  }
  const expires = now + (data.status === 'final' ? 30 : 3) * DAY;
  await db.prepare('INSERT OR REPLACE INTO live (code, rev, key_hash, updated, expires, data) VALUES (?1, ?2, ?3, ?4, ?5, ?6)').bind(code, rev, kh, now, expires, JSON.stringify(data)).run();
  if (Math.random() < 0.05) {
    await db.prepare('DELETE FROM live WHERE expires < ?1').bind(now).run();
    await db.prepare('DELETE FROM livenew WHERE at < ?1').bind(now - DAY).run();
  }
  return lj({ ok: true, rev });
}
export default {
  async fetch(req, env) {
    const url = new URL(req.url), p = url.pathname;
    if (!env.DB) return new Response('Database not connected', { status: 500 });
    const lm = /^\/api\/live\/([^/]+)$/.exec(p);
    if (lm) return liveApi(req, env, lm[1]);
    const frame = url.searchParams.has('live') ? {} : { 'x-frame-options': 'DENY' };
    if (p === '/admin') return new Response(ADMIN, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-frame-options': 'DENY' } });
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
    if (!app) return new Response(ALMOST, { status: 503, headers: Object.assign({ 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' }, frame) });
    const png = (b64) => new Response(fromB64(b64), { headers: { 'content-type': 'image/png', 'cache-control': 'public, max-age=3600' } });
    if (p === '/' || p === '/index.html') return new Response(app.html, { headers: Object.assign({ 'content-type': 'text/html; charset=utf-8' }, NOCACHE, frame) });
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
