import base64, json, re, os
D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, '..', 'out')
os.makedirs(OUT, exist_ok=True)
rd = lambda n: open(os.path.join(D, n), encoding='utf-8').read()

logo = base64.b64encode(open(os.path.join(D, 'logo_small.png'), 'rb').read()).decode()
lw, lh = open(os.path.join(D, 'lw.txt')).read().split()
src = rd('app.src.html')
src = src.replace('%%LOGO%%', 'data:image/png;base64,' + logo).replace('%%LW%%', lw).replace('%%LH%%', lh)

# 1) artifact copy (same page, no standalone bits)
open(os.path.join(OUT, 'royals-attack-stats.html'), 'w', encoding='utf-8').write(src)

# 2) standalone page used by the Worker and for update uploads
body_src = src.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '', 1)
i = body_src.index('</style>') + len('</style>')
head_wrap = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#20205f">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Royals Stats">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="icon" type="image/png" href="/icon-192.png">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
'''
sw_reg = '''<script>if('serviceWorker' in navigator&&/^https?:$/.test(location.protocol)){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').catch(function(){})})}</script>
'''
html = head_wrap + body_src[:i] + '\n</head>\n<body>\n<script>window.__STANDALONE=1;</script>' + body_src[i:] + '\n' + sw_reg + '</body>\n</html>\n'
open(os.path.join(OUT, 'royals-stats-update.html'), 'w', encoding='utf-8').write(html)

# 3) worker
manifest = json.dumps({
    "name": "Royals Attack Stats", "short_name": "Royals Stats", "start_url": "/", "scope": "/",
    "display": "standalone", "orientation": "portrait", "background_color": "#eef1fa", "theme_color": "#20205f",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
    ]})
assets = {}
for f in ['apple-touch-icon.png', 'icon-192.png', 'icon-512.png']:
    assets['/' + f] = base64.b64encode(open(os.path.join(D, f), 'rb').read()).decode()
w = rd('worker.tpl.js')
w = w.replace('__HTML__', json.dumps(html)).replace('__ADMIN__', json.dumps(rd('admin.html')))
w = w.replace('__SW__', json.dumps(rd('sw.js'))).replace('__MANIFEST__', json.dumps(manifest)).replace('__ASSETS__', json.dumps(assets))
open(os.path.join(OUT, 'royals-stats-worker.js'), 'w', encoding='utf-8').write(w)
for n in ['royals-attack-stats.html', 'royals-stats-update.html', 'royals-stats-worker.js']:
    print(n, os.path.getsize(os.path.join(OUT, n)))
