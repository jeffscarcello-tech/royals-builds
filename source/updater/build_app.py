import base64, json, os, re, subprocess, sys
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
subprocess.check_call([sys.executable, '-I', os.path.join(R, 'build', 'build.py')], stdout=subprocess.DEVNULL)
v = json.load(open(os.path.join(R, 'version.json')))
b = v['build']
assert re.fullmatch(r'[A-Za-z0-9._-]{3,40}', b)
assert "'" not in v['label']
html = open(os.path.join(R, 'out', 'royals-stats-update.html'), encoding='utf-8').read()
assert ('content="%s"' % b) in html, 'app-version meta does not match version.json'
for a in ['/apple-touch-icon.png', '/icon-192.png']:
    html = html.replace('href="%s"' % a, 'href="%s?v=%s"' % (a, b))
sw = open(os.path.join(R, 'build', 'sw.js'), encoding='utf-8').read()
assert "'royals-stats-v1'" in sw
sw = sw.replace("'royals-stats-v1'", "'%s%s'" % (v['cache_prefix'], b))
manifest = json.dumps({
  "name": "Royals Attack Stats", "short_name": "Royals Stats", "start_url": "/", "scope": "/",
  "display": "standalone", "orientation": "portrait", "background_color": "#eef1fa", "theme_color": "#20205f",
  "icons": [{"src": "/icon-192.png?v=" + b, "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png?v=" + b, "sizes": "512x512", "type": "image/png"},
            {"src": "/icon-512.png?v=" + b, "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]})
png = lambda n: base64.b64encode(open(os.path.join(R, 'build', n), 'rb').read()).decode()
svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="22" fill="#20205f"/><text x="50" y="72" font-family="Arial Black,Arial,sans-serif" font-size="66" font-weight="900" text-anchor="middle" fill="#fff">S</text></svg>'
app = {"app": "royals", "build": b, "label": v['label'], "html": html, "sw": sw, "manifest": manifest,
       "icon_svg": svg, "i192": png('icon-192.png'), "i512": png('icon-512.png'), "apple": png('apple-touch-icon.png'), "files": {}}
os.makedirs(os.path.join(R, 'dist'), exist_ok=True)
open(os.path.join(R, 'dist', 'app.json'), 'w', encoding='utf-8').write(json.dumps(app))
open(os.path.join(R, 'dist', 'build.txt'), 'w').write(b + '\n')
print('built', b, os.path.getsize(os.path.join(R, 'dist', 'app.json')))
