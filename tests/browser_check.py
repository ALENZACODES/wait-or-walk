"""Real browser check of the page (Playwright, headless Chromium).

Clicks every example button with real mouse input at a phone width (390 px) and a desktop width
(1440 px), checks the ambiguous alert flow, clearing the alert, and the load error retry.
Run: pip install playwright && python3 -m playwright install chromium
     python3 tests/browser_check.py https://alenzacodes.github.io/wait-or-walk/
Set CHROME=/path/to/chrome to use a specific browser binary.
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8080/'
EXPECT = {'Passenger alarm at Union': ('Union', 'low'), 'Person at track level, Kipling': ('Kipling', 'moderate'),
          'Fire investigation, St George': ('St George', 'high'), 'Fire at St George, headed to Dupont': ('St George', 'high')}
fails = []
def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)

with sync_playwright() as p:
    b = p.chromium.launch(**({'executable_path': os.environ['CHROME']} if os.environ.get('CHROME') else {}))
    for w, h in [(390, 844), (1440, 900)]:
        pg = b.new_page(viewport={'width': w, 'height': h}); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('#app:not([hidden])')
        if w < 700:
            check(pg.is_visible('#pct') and pg.locator('#pct').bounding_box()['y'] + pg.locator('#pct').bounding_box()['height'] < h - 40, f'{w}: an example result is visible above the fold')
        buttons = pg.locator('[data-alert]')
        for i in range(buttons.count()):
            btn = buttons.nth(i); label = btn.inner_text()
            btn.scroll_into_view_if_needed(); btn.click(); pg.wait_for_timeout(250)
            check(pg.input_value('#alert') == btn.get_attribute('data-alert'), f'{w}: "{label}" fills the alert box')
            if label in EXPECT:
                st, level = EXPECT[label]
                cls = pg.get_attribute('.result', 'class')
                check(pg.is_visible('#pct') and level in cls and pg.input_value('#station') == st, f'{w}: "{label}" shows a {level} risk number for {st} ({pg.inner_text("#pct")})')
            else:
                check(not pg.is_visible('#callBody') and pg.is_visible('#choice'), f'{w}: "{label}" asks which line before showing a number')
                pg.locator('#choice button').nth(1).click(); pg.wait_for_timeout(200)
                check(pg.is_visible('#pct') and pg.input_value('#line') == 'BD', f'{w}: choosing Line 2 shows a number ({pg.inner_text("#pct")})')
        pg.fill('#alert', 'Line 1: Shuttle buses running between St. George and Union due to a fire investigation.'); pg.wait_for_timeout(200)
        check(not pg.is_visible('#callBody') and pg.locator('#choice button').count() == 2, f'{w}: two stations named asks which one, no number')
        pg.locator('#choice button').nth(0).click(); pg.wait_for_timeout(200)
        check(pg.is_visible('#pct') and pg.input_value('#station') == 'St George', f'{w}: choosing St George shows a number')
        pg.fill('#alert', ''); pg.wait_for_timeout(200)
        check(not pg.is_visible('#callBody') and pg.input_value('#station') == '' and pg.input_value('#group') == '', f'{w}: clearing the alert clears the fields and the number')
        check(pg.locator('#drift').count() == 1, f'{w}: drift readout present in the call card')
        pg.fill('#alert', 'Line 2: Delays at Union due to a medical emergency.'); pg.wait_for_timeout(200)
        check(not pg.is_visible('#callBody') and 'not on Line 2' in pg.inner_text('#empty'), f'{w}: Union with Line 2 gives no number')
        check('Fix the line or station first' in pg.inner_text('#planbOut'), f'{w}: mismatch hides Plan B')
        pg.fill('#alert', 'Line 1: Delays at Eglinton due to a signal problem.'); pg.wait_for_timeout(300)
        check(pg.is_visible('#callBody') and pg.is_visible('#drift') and '%' in pg.inner_text('#drift'), f'{w}: drift readout visible under the call')
        warn = pg.locator('#planbWarn'); lst = pg.locator('#planbOut .planb').first
        check(warn.is_visible() and warn.bounding_box()['y'] < lst.bounding_box()['y'], f'{w}: "might not be running" warning sits above the Plan B list')
        check('LRT (light rail)' in pg.inner_text('#planbOut') and 'Line 5 Eglinton streetcar' not in pg.inner_text('#planbOut'), f'{w}: Line 5 Eglinton shown as LRT')
        check('min walk' in pg.inner_text('#planbOut'), f'{w}: Plan B shows walking time')
        check('Version r7' in pg.inner_text('footer') and 'Not affiliated' in pg.inner_text('footer'), f'{w}: footer shows version r7 and the not affiliated line')
        check(pg.is_visible('#pasteBtn') and 'cannot be read by this page' in pg.inner_text('.pastenote'), f'{w}: paste button and the note about live feeds')
        check(pg.is_visible('#scope') and pg.inner_text('#scope') == 'This predicts a logged service delay category, not how many minutes you personally have left to wait.', f'{w}: card says what the number predicts')
        check(pg.is_visible('.estlab') and 'estimated chance' in pg.inner_text('.estlab').lower() and pg.locator('#bands span').count() == 3, f'{w}: card says Estimated chance and shows 5+, 10+ and 20+')
        check(pg.inner_text('#reconcile').startswith('Why '), f'{w}: card explains the estimate against the raw share for the cause')
        check(pg.is_visible('.safety') and 'follow TTC staff' in pg.inner_text('.safety'), f'{w}: safety line visible')
        check(pg.locator('#pooledTable table').count() == 1 and pg.locator('#decisionTable table').count() == 1 and pg.locator('#simTable table').count() == 1, f'{w}: results, decision value and simulation tables render')
        check(pg.evaluate('document.documentElement.scrollWidth') <= w, f'{w}: no sideways scrolling')
        check(not errs, f'{w}: no script errors {errs}')
        pg.close()
    # Schedule clock checks with a fixed Toronto time
    import re
    def at(iso, w=1280):
        q = b.new_page(viewport={'width': w, 'height': 900}); q.clock.set_fixed_time(iso); q.goto(URL); q.wait_for_selector('#app:not([hidden])')
        q.locator('[data-worked]').click(); q.select_option('#dest', 'Jane'); q.wait_for_timeout(300); return q
    def mins(txt):
        out = []
        for h, m, ap in re.findall(r'(\d{1,2}):(\d{2}) ([ap])\.m\.', txt):
            h = int(h) % 12 + (12 if ap == 'p' else 0); out.append(h * 60 + int(m))
        return out
    q = at('2026-11-16T22:38:00Z')   # Monday 5:38 p.m.
    first = q.locator('#planbOut .planb li', has_text='149 Etobicoke').first.inner_text()
    deps = mins(first.split('Next you can catch:')[1].split('\n')[0]) if 'Next you can catch:' in first else []
    check(deps and deps[0] == 18 * 60 + 7, f'5:38 p.m.: the 5:39 bus 149 is not offered (1 min walk + 1 min to board); first is {deps[:1]}')
    etas = [mins(li.split('By the schedule:')[1])[-1] for li in q.locator('#planbOut .planb li').all_inner_texts() if 'By the schedule:' in li]
    check(len(etas) >= 2 and etas == sorted(etas), f'Plan B entries ordered by estimated arrival {etas}')
    check('By the schedule: at Jane about' in q.inner_text('#planbOut') and 'earliest scheduled arrival first' in q.inner_text('#planbOut'), 'Plan B ranked by scheduled arrival with estimates')
    check('Schedule data ends on Dec 21, 2026' in q.inner_text('#planbClock'), 'schedule end date shown')
    check('Blue Night' not in q.inner_text('#planbOut'), '5:38 p.m.: no Blue Night line in the daytime')
    check(q.inner_text('#mix').startswith('How 23% becomes about 8 minutes') and 'not your remaining wait' in q.inner_text('#suggest'), '5:38 p.m.: the 23% is tied to the 8 minute average, and the comparison says it is not your remaining wait')
    check(q.inner_text('#suggest').startswith('Schedule comparison: waiting looks better') and 'extra minutes by Plan B' in q.inner_text('#suggest'), f'5:38 p.m. Kipling to Jane: wait or switch line compares the best scheduled switch ({q.inner_text("#suggest")[:60]})')
    check(q.locator('#foldTable tr').count() == 5 and q.locator('#policyTable tr').count() == 5 and q.locator('#firstTwoTable table').count() == 2, 'data seen table, decision rule table and Jan to Jun table render')
    q.close()
    q = at('2026-11-16T22:30:00Z')   # Monday 5:30 p.m., the contrasting worked example
    q.locator('[data-contrast]').click(); q.wait_for_timeout(400)
    check(q.input_value('#dest') == 'Dupont' and q.inner_text('#suggest').startswith('Schedule comparison: switching looks better') and '26 Dupont' in q.inner_text('#suggest'), f'contrast example: St George fire, headed to Dupont, switching looks better ({q.inner_text("#suggest")[:90]})')
    q.close()
    for iso, label in [('2026-12-07T17:00:00Z', 'Dec 7 noon'), ('2026-12-20T17:00:00Z', 'Dec 20 noon')]:
        q = at(iso); check('Next you can catch' in q.inner_text('#planbOut'), f'{label}: departures shown'); q.close()
    q = at('2026-11-17T08:00:00Z')   # 3 a.m.
    txt = q.inner_text('#planbOut')
    check('Overnight: Blue Night route 300' in txt, '3 a.m.: Blue Night route 300 line shown overnight')
    check('3:00 a.m.' in q.inner_text('#planbClock') and ('Next you can catch' in txt or 'No departure you can still catch' in txt), '3 a.m.: clock and departures or a clear none message')
    q.close()
    q = at('2026-12-22T17:00:00Z')
    check('Schedule data ends on Dec 21, 2026' in q.inner_text('#planbClock') and 'Today is after that' in q.inner_text('#planbClock') and 'Next you can catch' not in q.inner_text('#planbOut'), 'after Dec 21: clear schedule ended message, no times')
    q.close()
    q = b.new_page(viewport={'width': 1280, 'height': 900}); q.clock.install(time='2026-11-17T04:58:30Z')   # Monday 11:58:30 p.m.
    q.goto(URL); q.wait_for_selector('#app:not([hidden])'); q.locator('[data-worked]').click(); q.wait_for_timeout(300)
    before = q.inner_text('#planbClock'); q.clock.run_for(150000); q.wait_for_timeout(300); after = q.inner_text('#planbClock')
    check('11:58 p.m.' in before and ('12:00 a.m.' in after or '12:01 a.m.' in after), f'Plan B refreshes each minute and across midnight ({before.split("(")[1].split(")")[0]} then {after.split("(")[1].split(")")[0]})')
    q.close()
    pg = b.new_page(viewport={'width': 390, 'height': 844})
    pg.route('**/data/planb.json*', lambda r: r.abort())
    pg.goto(URL); pg.wait_for_selector('#loadError:not([hidden])', timeout=8000)
    check(True, 'load failure shows an error with a retry button')
    pg.unroute('**/data/planb.json*'); pg.click('#retry'); pg.wait_for_selector('#app:not([hidden])', timeout=8000)
    check(True, 'retry loads the page')
    b.close()
print('FAILED: %d' % len(fails) if fails else 'All browser checks passed.')
sys.exit(1 if fails else 0)
