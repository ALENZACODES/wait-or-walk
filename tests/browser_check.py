"""Real browser check of the page (Playwright, headless Chromium).

Clicks every example button with real mouse input at a phone width (390 px) and a desktop width
(1440 px), checks the ambiguous alert flow, clearing the alert, and the load error retry.
Run: pip install playwright && python3 -m playwright install chromium
     python3 tests/browser_check.py https://alenzacodes.github.io/wait-or-walk/
Set CHROME=/path/to/chrome to use a specific browser binary.
Accessibility: set AXE=/path/to/axe.min.js (axe-core, Mozilla Public License 2.0, used unmodified and not stored in this
repo); CI installs it with npm. With REQUIRE_AXE=1 a missing axe-core is a failure.
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
            vb = pg.locator('#verdictShort').bounding_box()
            check(pg.is_visible('#pct') and pg.is_visible('#verdictShort') and vb['y'] + vb['height'] < h - 20, f'{w}: the pre filled example answer (chance and verdict) is visible above the fold')
            hero = pg.inner_text('.lede.hero'); check(pg.is_visible('.lede.hero') and 15 <= len(hero.split()) <= 24, f'{w}: one sentence hero of about 20 words ({len(hero.split())})')
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
        check('Version r9' in pg.inner_text('footer') and 'Not affiliated' in pg.inner_text('footer'), f'{w}: footer shows version r9 and the not affiliated line')
        check(pg.is_visible('#pasteBtn') and 'nothing is sent anywhere' in pg.text_content('.pastenote'), f'{w}: paste button and the privacy note')
        check(pg.is_visible('#scope') and pg.inner_text('#scope') == 'Not the chance your alert causes this delay, or your remaining wait.' and 'among comparable recorded TTC delays' in pg.inner_text('#pctlab'), f'{w}: card says which population the number is about')
        pg.click('.meaning summary'); check('Among comparable recorded TTC delays, the model estimates a' in pg.inner_text('#meaning') and 'not the chance your current alert causes that delay, or your remaining wait' in pg.inner_text('#meaning'), f'{w}: full wording in the card details')
        check(pg.is_visible('.estlab') and 'estimated chance' in pg.inner_text('.estlab').lower() and pg.locator('#bands span').count() == 3, f'{w}: card says Estimated chance and shows 5+, 10+ and 20+')
        check(pg.inner_text('#reconcile').startswith('Why '), f'{w}: card explains the estimate against the raw share for the cause')
        check(pg.is_visible('.safety') and 'follow TTC staff' in pg.inner_text('.safety'), f'{w}: safety line visible')
        check(pg.locator('#pooledTable table').count() == 1 and pg.locator('#decisionTable table').count() == 1 and pg.locator('#simTable table').count() == 1, f'{w}: results, decision value and simulation tables render')
        check(pg.evaluate('document.documentElement.scrollWidth') <= w, f'{w}: no sideways scrolling')
        check(not errs, f'{w}: no script errors {errs}')
        pg.close()
    # Schedule clock checks with a fixed Toronto time
    import re
    KIP = 'Line 2 Bloor-Danforth: Delays at Kipling due to a person at track level.'
    def at(iso, w=1280):   # live time: the rider's own alert, typed in
        q = b.new_page(viewport={'width': w, 'height': 900}); q.clock.set_fixed_time(iso); q.goto(URL); q.wait_for_selector('#app:not([hidden])')
        q.fill('#alert', KIP); q.select_option('#dest', 'Jane'); q.wait_for_timeout(300); return q
    def mins(txt):
        out = []
        for h, m, ap in re.findall(r'(\d{1,2}):(\d{2}) ([ap])\.m\.', txt):
            h = int(h) % 12 + (12 if ap == 'p' else 0); out.append(h * 60 + int(m))
        return out
    q = at('2026-11-16T22:38:00Z')   # Monday 5:38 p.m.
    first = q.locator('#planbOut .planb li', has_text='149 Etobicoke').first.inner_text()
    deps = mins(first.split('Scheduled departures you may be able to catch:')[1].split('\n')[0]) if 'Scheduled departures you may be able to catch:' in first else []
    check(deps and deps[0] == 18 * 60 + 7, f'5:38 p.m.: the 5:39 bus 149 is not offered (1 min walk + 1 min to board); first is {deps[:1]}')
    etas = [mins(li.split('Timetable estimate, not real time:')[1])[-1] for li in q.locator('#planbOut .planb li').all_inner_texts() if 'Timetable estimate, not real time:' in li]
    check(len(etas) >= 2 and etas == sorted(etas), f'Plan B entries ordered by estimated arrival {etas}')
    check('Timetable estimate, not real time: at Jane about' in q.inner_text('#planbOut') and 'earliest scheduled arrival first' in q.inner_text('#planbOut'), 'Plan B ranked by scheduled arrival with estimates')
    check('Schedule data ends on Dec 21, 2026' in q.inner_text('#planbClock'), 'schedule end date shown')
    check('Blue Night' not in q.inner_text('#planbOut'), '5:38 p.m.: no Blue Night line in the daytime')
    check(q.inner_text('#mix').startswith('How 23% becomes about 8 minutes') and 'not your remaining wait' in q.inner_text('#suggest'), '5:38 p.m.: the 23% is tied to the 8 minute average, and the comparison says it is not your remaining wait')
    check(q.inner_text('#suggest').startswith('Schedule comparison: waiting looks better') and 'extra minutes by Plan B' in q.inner_text('#suggest') and 'Assuming the incident has just begun' in q.inner_text('#suggest'), f'5:38 p.m. Kipling to Jane: verdict compares the best scheduled switch, assuming it just began ({q.inner_text("#suggest")[:60]})')
    check(q.is_hidden('#simBanner') and 'Simulated' not in q.inner_text('#planbClock'), '5:38 p.m.: a typed alert uses the live time, not the simulated clock')
    check(q.inner_text('#verdictShort').startswith('Verdict: waiting looks better'), 'the card shows the short verdict')
    check(q.is_visible('#calnote') and q.inner_text('#calnote') == 'The model is calibrated on recorded delay length, not time since the alert.' and q.inner_text('[data-elapsed="5"]') == 'Delay already reached 5 min', 'underway buttons say the delay already reached 5 or 10 minutes, with the calibration note')
    check('Break even: by the timetable switching loses by about' in q.inner_text('#breakeven'), f'waiting verdict shows the break even ({q.inner_text("#breakeven")[:70]})')
    check('can still catch' not in q.inner_text('body') and 'Timetable estimates, not real time.' in q.inner_text('#planbClock'), 'no "can still catch" anywhere; Plan B times labelled timetable estimates')
    check(q.locator('#periodEval tr').count() == 4 and q.text_content('#periodEval').count('Exploratory') == 3, 'each evaluation period shown on its own, marked exploratory')
    check('no rider testing has been done' in q.inner_text('#verdict').lower(), 'the page says plainly that no rider testing has been done')
    # Already underway
    p10 = q.inner_text('#pct'); q.click('[data-elapsed="5"]'); q.wait_for_timeout(200)
    check(q.inner_text('#pct') != p10 and q.locator('#bands span').count() == 2 and 'reached 5' in q.inner_text('#pctlab') and q.inner_text('#suggest').count('About 5 minutes in') == 1 and q.get_attribute('[data-elapsed="5"]', 'aria-pressed') == 'true', f'about 5 minutes in: conditional chance {q.inner_text("#pct")} replaces {p10}, verdict uses the remaining minutes')
    q.click('[data-elapsed="10"]'); q.wait_for_timeout(200)
    check(q.locator('#bands span').count() == 1 and '20 minutes or more in total' in q.inner_text('#pctlab') and 'Already a long delay' in q.inner_text('#advice'), f'about 10 minutes in: chance of 20+ in total ({q.inner_text("#pct")})')
    q.click('[data-elapsed="0"]'); q.wait_for_timeout(200)
    check(q.inner_text('#pct') == p10 and q.locator('#bands span').count() == 3, 'just started goes back to the headline')
    # Planned work: no forecast at all
    q.fill('#alert', 'Line 2 Bloor-Danforth: There is no subway service between Victoria Park and Kennedy stations due to planned track work. Shuttle buses are running.'); q.wait_for_timeout(300)
    check(q.is_hidden('#callBody') and q.inner_text('#empty') == 'This is planned service work. The incident delay model does not apply.' and q.is_hidden('#verdictShort') and '%' not in q.inner_text('#suggest'), 'planned work hides the forecast and says the model does not apply')
    q.fill('#alert', 'Line 1 Yonge-University: Trains are moving slower than usual at Eglinton while we perform track work.'); q.wait_for_timeout(300)
    check(q.is_hidden('#callBody') and 'planned service work' in q.inner_text('#empty') and q.locator('#planbOut .planb').count() >= 1, 'a planned slow zone at one station: no forecast, Plan B still shown')
    check(q.locator('#evidence').count() == 1 and q.get_attribute('#evidence', 'open') is None and q.locator('#robustTable table').count() == 1 and q.locator('#underwayTable tr').count() == 3 and q.locator('#stressTable table').count() == 1, 'evidence sits behind an Evidence section; late bus rule and underway tables render')
    check(q.locator('#foldTable tr').count() == 5 and q.locator('#policyTable tr').count() == 5 and q.locator('#firstTwoTable table').count() == 2, 'data seen table, decision rule table and Jan to Jun table render')
    q.close()
    # Examples run on the simulated clock, so they work after the schedule data ends (Jan 5, 2027)
    for iso, label in [('2026-11-16T15:00:00Z', 'Nov 16, 10 a.m.'), ('2027-01-05T22:00:00Z', 'Jan 5, 2027')]:
        q = b.new_page(viewport={'width': 1280, 'height': 900}); q.clock.set_fixed_time(iso); q.goto(URL); q.wait_for_selector('#app:not([hidden])')
        q.locator('[data-worked]').click(); q.wait_for_timeout(300)
        check(q.is_visible('#simBanner') and 'Simulated Monday, November 16, 2026, 5:30 p.m.' in q.inner_text('#simBanner') and 'Simulated Monday, November 16, 2026, 5:30 p.m.' in q.inner_text('#planbClock') and 'Scheduled departures you may be able to catch' in q.inner_text('#planbOut') and q.inner_text('#pct') == '23%', f'{label}: Kipling example on the simulated clock with departures')
        k = q.inner_text('#suggest'); check(k.startswith('Schedule comparison: waiting looks better') and '149' in k, f'{label}: Kipling example verdict ({k[:80]})')
        q.locator('[data-contrast]').click(); q.wait_for_timeout(300)
        t = q.inner_text('#suggest')
        check(q.input_value('#dest') == 'Dupont' and t.startswith('Schedule comparison: switching looks better') and '26 Dupont' in t and 'runs on time' in t and q.locator('#suggest a[href*="ttc.ca/service-alerts"]').count() == 1, f'{label}: contrast example switching, with the catch it and runs on time line and a TTC link ({t[:70]})')
        be = q.inner_text('#breakeven'); check('Break even: by the timetable switching wins by about' in be and '5:35 p.m. bus' in be and 'the next is 5:58 p.m.' in be, f'{label}: missed bus warning with the break even margin ({be[:110]})')
        if label.startswith('Jan'):
            q.click('#liveTime'); q.wait_for_timeout(300)
            check(q.is_hidden('#simBanner') and 'Today is after that' in q.inner_text('#planbClock') and 'Scheduled departures you may be able to catch' not in q.inner_text('#planbOut'), 'Jan 5, 2027: live time shows the schedule ended message')
        q.close()
    for iso, label in [('2026-12-07T17:00:00Z', 'Dec 7 noon'), ('2026-12-20T17:00:00Z', 'Dec 20 noon')]:
        q = at(iso); check('Scheduled departures you may be able to catch' in q.inner_text('#planbOut'), f'{label}: departures shown'); q.close()
    q = at('2026-11-17T08:00:00Z')   # 3 a.m.
    txt = q.inner_text('#planbOut')
    check('Overnight: Blue Night route 300' in txt, '3 a.m.: Blue Night route 300 line shown overnight')
    check('3:00 a.m.' in q.inner_text('#planbClock') and ('Scheduled departures you may be able to catch' in txt or 'No departure you can still catch' in txt), '3 a.m.: clock and departures or a clear none message')
    q.close()
    q = at('2026-12-22T17:00:00Z')
    check('Schedule data ends on Dec 21, 2026' in q.inner_text('#planbClock') and 'Today is after that' in q.inner_text('#planbClock') and 'Scheduled departures you may be able to catch' not in q.inner_text('#planbOut'), 'after Dec 21: clear schedule ended message, no times')
    q.close()
    q = b.new_page(viewport={'width': 1280, 'height': 900}); q.clock.install(time='2026-11-17T04:58:30Z')   # Monday 11:58:30 p.m.
    q.goto(URL); q.wait_for_selector('#app:not([hidden])'); q.fill('#alert', KIP); q.wait_for_timeout(300)
    before = q.inner_text('#planbClock'); q.clock.run_for(150000); q.wait_for_timeout(300); after = q.inner_text('#planbClock')
    check('11:58 p.m.' in before and ('12:00 a.m.' in after or '12:01 a.m.' in after), f'Plan B refreshes each minute and across midnight ({before.split("(")[1].split(")")[0]} then {after.split("(")[1].split(")")[0]})')
    q.close()
    # The alerts copy: shown with its time, one tap fills the alert; a missing copy leaves paste working
    import json, time as _t
    fx = {'source': 'TTC GTFS Realtime alerts, subway feed (https://gtfsrt.ttc.ca/alerts/subway)', 'licence': 'Open Government Licence Toronto', 'fetchedAt': 1794772174, 'feedTimestamp': 1794772174,
          'alerts': [{'id': '1', 'lines': ['YU'], 'cause': 'MEDICAL_EMERGENCY', 'effect': 'SIGNIFICANT_DELAYS', 'header': 'Line 1 Yonge-University: Delays northbound at Museum station due to a medical emergency.', 'description': '', 'start': 1794772035, 'end': 0}]}
    q = b.new_page(viewport={'width': 1280, 'height': 900}); q.clock.set_fixed_time('2026-11-15T20:30:00Z')
    q.route('**/data/live_alerts.json*', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(fx)))
    q.goto(URL); q.wait_for_selector('#live:not([hidden])', timeout=8000); q.click('#liveSum')
    check('copied 2:49 p.m. on Nov 15, 2026' in q.inner_text('#liveSum') and 'Open Government Licence Toronto' in q.inner_text('#liveNote'), f'alerts copy shows when it was copied ({q.inner_text("#liveSum")})')
    q.click('[data-live="0"]'); q.wait_for_timeout(300)
    check(q.input_value('#station') == 'Museum' and q.input_value('#group') == 'medical' and q.is_visible('#pct'), 'one tap on a copied alert fills it and shows a number')
    q.close()
    q.close()
    # Stale copy: older than 90 minutes and the job status unknown, a red banner; a recent successful job run (feed unchanged) clears it
    old = dict(fx, fetchedAt=1794772174 - 3 * 3600)
    for api, want, label in [(None, True, 'no job status'), ({'workflow_runs': [{'updated_at': '2026-11-15T20:20:00Z'}]}, False, 'job ran 10 minutes ago, feed unchanged'), ({'workflow_runs': [{'updated_at': '2026-11-15T17:00:00Z'}]}, True, 'job last ran 3.5 hours ago (delayed schedule)')]:
        q = b.new_page(viewport={'width': 1280, 'height': 900}); q.clock.set_fixed_time('2026-11-15T20:30:00Z')
        q.route('**/data/live_alerts.json*', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(old)))
        def handler(body):
            return (lambda r: r.abort()) if body is None else (lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(body)))
        q.route('https://api.github.com/**', handler(api))
        q.goto(URL); q.wait_for_selector('#live:not([hidden])', timeout=8000); q.wait_for_timeout(300)
        shown = 'isstale' in (q.get_attribute('#live', 'class') or '')
        check(shown == want and (not want or ('may be out of date' in q.inner_text('#liveSum') and 'may be out of date' in q.text_content('#liveStale'))), f'stale banner {"shown" if want else "hidden"}: {label} ({q.inner_text("#liveSum")})')
        q.close()
    hist = {'since': 1794772174, 'alerts': {'1': {'firstSeen': 1794772174, 'lastSeen': 1794772174, 'goneBy': 1794773282, 'header': 'Line 1: Delays at Museum due to a medical emergency.', 'lines': ['YU'], 'cause': 'MEDICAL_EMERGENCY', 'effect': 'SIGNIFICANT_DELAYS'},
            '2': {'firstSeen': 1794772174, 'lastSeen': 1794773282, 'header': 'Line 2: No service between Victoria Park and Kennedy due to planned track work.', 'lines': ['BD'], 'cause': 'MAINTENANCE', 'effect': 'NO_SERVICE'}}}
    q = b.new_page(viewport={'width': 1280, 'height': 900}); q.clock.set_fixed_time('2026-11-15T20:30:00Z')
    q.route('**/data/alert_history.json*', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(hist)))
    q.goto(URL); q.wait_for_selector('#live:not([hidden])', timeout=8000); q.click('#liveSum'); q.wait_for_timeout(300)
    check('Subway alerts seen in Nov 2026: 2 (1 planned work)' in q.inner_text('#historyStrip') and q.locator('.hdays .hd').count() == 30 and 'not a check of the forecasts' in q.inner_text('#historyStrip'), f'alerts seen this month strip ({q.inner_text("#historyStrip")[:60]})')
    q.close()
    q = b.new_page(viewport={'width': 1280, 'height': 900}); q.route('**/data/live_alerts.json*', lambda r: r.abort())
    q.goto(URL); q.wait_for_selector('#app:not([hidden])'); q.wait_for_timeout(500)
    check(q.is_hidden('#live') and q.is_visible('#pasteBtn'), 'no alerts copy: the list is hidden and paste still works')
    q.goto(URL + '?alert=' + 'Line%201%3A%20Trains%20are%20bypassing%20St.%20George%20while%20we%20investigate%20a%20fire.&dest=Dupont&in=5'); q.wait_for_selector('#app:not([hidden])'); q.wait_for_timeout(300)
    check(q.input_value('#station') == 'St George' and q.input_value('#dest') == 'Dupont' and q.get_attribute('[data-elapsed="5"]', 'aria-pressed') == 'true', 'a shared link reopens the alert, destination and setting')
    q.close()
    # Plan B extras: elevator and escalator outages, Bike Share live counts and weather (fixtures, so the check is stable)
    acc = {'fetchedAt': 1794774372, 'alerts': [{'id': '9', 'station': 'Kipling', 'kind': 'escalator', 'header': 'Kipling: Escalator 16B3E out of service from Line 2 platform to bus platform while we perform maintenance.'},
                                               {'id': '8', 'station': 'Spadina', 'kind': 'elevator', 'header': 'Spadina: Elevator out of service.'}]}
    near = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'bikeshare_near.json')))
    kid = near['stations']['Kipling'][0]['id']
    status = {'last_updated': '2026-11-15T20:27:05Z', 'ttl': 7, 'data': {'stations': [{'station_id': kid, 'num_vehicles_available': 4, 'num_docks_available': 11, 'is_installed': True, 'is_renting': True, 'is_returning': True}]}}
    wx = {'properties': {'currentConditions': {'temperature': {'value': {'en': 7.6}}, 'condition': {'en': 'Mostly Cloudy'}, 'station': {'value': {'en': "Toronto Pearson Int'l Airport"}}, 'timestamp': {'en': '2026-11-15T20:00:00Z'}}, 'warnings': []}}
    def fixture(body):
        return lambda r: r.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'}, body=json.dumps(body))
    q = b.new_page(viewport={'width': 1280, 'height': 900}); q.clock.set_fixed_time('2026-11-15T20:30:00Z')
    q.route('**/data/access_alerts.json*', fixture(acc)); q.route('**/gbfs/v3.0/station_status*', fixture(status)); q.route('https://api.weather.gc.ca/**', fixture(wx))
    q.goto(URL); q.wait_for_selector('#app:not([hidden])'); q.wait_for_timeout(500); q.get_by_role('button', name='Person at track level, Kipling').click(); q.wait_for_selector('#accessWarn', timeout=8000)
    aw = q.text_content('#accessWarn')
    check('Escalator 16B3E' in aw and 'Spadina' not in aw and 'Open Government Licence Toronto' in aw, 'Plan B shows the elevator or escalator outage at the delay station only')
    check(q.is_hidden('#bikesFrom') and q.is_hidden('#surfaceRel'), 'route history, Bike Share and weather sit behind a closed fold')
    q.click('#planbExtras > summary'); q.wait_for_timeout(200)
    bf = q.inner_text('#bikesFrom'); bn = q.inner_text('#bikeNote'); wn = q.inner_text('#weatherNow')
    check('4 bikes, 11 open docks' in bf and '3:27 p.m.' in bn and 'CC BY 4.0' in bn, f'Bike Share live counts near Kipling ({bf.splitlines()[0]})')
    sr = q.inner_text('#surfaceRel')
    check('149' in sr and 'scheduled trips' in sr and 'not on time performance' in q.inner_text('#planbExtras'), f'route delay history for the Plan B routes, validated first ({sr.splitlines()[0][:70]})')
    check('7.6 °C, mostly cloudy' in wn and 'Environment and Climate Change Canada' in wn and 'not part of the forecast' in wn, f'weather is context only and attributed ({wn[:50]})')
    q.close()
    q = b.new_page(viewport={'width': 1280, 'height': 900})
    q.route('**/gbfs/v3.0/station_status*', lambda r: r.abort()); q.route('https://api.weather.gc.ca/**', lambda r: r.abort())
    q.goto(URL); q.wait_for_selector('#app:not([hidden])'); q.wait_for_timeout(500); q.get_by_role('button', name='Person at track level, Kipling').click(); q.wait_for_selector('#planbExtras', timeout=8000); q.click('#planbExtras > summary')
    check('could not be read' in q.inner_text('#bikeNote') and 'could not be read' in q.inner_text('#weatherNow') and q.is_visible('#pct'), 'Bike Share and weather failures say so and the rest still works')
    q.close()
    # axe-core accessibility rules (WCAG 2.1 A and AA) at both widths, with every fold opened
    axe = os.environ.get('AXE') or os.path.join(os.getcwd(), 'node_modules', 'axe-core', 'axe.min.js')
    if os.path.exists(axe):
        for w, h in [(390, 844), (1440, 900)]:
            q = b.new_page(viewport={'width': w, 'height': h}); q.clock.set_fixed_time('2026-11-15T20:30:00Z')
            q.route('**/data/access_alerts.json*', fixture(acc)); q.route('**/gbfs/v3.0/station_status*', fixture(status)); q.route('https://api.weather.gc.ca/**', fixture(wx))
            q.goto(URL); q.wait_for_selector('#app:not([hidden])'); q.wait_for_timeout(500); q.get_by_role('button', name='Person at track level, Kipling').click(); q.wait_for_selector('#planbExtras', timeout=8000); q.wait_for_timeout(300)
            q.evaluate("document.querySelectorAll('details').forEach((d) => { d.open = true; })"); q.wait_for_timeout(200)
            q.add_script_tag(path=axe)
            res = q.evaluate("axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } }).then((r) => r.violations.map((v) => v.id + ' (' + v.nodes.length + '): ' + v.nodes.slice(0, 3).map((n) => n.target.join(' ')).join(', ')))")
            check(not res, f'{w}: axe-core finds no WCAG 2.1 A or AA violations' + (f' {res}' if res else ''))
            q.close()
    else:
        check(not os.environ.get('REQUIRE_AXE'), 'axe-core not found (set AXE=/path/to/axe.min.js)')
    pg = b.new_page(viewport={'width': 390, 'height': 844})
    pg.route('**/data/planb.json*', lambda r: r.abort())
    pg.goto(URL); pg.wait_for_selector('#loadError:not([hidden])', timeout=8000)
    check(True, 'load failure shows an error with a retry button')
    pg.unroute('**/data/planb.json*'); pg.click('#retry'); pg.wait_for_selector('#app:not([hidden])', timeout=8000)
    check(True, 'retry loads the page')
    b.close()
print('FAILED: %d' % len(fails) if fails else 'All browser checks passed.')
sys.exit(1 if fails else 0)
