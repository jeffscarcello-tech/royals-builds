import json,sys
from playwright.sync_api import sync_playwright
URL='file:///home/claude/royals/out/royals-attack-stats.html'
F=0
def chk(n,c):
    global F
    print(('PASS ' if c else 'FAIL ')+n)
    if not c:F+=1
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':400,'height':800},permissions=['clipboard-read','clipboard-write'])
    pg=ctx.new_page();errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(URL)
    # roundtrip incl. unicode + XSS name
    r=pg.evaluate('''()=>{
      const mk=()=>({3:{k:5,e:1,pc:2},2:{k:3,e:2,pc:1},1:{k:0,e:1,pc:0}});
      const g={id:'abc123',opp:'Ré<img src=x onerror=window.__x=1>🏐',date:'2026-11-18',atk:mk(),players:[{name:'Zoë <b>',c:[4,3,2,1]}],missed:3,missedO:2,o:{atk:mk(),players:[{name:'Opp1',c:[1,2,3,4]}]}};
      const u=shareUrl(g);const h=u.split('#')[1];
      const back=unpackGame(JSON.parse(fromB64(h.slice(2))));
      return {ok:JSON.stringify(back)===JSON.stringify(g),bad:[unpackGame({v:1}),unpackGame(null)].every(x=>x===null),url:u.length}}''')
    chk('pack/unpack roundtrip',r['ok']);chk('invalid rejected',r['bad'])
    # build a game via state, then share from Sheet
    pg.evaluate('''()=>{S.opp='Rivals';S.t.r.atk[3].k=4;S.t.r.atk[3].e=1;S.t.o.atk[3].k=2;S.missed=2;save();render()}''')
    pg.click('text=Sheet') if pg.locator('text=Sheet').count() else None
    pg.evaluate("document.querySelector('[data-act=sharecur]')&&document.querySelector('[data-act=sharecur]').click()")
    chk('share panel opens',pg.is_visible('#shwrap'))
    link=pg.input_value('#shBox')
    chk('link has hash',('#g=' in link))
    pg.screenshot(path='share_panel.png')
    pg.click('[data-act=shtext]')
    chk('text has both teams','ROYALS' in pg.input_value('#shBox') and 'RIVALS' in pg.input_value('#shBox').upper())
    ow=pg.evaluate('document.documentElement.scrollWidth<=innerWidth')
    chk('no overflow 400',ow)
    pg.click('[data-act=shclose]:last-child')
    chk('panel closes',not pg.is_visible('#shwrap'))
    # recipient
    for w in (400,360):
        rc=b.new_context(viewport={'width':w,'height':800});rp=rc.new_page();re_=[]
        rp.on('pageerror',lambda e:re_.append(str(e)))
        rp.goto(URL+'#g='+link.split('#g=')[1])
        txt=rp.inner_text('body').lower()
        chk(f'viewer shows report {w}','game report' in txt and 'rivals' in txt)
        chk(f'viewer no overflow {w}',rp.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        chk(f'viewer did not write storage {w}',rp.evaluate("localStorage.getItem('royals-attack-stats-v1')")is None)
        if w==400:
            rp.screenshot(path='viewer.png',full_page=True)
            rp.click('[data-act=vsave]')
            chk('saved to games',rp.evaluate("JSON.parse(localStorage.getItem('royals-attack-stats-v1')).games.length")==1)
            rp.click('[data-act=vopen]')
            chk('open app leaves viewer','game report' not in rp.inner_text('h1').lower())
        chk(f'no errors {w}',not re_)
        rc.close()
    # garbage hash
    gp=ctx.new_page();gp.goto(URL+'#g=!!notvalid');gp.goto(URL+'#g=AAAA');gp.reload()
    chk('garbage falls back','attack stats' in gp.inner_text('h1').lower())
    # XSS not executed
    xp=ctx.new_page();xp.goto(URL);
    u=xp.evaluate('''()=>{const mk=()=>({3:{k:1,e:0,pc:0},2:{k:0,e:0,pc:0},1:{k:0,e:0,pc:0}});return shareUrl({id:'x1',opp:'<img src=x onerror=window.__x=1>',date:'2026-11-18',atk:mk(),players:[{name:'<b>x',c:[0,0,0,0]}],missed:0})}''')
    xp.goto(u);xp.reload()
    chk('xss not executed',xp.evaluate('window.__x')is None)
    chk('legacy share (no opp) notes it','not saved' in xp.inner_text('body').lower())
    chk('no page errors',not errs)
    b.close()
print('FAILS:',F)
