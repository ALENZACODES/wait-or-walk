"""Consistency check across the public text: the page, README, DEVPOST and, if given, the paste sheet, the cover
script and the video captions. Fails on retired wording (including the retired 0.16 and 3.08 headline figures),
dashes, missing key claims, or a hero or figures line that differs.
Run: python3 scripts/consistency_check.py [extra text files...]
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
HERO = 'Subway stopped? Paste the TTC alert to see the chance a comparable recorded delay lasts 10+ minutes, and timetabled buses nearby.'
# The figures line: how often the verdict says switch and what it gains, at the same prominence as the hero.
FIGS = 'It also gives a cautious wait or switch call. Simulated on 7,455 past delays, it said switch on 107 of 13,174 trips (a delay and a direction of travel, 0.8%): about 8 minutes saved on each (5.5 to 10.4) with buses on schedule, about 3 with the bus 5 minutes late, and about 15 lost when the first bus was missed. Overall that is 0.06 minutes per delay, and 0.95 on delays of 20 minutes or more. No rider testing has been done.'
RETIRED = [r'can still catch', r'you can catch', r'\bcatchable\b', r'about (5|10) minutes in\b', r'About (5|10) min in', r'not been tested with riders', r'and it runs on time', r'Bike Share and weather', r'Toronto weather now',
           # retired headline figures of the timetable only rule (round 10): 3.08 anywhere, 0.16 as a headline
           r'\b3\.08\b', r'\b0\.16( min)? saved \(0\.11', r'\b0\.16,? and\b', r'\(0\.16[,)]', r'0\.16 minutes',
           # the chance is conditional on a recorded positive delay; the old unconditional wording is retired
           r'comparable recorded TTC delays', r'to Nov(ember)? 16, 2026', r'whether to wait\.']
NEED_ALL = ['No rider testing has been done', 'not real time', 'No manual screen reader test has been done', 'late bus check', 'NextBus',
            'with a recorded delay of 1 minute or more', 'Only the stop code is sent to the NextBus host', 'rider-check.md', '107 of 13,174', 'not a rider benefit', '98%']
NEED_DOCS = ['23%', '0.751', '7,455', '2 minute judge path', 'slay-hacks-submission', 'zero_minute_check.py', 'Zero minute records', 'freeze_check.mjs', 'parser_fresh', 'alerts-backup.yml', 'Scheduled runs so far', 'liveCheck', 'check_forecast_log.mjs', 'Delay already reached 5 min', 'The model is calibrated on recorded delay length, not time since the alert',
             'Copy TTC subway alerts', 'Exploratory: looked at while the rules were chosen', 'alerts seen this month',
             'Bike Share Toronto', 'axe-core', 'Open Government Licence Toronto',
             '0.06', '0.95', '0.63', 'alert_forecasts.jsonl', '102 real TTC alerts', 'calibration in the large', 'Narrow margin', 'Timetable risk for this trip',
             'run 43777263323', '15% instead of 23%', 'not the headline', '7 of the 102']

def text_of(p):
    s = open(p, encoding='utf-8').read()
    if p.endswith('.json'):
        d = json.load(open(p)); s = ' '.join(t for _, t in d.get('caps', []))
    if p.endswith('.html'): s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', s)

def main(extra):
    fails = []
    files = {'index.html': os.path.join(ROOT, 'index.html'), 'README.md': os.path.join(ROOT, 'README.md'), 'DEVPOST.md': os.path.join(ROOT, 'DEVPOST.md')}
    files.update({os.path.basename(p): p for p in extra})
    T = {k: text_of(p) for k, p in files.items()}
    T['app.js'] = text_of(os.path.join(ROOT, 'app.js'))
    for k, s in T.items():
        for r in RETIRED:
            if re.search(r, s, re.I): fails.append(f'{k}: retired wording /{r}/')
        if re.search('[\u2013\u2014]', s): fails.append(f'{k}: contains a dash character')
    for k in ('index.html', 'README.md', 'DEVPOST.md'):
        for n in NEED_ALL:
            if n not in T[k]: fails.append(f'{k}: missing "{n}"')
        if HERO not in T[k]: fails.append(f'{k}: hero line differs')
        if FIGS not in T[k]: fails.append(f'{k}: figures line differs or is missing')
    for k in ('README.md', 'DEVPOST.md'):
        for n in NEED_DOCS:
            if n.lower() not in T[k].lower(): fails.append(f'{k}: missing "{n}"')
    for k in extra:
        b = os.path.basename(k)
        if b.startswith('PASTE') and HERO not in T[b]: fails.append(f'{b}: pitch differs from the hero line')
        if b.startswith('PASTE') and FIGS not in T[b]: fails.append(f'{b}: figures line missing')
    page = T['index.html'] + ' ' + T['app.js']
    for n in ['Delay already reached 5 min', 'Delay already reached 10 min', 'calibrated on recorded delay length', 'Scheduled departures you may be able to catch', 'Timetable estimate']:
        if n not in page: fails.append(f'page: missing "{n}"')
    print('\n'.join(fails) if fails else f'Consistent: {", ".join(sorted(T))}')
    return 1 if fails else 0

if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
