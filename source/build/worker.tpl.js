// Royals Attack Stats: Cloudflare Worker (one file, paste into the dashboard editor).
//
// What it does
//  - Serves the app at your Worker address.
//  - /admin lets you upload a new app file (royals-stats-update.html) to install an update.
//    Uploaded versions are kept in a KV namespace, so no redeploy is needed.
//
// One-time setup in the Cloudflare dashboard (no command line needed)
//  1. Workers & Pages > Create > Hello World > Deploy, then Edit code and paste this whole file.
//  2. Storage & Databases > KV > Create a namespace (any name).
//  3. Worker > Settings > Bindings > Add > KV namespace: variable name APP_KV, pick that namespace.
//  4. Worker > Settings > Variables and Secrets > Add a Secret named ADMIN_PASSWORD.
//  5. Open https://YOUR-WORKER.workers.dev/admin to upload updates later.
//
// Stats are stored in each device's browser. Updating the app never touches them.

const APP_ID = 'royals-attack-stats';
const MAX_BYTES = 5 * 1024 * 1024;

const HTML = __HTML__;
const ADMIN = __ADMIN__;
const SW = __SW__;
const MANIFEST = __MANIFEST__;
const ASSETS = __ASSETS__;

const te = new TextEncoder();
const fromB64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const json = (o, status) => new Response(JSON.stringify(o), {
  status: status || 200,
  headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }
});
const versionOf = (html) => {
  const m = /<meta name="app-version" content="([^"]*)"/.exec(html || '');
  return m ? m[1] : 'unknown';
};

async function sha(s) {
  return new Uint8Array(await crypto.subtle.digest('SHA-256', te.encode(s)));
}
// 'ok' | 'bad' | 'nopass'
async function checkPassword(req, env) {
  if (!env.ADMIN_PASSWORD) return 'nopass';
  const given = req.headers.get('x-admin-password') || '';
  const a = await sha(given);
  const b = await sha(String(env.ADMIN_PASSWORD));
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a[i] ^ b[i];
  return d === 0 ? 'ok' : 'bad';
}
async function readJson(env, key) {
  try {
    const t = await env.APP_KV.get(key);
    return t ? JSON.parse(t) : null;
  } catch (e) {
    return null;
  }
}

async function serveApp(env) {
  let html = null;
  if (env.APP_KV) {
    try { html = await env.APP_KV.get('app:current'); } catch (e) { html = null; }
  }
  return new Response(html || HTML, {
    headers: {
      'content-type': 'text/html; charset=utf-8',
      'cache-control': 'no-cache',
      'x-content-type-options': 'nosniff'
    }
  });
}

async function status(env) {
  const out = {
    kvBound: !!env.APP_KV,
    passwordSet: !!env.ADMIN_PASSWORD,
    builtInVersion: versionOf(HTML),
    source: 'built-in',
    version: versionOf(HTML),
    uploadedAt: null,
    hasPrevious: false,
    prevVersion: null
  };
  if (env.APP_KV) {
    const meta = await readJson(env, 'app:meta');
    let cur = null;
    try { cur = await env.APP_KV.get('app:current'); } catch (e) {}
    if (cur) {
      out.source = 'uploaded';
      out.version = (meta && meta.version) || versionOf(cur);
      out.uploadedAt = (meta && meta.uploadedAt) || null;
    }
    let prev = null;
    try { prev = await env.APP_KV.get('app:prev'); } catch (e) {}
    if (prev) {
      const pm = await readJson(env, 'app:prevmeta');
      out.hasPrevious = true;
      out.prevVersion = (pm && pm.version) || versionOf(prev);
    }
  }
  return json(out);
}

// Shared guard for the three POST actions.
async function guard(req, env) {
  const p = await checkPassword(req, env);
  if (p === 'nopass') return json({ error: 'No password is set yet. Add a Secret named ADMIN_PASSWORD in the Worker settings.' }, 403);
  if (p === 'bad') return json({ error: 'Wrong password.' }, 401);
  if (!env.APP_KV) return json({ error: 'Storage is not connected. Add a KV binding named APP_KV in the Worker settings.' }, 500);
  return null;
}

async function upload(req, env) {
  const denied = await guard(req, env);
  if (denied) return denied;
  const text = await req.text();
  if (text.length > MAX_BYTES) return json({ error: 'That file is too large.' }, 413);
  if (!/<!doctype html/i.test(text) || !/<\/html>/i.test(text)) {
    return json({ error: 'That does not look like a full app file. Use royals-stats-update.html.' }, 400);
  }
  if (text.indexOf('<meta name="app-id" content="' + APP_ID + '">') === -1) {
    return json({ error: 'That file is not the Royals Attack Stats app, so it was not installed.' }, 400);
  }
  const version = versionOf(text);
  const cur = await env.APP_KV.get('app:current');
  if (cur) {
    const curMeta = await env.APP_KV.get('app:meta');
    await env.APP_KV.put('app:prev', cur);
    await env.APP_KV.put('app:prevmeta', curMeta || '{}');
  }
  await env.APP_KV.put('app:current', text);
  await env.APP_KV.put('app:meta', JSON.stringify({ version: version, uploadedAt: new Date().toISOString(), bytes: text.length }));
  return json({ message: 'Installed version ' + version + '. Close and reopen the app to see it. It can take up to a minute to reach every device.' });
}

async function rollback(req, env) {
  const denied = await guard(req, env);
  if (denied) return denied;
  const prev = await env.APP_KV.get('app:prev');
  if (!prev) return json({ error: 'There is no previous version saved.' }, 400);
  const prevMeta = await env.APP_KV.get('app:prevmeta');
  const cur = await env.APP_KV.get('app:current');
  const curMeta = await env.APP_KV.get('app:meta');
  await env.APP_KV.put('app:current', prev);
  await env.APP_KV.put('app:meta', prevMeta || '{}');
  if (cur) {
    await env.APP_KV.put('app:prev', cur);
    await env.APP_KV.put('app:prevmeta', curMeta || '{}');
  } else {
    await env.APP_KV.delete('app:prev');
    await env.APP_KV.delete('app:prevmeta');
  }
  return json({ message: 'Went back to version ' + versionOf(prev) + '.' });
}

async function useBuiltIn(req, env) {
  const denied = await guard(req, env);
  if (denied) return denied;
  const cur = await env.APP_KV.get('app:current');
  if (!cur) return json({ message: 'Already using the built-in version.' });
  const curMeta = await env.APP_KV.get('app:meta');
  await env.APP_KV.put('app:prev', cur);
  await env.APP_KV.put('app:prevmeta', curMeta || '{}');
  await env.APP_KV.delete('app:current');
  await env.APP_KV.delete('app:meta');
  return json({ message: 'Now using the built-in version ' + versionOf(HTML) + '.' });
}

export default {
  async fetch(req, env) {
    const path = new URL(req.url).pathname;
    if (path === '/' || path === '/index.html') return serveApp(env);
    if (path === '/admin' || path === '/admin/') {
      return new Response(ADMIN, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } });
    }
    if (path === '/admin/status') return status(env);
    if (req.method === 'POST') {
      if (path === '/admin/upload') return upload(req, env);
      if (path === '/admin/rollback') return rollback(req, env);
      if (path === '/admin/builtin') return useBuiltIn(req, env);
    }
    if (path === '/manifest.webmanifest') {
      return new Response(MANIFEST, { headers: { 'content-type': 'application/manifest+json', 'cache-control': 'public, max-age=3600' } });
    }
    if (path === '/sw.js') {
      return new Response(SW, { headers: { 'content-type': 'application/javascript; charset=utf-8', 'cache-control': 'no-cache', 'service-worker-allowed': '/' } });
    }
    if (ASSETS[path]) {
      return new Response(fromB64(ASSETS[path]), { headers: { 'content-type': 'image/png', 'cache-control': 'public, max-age=86400' } });
    }
    return new Response('Not found', { status: 404 });
  }
};
