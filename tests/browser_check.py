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
          'Fire investigation, St George': ('St George', 'high')}
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
            check(pg.is_visible('#pct') and pg.locator('#pct').bounding_box()['y'] < h, f'{w}: an example result is visible above the fold')
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
        check(pg.evaluate('document.documentElement.scrollWidth') <= w, f'{w}: no sideways scrolling')
        check(not errs, f'{w}: no script errors {errs}')
        pg.close()
    pg = b.new_page(viewport={'width': 390, 'height': 844})
    pg.route('**/data/planb.json', lambda r: r.abort())
    pg.goto(URL); pg.wait_for_selector('#loadError:not([hidden])', timeout=8000)
    check(True, 'load failure shows an error with a retry button')
    pg.unroute('**/data/planb.json'); pg.click('#retry'); pg.wait_for_selector('#app:not([hidden])', timeout=8000)
    check(True, 'retry loads the page')
    b.close()
print('FAILED: %d' % len(fails) if fails else 'All browser checks passed.')
sys.exit(1 if fails else 0)
