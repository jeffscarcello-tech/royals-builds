import json, time, base64, sys
import numpy as np, cv2
from playwright.sync_api import sync_playwright
URL='http://localhost:8787/'
F=0
def chk(n,c):
    global F
    print(('PASS ' if c else 'FAIL ')+n)
    if not c: F+=1
MOCK='''window.__shares=[];window.__canFiles=true;
navigator.canShare=function(d){return !!(d&&d.files&&window.__canFiles)};
navigator.share=async function(d){window.__shares.push({text:d.text||null,url:d.url||null,title:d.title||null,files:d.files?d.files.map(f=>({name:f.name,type:f.type,size:f.size})):null});};'''
def wait_for(pg,js,t=8):
    end=time.time()+t
    while time.time()<end:
        if pg.evaluate(js): return True
        time.sleep(.2)
    return False
with sync_playwright() as p:
    b=p.chromium.launch()
    for W,H in ((390,844),(1280,900)):
        tag=f'[{W}] '
        ctx=b.new_context(viewport={'width':W,'height':H},accept_downloads=True)
        ctx.add_init_script(MOCK)
        pg=ctx.new_page();errs=[]
        pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.goto(URL)
        # finish a game: the paper-sheet game plus set scores
        pg.evaluate("()=>{S.tab='s';save();render()}")
        pg.click('[data-act=sample]')
        pg.evaluate(f"()=>openGame('{'sample-nov2-2026'}','r')")
        pg.evaluate("()=>{S.tab='s';save();render()}")
        for i,(a,c) in enumerate([(25,21),(22,25),(25,19),(25,17)]):
            pg.click('[data-act=setadd]')
            pg.fill(f'.setin[data-i="{i}"][data-k="0"]',str(a))
            pg.fill(f'.setin[data-i="{i}"][data-k="1"]',str(c))
        chk(tag+'set scores saved',pg.evaluate("JSON.stringify(S.games.find(g=>g.id===S.gid).sets)")=='[[25,21],[22,25],[25,19],[25,17]]')
        chk(tag+'no overflow on sheet',pg.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        if W==390: pg.screenshot(path='t4_sheet.png')
        # picture
        pg.click('[data-act=fpic][data-id=cur]')
        ok=wait_for(pg,"(()=>{const c=document.getElementById('picCv');if(!c)return false;const d=c.getContext('2d').getImageData(500,5,1,1).data;return d[0]>240&&d[1]>180&&d[2]<90})()")
        chk(tag+'picture drawn (accent bar)',ok)
        chk(tag+'picture is 1080x1350',pg.evaluate("[picCv.width,picCv.height].join()")=='1080,1350')
        if W==390:
            url=pg.evaluate("picCv.toDataURL('image/png')")
            open('t4_picture.png','wb').write(base64.b64decode(url.split(',')[1]))
            pg.screenshot(path='t4_picsheet.png')
        pg.click('[data-act=pshare]')
        wait_for(pg,"window.__shares.length>0")
        s=pg.evaluate("window.__shares.pop()")
        chk(tag+'picture shared as png file',s and s['files'] and s['files'][0]['name']=='royals-Royals-vs-Calvin-Christian-2026-11-02.png' and s['files'][0]['type']=='image/png' and s['files'][0]['size']>20000)
        chk(tag+'picture share text is first line',s and s['text']=='FINAL: Royals 3, Calvin Christian 1 (Nov 2)')
        pg.evaluate("window.__canFiles=false")
        with pg.expect_download() as d: pg.click('[data-act=pshare]')
        chk(tag+'picture download fallback',d.value.suggested_filename.endswith('.png'))
        pg.click('[data-act=ptext]')
        wait_for(pg,"window.__shares.length>0")
        s=pg.evaluate("window.__shares.pop()")
        chk(tag+'text summary',s and s['text'].startswith('FINAL: Royals 3, Calvin Christian 1') and 'Sets: 25-21, 22-25, 25-19, 25-17' in s['text'] and 'Kill %' in s['text'])
        pg.click('#shpanel [data-act=shclose]')
        # recap
        pg.click('[data-act=frecap][data-id=cur]')
        t1=pg.input_value('#rcBox')
        chk(tag+'recap emoji start/end',t1.startswith('🏐') and t1.rstrip()[-1] in '💙👑💜🙌💪')
        chk(tag+'recap uses real result',('3–1' in t1) and 'Calvin Christian' in t1)
        pg.click('[data-act=ragain]');t2=pg.input_value('#rcBox')
        chk(tag+'write it a different way changes it',t2!=t1)
        pg.click('[data-act=rshare]');wait_for(pg,"window.__shares.length>0")
        chk(tag+'recap shared',pg.evaluate("window.__shares.pop().text")==t2)
        pg.click('#shpanel [data-act=shclose]')
        # spreadsheet
        with pg.expect_download() as d: pg.click('[data-act=fcsv][data-id=cur]')
        csv=open(d.value.path(),encoding='utf-8-sig').read()
        chk(tag+'spreadsheet export',d.value.suggested_filename.endswith('.csv') and 'Royals,Pass 3,14,5,2,21,66.7%,42.9%' in csv and 'Calvin Christian,All' in csv and 'Set 4' in csv)
        # link + QR
        pg.click('[data-act=flink][data-id=cur]')
        chk(tag+'link goes live',wait_for(pg,"(document.getElementById('lkStat')||{}).textContent==='Link is live ✓'"))
        link=pg.input_value('#lkUrl')
        chk(tag+'link format',link.startswith('http://localhost:8787/?live=') and len(link.split('=')[1])==6)
        png=pg.locator('.qrbox').screenshot()
        img=cv2.imdecode(np.frombuffer(png,np.uint8),cv2.IMREAD_COLOR)
        img=cv2.copyMakeBorder(img,40,40,40,40,cv2.BORDER_CONSTANT,value=(255,255,255))
        val,_,_=cv2.QRCodeDetector().detectAndDecode(img)
        chk(tag+'QR decodes to the link',val==link)
        if W==390: pg.screenshot(path='t4_link.png')
        pg.click('[data-act=lshare]');wait_for(pg,"window.__shares.length>0")
        chk(tag+'link shared',pg.evaluate("window.__shares.pop().url")==link)
        pg.click('#shpanel [data-act=shclose]')
        # recipient
        rc=b.new_context(viewport={'width':W,'height':H});rp=rc.new_page();rerr=[]
        rp.on('pageerror',lambda e:rerr.append(str(e)))
        rp.goto(link)
        chk(tag+'summary page loads',wait_for(rp,"document.body.innerText.toLowerCase().includes('calvin christian')&&document.querySelector('h1').textContent==='Game Summary'"))
        body=rp.inner_text('body')
        chk(tag+'summary shows result and sets','royals 3, calvin christian 1' in body.lower() and 'SETS' in body.upper())
        chk(tag+'summary read-only (no edit buttons)',rp.locator('[data-act=hit],[data-act=vsave],.nav2 .tab').count()==0 or not rp.is_visible('.nav2'))
        chk(tag+'summary no overflow',rp.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        chk(tag+'get app link',rp.locator('.vfoot a').count()==1)
        if W==390: rp.screenshot(path='t4_summary.png',full_page=True)
        # edit -> link updates
        before=rp.evaluate("VIEW.atk[3].k")
        pg.evaluate("()=>{S.tab='r';render()}")
        pg.click('[data-act=hit][data-d="atk|r|3|k"]') if pg.locator('[data-act=hit][data-d="atk|r|3|k"]').count() else pg.evaluate("()=>{bump('atk|r|3|k',1)}")
        time.sleep(3.5)
        rp.evaluate("livePoll()");
        chk(tag+'edit shows up on the link',wait_for(rp,f"VIEW.atk&&VIEW.atk[3].k==={before+1}"))
        # offline then back online
        ctx.set_offline(True)
        pg.evaluate("()=>bump('atk|r|3|k',1)")
        time.sleep(2.5)
        chk(tag+'offline: waits',pg.evaluate("S.links[S.gid].dirty===true"))
        ctx.set_offline(False)
        pg.evaluate("window.dispatchEvent(new Event('online'))")
        chk(tag+'back online: sends',wait_for(pg,"S.links[S.gid].dirty===false&&!LQ.busy",10))
        rp.evaluate("livePoll()")
        chk(tag+'link has offline edit',wait_for(rp,f"VIEW.atk[3].k==={before+2}"))
        # code taken -> new code
        old=pg.evaluate("S.links[S.gid].code")
        pg.evaluate("()=>{const L=S.links[S.gid];L.key='ffffffffffffffffffffffffffffffff';L.h='';L.dirty=true;liveKick(0)}")
        chk(tag+'403 makes a new code',wait_for(pg,f"S.links[S.gid].code!=='{old}'&&S.links[S.gid].rev>0&&!S.links[S.gid].dirty",10))
        newlink='http://localhost:8787/?live='+pg.evaluate("S.links[S.gid].code")
        # stop sharing
        pg.evaluate("()=>{S.tab='s';render()}")
        pg.click('[data-act=flink][data-id=cur]')
        chk(tag+'reopened link keeps code',pg.input_value('#lkUrl')==newlink)
        pg.click('[data-act=lstop]');pg.click('[data-act=lstop]')
        chk(tag+'stop sharing sends delete',wait_for(pg,"S.liveDel.length===0&&!S.links[S.gid]",10))
        r2=rc.new_page();r2.goto(newlink)
        chk(tag+'stopped link is gone',wait_for(r2,"document.body.innerText.includes('no longer available')"))
        r2.goto('http://localhost:8787/?live=ZZZZZZ')
        chk(tag+'unknown code message',wait_for(r2,"document.body.innerText.includes('no longer available')"))
        # Games card has the four buttons
        pg.evaluate("()=>{S.tab='g';render()}")
        chk(tag+'games card buttons',pg.locator('.card .fin [data-act=fpic]').count()>=1 and pg.locator('.card .fin [data-act=flink]').count()>=1)
        chk(tag+'games card shows sets',pg.locator('.card .tbl td.w').count()>0)
        chk(tag+'no overflow games',pg.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        if W==390: pg.screenshot(path='t4_games.png')
        chk(tag+'version shown matches build',pg.evaluate("VERSION")=='2026-11-21.2')
        chk(tag+'no page errors',not errs and not rerr)
        if errs or rerr: print(errs,rerr)
        rc.close();ctx.close()
    b.close()
print('FAILS:',F)
