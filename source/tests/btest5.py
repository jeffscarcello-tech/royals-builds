import json, time
from playwright.sync_api import sync_playwright
URL='http://localhost:8787/'
VER=json.load(open('/home/claude/royals/version.json'))['build']
F=0
def chk(n,c):
    global F
    print(('PASS ' if c else 'FAIL ')+n)
    if not c: F+=1
def errs(pg,k='r'): return pg.evaluate(f"(()=>{{const T=S.t['{k}'];const e=errTotals(T.atk,T.players,'{k}'==='r'?S.missed:S.missedO);return [e.t,e.h,e.s,e.a]}})()")
def nowide(pg): return pg.evaluate('document.documentElement.scrollWidth<=innerWidth')
LEGACY={"opp":"Old Rivals","date":"2026-10-20","t":{"r":{"atk":{"3":{"k":2,"e":1,"pc":0},"2":{"k":0,"e":0,"pc":0},"1":{"k":0,"e":0,"pc":0}},"players":[{"id":"a","name":"Aedyn","c":[1,1,0,1]}]},"o":{"atk":{"3":{"k":0,"e":0,"pc":0},"2":{"k":0,"e":0,"pc":0},"1":{"k":0,"e":0,"pc":0}},"players":[]}},
  "missed":2,"missedO":0,"tab":"g","fix":True,"hist":[{"d":"miss|r","delta":1}],"gid":"g2",
  "games":[{"id":"g1","opp":"First Foe","date":"2026-10-10","atk":{"3":{"k":3,"e":1,"pc":1},"2":{"k":0,"e":0,"pc":0},"1":{"k":0,"e":0,"pc":0}},"players":[{"name":"Sam","c":[2,0,0,0]}],"missed":1},
           {"id":"g2","opp":"Old Rivals","date":"2026-10-20","atk":{"3":{"k":2,"e":1,"pc":0},"2":{"k":0,"e":0,"pc":0},"1":{"k":0,"e":0,"pc":0}},"players":[{"name":"Aedyn","c":[1,1,0,1]}],"missed":2,"missedO":0,"o":{"atk":{"3":{"k":0,"e":0,"pc":0},"2":{"k":0,"e":0,"pc":0},"1":{"k":0,"e":0,"pc":0}},"players":[]}}]}
with sync_playwright() as p:
    b=p.chromium.launch()
    for W,H in ((390,844),(1280,900)):
        T=f'[{W}] '
        ctx=b.new_context(viewport={'width':W,'height':H},accept_downloads=True,has_touch=False)
        pg=ctx.new_page();E=[]
        pg.on('pageerror',lambda e:E.append(str(e)))
        pg.goto(URL)
        chk(T+'opens on Games',pg.inner_text('h1').lower()=='games' and 'no games yet' in pg.inner_text('#app').lower())
        chk(T+'version visible',pg.inner_text('#verTag')=='v '+VER)
        chk(T+'bottom nav Games/Season/Settings',pg.locator('#bnav .tab').all_inner_texts()==['Games','Season','Settings'] or [x.upper() for x in pg.locator('#bnav .tab').all_inner_texts()]==['GAMES','SEASON','SETTINGS'])
        # new game
        pg.click('[data-act=newgame]');pg.fill('#gfOpp','Calvin Christian');pg.fill('#gfDate','2026-11-02');pg.click('#gfGo')
        chk(T+'new game opens game screen',pg.is_visible('#gameHd') and not pg.is_visible('#appHd') and pg.inner_text('#gTitle').lower()=='calvin christian')
        chk(T+'game tabs Royals/Opponent/Summary',[x.lower() for x in pg.locator('#bnav .tab').all_inner_texts()]==['royals','calvin christian','summary'])
        chk(T+'roster players in new game',pg.evaluate("S.t.r.players.map(p=>p.name).join()")=='Aedyn,Sam,AMC')
        chk(T+'started game is saved before any tap',pg.evaluate("S.games.length")==1)
        for d in ['atk|r|3|e','atk|r|3|e','atk|r|2|k','miss|r','miss|r','miss|r']:
            pg.click(f'[data-act=hit][data-d="{d}"]') if pg.locator(f'[data-act=hit][data-d="{d}"]').count() else pg.click(f'[data-d="{d}"]')
        pid=pg.evaluate("S.t.r.players[0].id")
        pg.click(f'[data-act=hit][data-d="pass|r|{pid}|3"]')
        chk(T+'royals errors 6 = 2+3+1',errs(pg)==[6,2,3,1])
        # long press takes one away
        sel='[data-act=hit][data-d="atk|r|3|e"]';pg.locator(sel).scroll_into_view_if_needed();time.sleep(.2);bx=pg.locator(sel).bounding_box()
        pg.mouse.move(bx['x']+bx['width']/2,bx['y']+bx['height']/2);pg.mouse.down();time.sleep(0.9);pg.mouse.up()
        time.sleep(0.2)
        chk(T+'hold takes one away (no extra add)',pg.evaluate("S.t.r.atk[3].e")==1)
        pg.click('[data-act=undo]')
        chk(T+'undo puts it back',pg.evaluate("S.t.r.atk[3].e")==2)
        # opponent
        pg.click('#bnav [data-tab=o]')
        pg.click('[data-act=add][data-tk=o]')
        oid=pg.evaluate("S.t.o.players[0].id")
        for d in ['atk|o|1|e','atk|o|1|e','miss|o','miss|o',f'pass|o|{oid}|3']:
            pg.click(f'[data-d="{d}"]')
        chk(T+'opponent errors 5 = 2+2+1 '+str(errs(pg,'o')),errs(pg,'o')==[5,2,2,1])
        chk(T+'no overflow on team tab',nowide(pg))
        # edit game from header
        pg.click('[data-act=editgame]');pg.fill('#gfOpp','Calvin Christian Collegiate');pg.click('#gfGo')
        chk(T+'edit game renames header and tab',pg.inner_text('#gTitle').lower()=='calvin christian collegiate' and 'collegiate' in pg.locator('#bnav [data-tab=o]').inner_text().lower())
        # back to list
        pg.click('[data-act=home]')
        chk(T+'list shows game in progress',pg.locator('.glist .gr').count()==1 and 'in progress' in pg.locator('.glist .chip').first.inner_text().lower())
        chk(T+'current game highlighted',pg.locator('.glist .gr.cur').count()==1)
        chk(T+'no overflow on games list',nowide(pg))
        # second game, then open the first again
        pg.click('[data-act=newgame]');pg.fill('#gfOpp','Westgate');pg.fill('#gfDate','2026-11-09');pg.click('#gfGo')
        chk(T+'second game starts at 0',errs(pg)==[0,0,0,0])
        pg.click('[data-act=hit][data-d="atk|r|3|k"]')
        pg.click('[data-act=home]')
        names=[x.lower() for x in pg.locator('.glist .gm2 b').all_inner_texts()]
        chk(T+'newest game first',len(names)==2 and 'westgate' in names[0])
        pg.locator('.glist .gr').nth(1).click()
        chk(T+'opening older game restores it',pg.inner_text('#gTitle').lower()=='calvin christian collegiate' and errs(pg)==[6,2,3,1] and errs(pg,'o')==[5,2,2,1])
        # reload opens straight into the in-progress game
        pg.click('[data-d="miss|r"]')
        pg.reload()
        chk(T+'reload reopens the game in progress',pg.is_visible('#gameHd') and errs(pg)[0]==7)
        # summary: sets, finish, share menu
        pg.click('#bnav [data-tab=s]')
        for i,(a,c) in enumerate([(25,20),(25,22),(18,25),(25,19)]):
            pg.click('[data-act=setadd]');pg.fill(f'.setin[data-i="{i}"][data-k="0"]',str(a));pg.fill(f'.setin[data-i="{i}"][data-k="1"]',str(c))
        pg.click('[data-act=finish]')
        chk(T+'finish marks final and opens Share menu',pg.evaluate("S.final")==True and pg.is_visible('#shwrap') and pg.locator('#shpanel .opt').count()==5)
        chk(T+'header says Final W 3–1','final w 3–1' in pg.inner_text('#gSub').lower())
        if W==390: pg.screenshot(path='t5_sharemenu.png')
        pg.click('#shpanel [data-act=fpic]')
        chk(T+'picture from Share menu',pg.locator('#picCv').count()==1)
        pg.click('#shpanel [data-act=shclose]')
        chk(T+'summary shows result',('royals 3, calvin christian collegiate 1' in pg.inner_text('#app').lower()))
        chk(T+'summary has both full sheets','total errors: 7' in pg.inner_text('#app').lower() and 'total errors: 5' in pg.inner_text('#app').lower())
        chk(T+'no overflow on summary',nowide(pg))
        if W==390: pg.screenshot(path='t5_summary.png')
        pg.click('[data-act=home]')
        chk(T+'list chip W 3–1',any('w 3–1' in t.lower() for t in pg.locator('.glist .chip').all_inner_texts()))
        # game menu: delete + undo
        pg.locator('.glist .more').nth(0).click()
        chk(T+'game menu',pg.locator('#shpanel [data-act=gdel]').count()==1)
        pg.click('#shpanel [data-act=gdel]')
        chk(T+'deleted from list',pg.locator('.glist .gr').count()==1)
        pg.click('#toast [data-act=toastundo]')
        chk(T+'undo delete restores it',pg.locator('.glist .gr').count()==2)
        # season
        pg.click('#bnav [data-v=season]')
        zt=pg.inner_text('#app').lower()
        chk(T+'season record 1–0 and sets 3–1','record' in zt and '1–0' in zt and '3–1' in zt)
        chk(T+'season errors line','hitting (' in zt)
        chk(T+'trend charts',pg.locator('svg.chart').count()==3)
        pg.click('[data-act=sfilt][data-v="5"]')
        chk(T+'last 5 filter',pg.evaluate("S.seasonF")=='5' and 'last 5 games' in pg.inner_text('#app').lower())
        chk(T+'no overflow on season',nowide(pg))
        if W==390: pg.screenshot(path='t5_season.png')
        # settings: roster, theme, version
        pg.click('#bnav [data-v=settings]')
        pg.click('[data-act=rosadd]');pg.locator('.rosin').last.fill('Zoe')
        pg.click('[data-act=settheme][data-v=dark]')
        chk(T+'dark theme',pg.evaluate("document.documentElement.getAttribute('data-theme')")=='dark')
        chk(T+'settings shows version',VER in pg.inner_text('#app'))
        chk(T+'no overflow on settings',nowide(pg))
        if W==390: pg.screenshot(path='t5_settings_dark.png',full_page=True)
        pg.click('[data-act=settheme][data-v=auto]')
        pg.click('#bnav [data-v=home]');pg.click('[data-act=newgame]')
        chk(T+'form lists roster with new player','Zoe' in pg.inner_text('#shpanel'))
        pg.fill('#gfOpp','Roster Check');pg.click('#gfGo')
        chk(T+'new game uses updated roster',pg.evaluate("S.t.r.players.map(p=>p.name).join()")=='Aedyn,Sam,AMC,Zoe')
        chk(T+'no page errors',not E)
        if E: print(E)
        ctx.close()
    # older saved data still loads
    ctx=b.new_context(viewport={'width':390,'height':844});pg=ctx.new_page();E=[]
    pg.on('pageerror',lambda e:E.append(str(e)))
    pg.goto(URL);pg.evaluate("d=>{localStorage.setItem('royals-attack-stats-v1',JSON.stringify(d))}",LEGACY);pg.reload()
    chk('legacy: opens into its game in progress',pg.is_visible('#gameHd') and errs(pg)==[4,1,2,1])
    chk('legacy: fix mode is off',pg.evaluate("S.fix")==False)
    pg.click('[data-act=undo]')
    chk('legacy: undo of old missed serve',errs(pg)==[3,1,1,1])
    pg.click('[data-act=home]')
    chk('legacy: both games listed',pg.locator('.glist .gr').count()==2)
    pg.locator('.glist .gr').nth(1).click()
    pg.click('#bnav [data-tab=s]')
    chk('legacy: old game summary says opponent not saved' ,'opponent' in pg.inner_text('#app').lower())
    pg.click('#bnav [data-tab=o]')
    chk('legacy: can add opponent stats',pg.locator('[data-act=add][data-tk=o]').count()==1)
    for w in (360,320):
        pg.set_viewport_size({'width':w,'height':800})
        for v in ('home','season','settings'):
            pg.evaluate(f"()=>{{S.view='{v}';render()}}");chk(f'legacy: no overflow {v} at {w}',nowide(pg))
        pg.evaluate("()=>{S.view='game';S.tab='s';render()}");chk(f'legacy: no overflow summary at {w}',nowide(pg))
        pg.evaluate("()=>{S.tab='r';render()}");chk(f'legacy: no overflow team at {w}',nowide(pg))
    chk('legacy: no page errors',not E)
    if E: print(E)
    b.close()
print('FAILS:',F)
