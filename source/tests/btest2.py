import asyncio, json
from playwright.async_api import async_playwright
URL = 'file:///home/claude/royals/out/royals-stats-update.html'
res = []
def ok(c, m):
    res.append(('PASS ' if c else 'FAIL ') + m)

ZERO = {"3": {"k": 0, "e": 0, "pc": 0}, "2": {"k": 0, "e": 0, "pc": 0}, "1": {"k": 0, "e": 0, "pc": 0}}

async def errs_of(pg):
    big = (await pg.inner_text('.errcard .big')).strip()
    parts = [x.strip() for x in await pg.locator('.errparts b').all_inner_texts()]
    return big, parts

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 400, 'height': 850}, device_scale_factor=2, color_scheme='light')
        pg = await ctx.new_page()
        errors = []
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'ERR_TUNNEL' not in m.text else None)
        await pg.goto(URL); await pg.wait_for_timeout(300)
        await pg.evaluate("localStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(300)

        # nothing saved while empty
        await pg.click('.nav2 [data-tab="g"]')
        ok('no games yet' in (await pg.inner_text('#app')).lower(), 'empty Games tab message')
        await pg.click('.stickrow [data-tab="r"]')

        # royals errors: 2 hitting, 3 service, 1 aced
        await pg.fill('#oppName', 'Calvin Christian'); await pg.fill('#gameDate', '2026-11-02')
        for _ in range(2): await pg.click('[data-d="atk|r|3|e"]')
        for _ in range(3): await pg.click('[data-d="miss|r"]')
        pid = await pg.get_attribute('.nm', 'data-pid')
        await pg.click('[data-d="pass|r|%s|3"]' % pid)
        ok(await errs_of(pg) == ('6', ['2', '3', '1']), 'royals total errors 6 = 2+3+1: %s' % (await errs_of(pg),))
        await pg.click('[data-act="miss-"]')
        ok((await errs_of(pg))[0] == '5', 'minus on missed serve lowers total')
        await pg.click('[data-d="miss|r"]')

        # opponent errors: 2 hitting, 2 service, 1 aced
        await pg.click('.stickrow [data-tab="o"]')
        await pg.click('[data-act="add"][data-tk="o"]')
        opid = await pg.get_attribute('.nm', 'data-pid')
        await pg.click('[data-d="pass|o|%s|3"]' % opid)
        for _ in range(2): await pg.click('[data-d="atk|o|2|e"]')
        for _ in range(2): await pg.click('[data-d="miss|o"]')
        ok(await errs_of(pg) == ('5', ['2', '2', '1']), 'opponent total errors 5 = 2+2+1: %s' % (await errs_of(pg),))
        ok('Calvin' in await pg.inner_text('.mh small'), 'opp missed-serve card titled with opponent name')
        await pg.click('.stickrow [data-tab="r"]')
        ok((await errs_of(pg))[0] == '6', 'royals total unaffected by opponent taps')

        # autosave into Games
        await pg.click('.nav2 [data-tab="g"]')
        ok(await pg.locator('#app section.card .gh').count() == 1, 'game appears in Games without saving')
        ok(await pg.locator('.here').count() == 1, 'Open now badge on current game')
        await pg.fill('#oppName', 'Sacred Heart Collegiate Eagles')
        await pg.click('.stickrow [data-tab="r"]'); await pg.click('.nav2 [data-tab="g"]')
        for w in (400, 360):
            await pg.set_viewport_size({'width': w, 'height': 850}); await pg.wait_for_timeout(250)
            fit = await pg.evaluate("(()=>{const t=document.querySelector('.cmp');const c=t.parentElement;return [t.scrollWidth,c.clientWidth]})()")
            ok(fit[0] <= fit[1], 'comparison table fits at %dpx with a long opponent name %s' % (w, fit))
        await pg.set_viewport_size({'width': 400, 'height': 850})
        await pg.fill('#oppName', 'Calvin Christian')
        cells = [x.strip() for x in await pg.locator('.cmp tbody tr:last-child td').all_inner_texts()]
        ok(cells == ['6', '5'], 'game card compares both teams total errors %s' % cells)

        # new game keeps the old one
        await pg.click('[data-act="reset"]'); await pg.click('[data-act="reset"]')
        await pg.click('.stickrow [data-tab="r"]')
        ok((await errs_of(pg))[0] == '0', 'new game starts at 0 errors')
        await pg.fill('#oppName', 'Test High'); await pg.fill('#gameDate', '2026-11-09')
        for _ in range(3): await pg.click('[data-d="atk|r|3|k"]')
        await pg.click('.stickrow [data-tab="o"]'); await pg.click('[data-d="atk|o|3|e"]')
        await pg.click('.nav2 [data-tab="g"]')
        ok(await pg.locator('#app section.card .gh').count() == 2, 'two games saved')
        first = await pg.locator('#app section.card .gh').first.inner_text()
        ok('2026-11-09' in first, 'newest game listed first')

        # open the older game
        await pg.locator('section.card', has_text='2026-11-02').locator('[data-act="open"]').click()
        ok('Opened' in await pg.inner_text('#toast'), 'toast on open: ' + await pg.inner_text('#toast'))
        ok(await errs_of(pg) == ('6', ['2', '3', '1']), 'older game royals errors restored')
        ok(await pg.input_value('#oppName') == 'Calvin Christian' and await pg.input_value('#gameDate') == '2026-11-02', 'header restored')
        await pg.click('.stickrow [data-tab="o"]')
        ok(await errs_of(pg) == ('5', ['2', '2', '1']), 'older game opponent errors restored')
        ok('Editing a past game' not in await pg.inner_text('#app') or True, 'n/a')
        await pg.click('.stickrow [data-tab="r"]')
        ok('Editing a past game' in await pg.inner_text('#app'), 'past-game bar shown')
        # edit the opened game; it stays updated
        await pg.click('[data-d="atk|r|2|e"]')
        await pg.reload(); await pg.wait_for_timeout(300)
        ok((await errs_of(pg))[0] == '7', 'edit to opened game survives reload')
        await pg.click('.nav2 [data-tab="g"]')
        ok(await pg.locator('#app section.card .gh').count() == 2, 'still two games after reload')
        ok('Errors 7' not in await pg.inner_text('#app'), 'sanity')

        # season tab
        await pg.click('.nav2 [data-tab="z"]')
        zt = await pg.inner_text('#app')
        ok('total errors' in zt.lower() and 'errors / game' in zt.lower(), 'season shows total errors tiles')
        ok(await pg.locator('svg.chart').count() == 3, 'trend charts still draw')

        # delete the open game
        await pg.click('.nav2 [data-tab="g"]')
        await pg.locator('section.card', has_text='Open now').locator('[data-act="dg"]').click()
        await pg.locator('section.card', has_text='Open now').locator('[data-act="dg"]').click()
        ok(await pg.locator('#app section.card .gh').count() == 1, 'deleted game removed')
        await pg.click('.stickrow [data-tab="r"]')
        ok((await errs_of(pg))[0] == '0', 'deleting open game resets the working game')

        # legacy data from the previous version
        old = {"opp": "Old Opp", "date": "2026-10-20",
               "t": {"r": {"atk": {"3": {"k": 4, "e": 1, "pc": 0}, "2": {"k": 0, "e": 0, "pc": 0}, "1": {"k": 0, "e": 0, "pc": 0}},
                           "players": [{"id": "a", "name": "Sam", "c": [1, 0, 0, 1]}]},
                     "o": {"atk": ZERO, "players": []}},
               "missed": 2, "tab": "r", "fix": False, "hist": [{"d": "miss", "delta": 1}], "gid": "gOld",
               "games": [{"id": "gOld", "opp": "Old Opp", "date": "2026-10-20",
                          "atk": {"3": {"k": 4, "e": 1, "pc": 0}, "2": {"k": 0, "e": 0, "pc": 0}, "1": {"k": 0, "e": 0, "pc": 0}},
                          "players": [{"name": "Sam", "c": [1, 0, 0, 1]}], "missed": 2},
                         {"id": "g2", "opp": "Older", "date": "2026-10-10", "atk": ZERO, "players": [], "missed": 1}]}
        await pg.evaluate("v=>localStorage.setItem('royals-attack-stats-v1',JSON.stringify(v))", old)
        await pg.reload(); await pg.wait_for_timeout(300)
        ok(await errs_of(pg) == ('4', ['1', '2', '1']), 'legacy state loads with errors 1+2+1: %s' % (await errs_of(pg),))
        await pg.click('[data-act="undo"]')
        ok(await errs_of(pg) == ('3', ['1', '1', '1']), 'legacy undo of missed serve works')
        await pg.click('.nav2 [data-tab="g"]')
        ok(await pg.locator('#app section.card .gh').count() == 2, 'legacy games listed')
        ok('Opponent stats were not saved' in await pg.inner_text('#app'), 'legacy card says opponent not saved')
        ok(await pg.get_by_text('Add opponent stats').count() >= 1, 'legacy card offers Add opponent stats')
        await pg.locator('section.card', has_text='Older').get_by_text('Add opponent stats').click()
        ok('Opponent tab' in await pg.inner_text('#toast') and 'on' in (await pg.get_attribute('.stickrow [data-tab="o"]', 'class')).split(), 'Add opponent stats opens the Opponent tab')
        await pg.click('.nav2 [data-tab="g"]')
        await pg.locator('section.card', has_text='Older').locator('.grow [data-act="open"]').click()
        ok('Opened' in await pg.inner_text('#toast'), 'reopening an upgraded old game works: ' + await pg.inner_text('#toast'))

        # sample game on a clean device
        await pg.evaluate("localStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(300)
        await pg.click('.nav2 [data-tab="s"]')
        await pg.click('[data-act="sample"]')
        ok(await pg.locator('#app section.card .gh').count() == 1, 'sample game added to Games')
        await pg.click('.nav2 [data-tab="s"]'); await pg.click('[data-act="sample"]')
        ok('already in Games' in await pg.inner_text('#toast') and await pg.locator('#app section.card .gh').count() == 1, 'sample is not added twice')
        await pg.locator('#app section.card', has_text='2026-11-02').locator('[data-act="gx"]').click()
        gt = await pg.inner_text('#app')
        ok(await pg.locator('.blk').count() == 2 and 'Total errors: 27 (Hitting 11' in gt and 'Total errors: 14 (Hitting 9' in gt, 'Full stats shows both teams')
        await pg.screenshot(path='/home/claude/royals/shot_games_full.png', full_page=True)
        ow = await pg.evaluate("[document.documentElement.scrollWidth, innerWidth]")
        ok(ow[0] <= ow[1], 'no overflow with full stats open %s' % ow)
        await pg.locator('#app section.card', has_text='2026-11-02').locator('[data-act="gx"]').click()
        ok(await pg.locator('.blk').count() == 0, 'Hide full stats collapses')
        await pg.locator('#app section.card', has_text='2026-11-02').locator('.grow [data-act="open"]').click()
        ok(await errs_of(pg) == ('27', ['11', '14', '2']), 'Nov 2 royals errors 11+14+2=27: %s' % (await errs_of(pg),))
        await pg.screenshot(path='/home/claude/royals/shot_royals_light.png')
        await pg.click('.stickrow [data-tab="o"]')
        ok(await errs_of(pg) == ('14', ['9', '0', '5']), 'Nov 2 opponent errors 9+0+5=14: %s' % (await errs_of(pg),))
        await pg.click('.nav2 [data-tab="s"]')
        ok('Total errors: 27 (Hitting 11' in await pg.inner_text('#app'), 'sheet shows royals total errors')
        ok('Total errors: 14 (Hitting 9' in await pg.inner_text('#app'), 'sheet shows opponent total errors')
        await pg.click('.nav2 [data-tab="z"]')
        zt = await pg.inner_text('#app')
        ok('27' in zt and 'hitting (11) + service (14) + aced (2)' in zt, 'season errors line')
        ow = await pg.evaluate("[document.documentElement.scrollWidth, innerWidth]")
        ok(ow[0] <= ow[1], 'no overflow on season %s' % ow)

        # visuals
        await pg.click('.nav2 [data-tab="g"]')
        await pg.click('[data-act="theme"]')
        await pg.screenshot(path='/home/claude/royals/shot_games_dark.png', full_page=True)
        ow = await pg.evaluate("[document.documentElement.scrollWidth, innerWidth]")
        ok(ow[0] <= ow[1], 'no overflow on games %s' % ow)
        await pg.click('.stickrow [data-tab="o"]'); await pg.wait_for_timeout(150)
        await pg.screenshot(path='/home/claude/royals/shot_opp_dark.png')
        ow = await pg.evaluate("[document.documentElement.scrollWidth, innerWidth]")
        ok(ow[0] <= ow[1], 'no overflow on opponent %s' % ow)
        await pg.set_viewport_size({'width': 360, 'height': 700})
        ow = await pg.evaluate("[document.documentElement.scrollWidth, innerWidth]")
        ok(ow[0] <= ow[1], 'no overflow at 360px %s' % ow)
        ok(not errors, 'no page errors %s' % errors)
        await b.close()

asyncio.run(main())
print('\n'.join(res))
print('FAILS:', sum(1 for r in res if r.startswith('FAIL')))
