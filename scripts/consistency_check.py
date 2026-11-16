"""Consistency check across the public text: the page, README, DEVPOST and, if given, the paste sheet, the cover
script and the video captions. Fails on retired wording (including the retired 0.16 and 3.08 headline figures),
dashes, missing key claims, or a hero or figures line that differs.
Run: python3 scripts/consistency_check.py [extra text files...]
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
HERO = 'Subway stopped? Paste the TTC alert to see the chance a comparable recorded delay lasts 10+ minutes, and timetabled buses nearby.'
# The figures line: how often the verdict says switch and what it gains, at the same prominence as the hero.
FIGS = 'It also gives a cautious wait or switch call, and it rarely says switch: on 107 of 13,174 simulated trips (a past delay and a direction of travel), about 1 in 120. In the simulation those calls saved about 8 minutes each with an on time bus and lost about 15 each when the first bus was missed. No rider testing has been done.'
# The one place a dash is allowed: the attribution statement the Open Government Licence Toronto asks for, verbatim.
ATTR = 'Contains information licensed under the Open Government Licence – Toronto.'
RETIRED = [r'can still catch', r'you can catch', r'\bcatchable\b', r'about (5|10) minutes in\b', r'About (5|10) min in', r'not been tested with riders', r'and it runs on time', r'Bike Share and weather', r'Toronto weather now',
           # retired headline figures of the timetable only rule (round 10): 3.08 anywhere, 0.16 as a headline
           r'\b3\.08\b', r'\b0\.16( min)? saved \(0\.11', r'\b0\.16,? and\b', r'\(0\.16[,)]', r'0\.16 minutes',
           # the chance is conditional on a recorded positive delay; the old unconditional wording is retired
           r'comparable recorded TTC delays', r'to Nov(ember)? 16, 2026', r'whether to wait\.',
           # round 11 figures line (mixed units) and the privacy line that left out the IP address
           r'Overall that is 0\.06 minutes per delay', r'Only the stop code is sent to the NextBus host\.( |$)',
           # round 12 figures line and switch saving figures that did not say they were simulated
           r'When it does, it saves about 8 minutes', r'On those calls it saved', r'does not rescale its number']
# Mojibake: UTF 8 read as Windows 1252 (an en dash becomes a, euro sign, en dash). Fails anywhere.
MOJIBAKE = re.compile('\u00e2\u20ac|\u00c3[\u0080-\u00bf]|\ufffd')
# Every sentence giving minutes saved or gained by switching must say they are simulated or timetable figures.
SAVED = re.compile(r'\b(saved?|saves|saving|gains?|gained)\b', re.I)
MINS = re.compile(r'\b\d+(\.\d+)? (minutes?|min)\b')
LABEL = re.compile(r'simulat|timetable', re.I)
NEED_ALL = ['No rider testing has been done', 'not real time', 'No manual screen reader test has been done', 'late bus check', 'NextBus',
            'with a recorded delay of 1 minute or more', 'Only the stop code is sent to the NextBus host', 'also sees your IP address', 'about 1 in 120', 'Next to existing transit apps', 'rider-check.md', '107 of 13,174', 'not a rider benefit', '98%']
NEED_BOTH = ['all incidents view', 'does not confirm it is the same vehicle']
# DEVPOST is the short presentation; README carries the full evidence set.
NEED_DEVPOST = ['23%', '15%', '4%', '0.751', '7,455', '2 minute judge path', 'slay-hacks-submission', 'Zero minute', 'freeze', 'Delay already reached 5 min',
                'Copy TTC subway alerts', 'Bike Share Toronto', 'axe-core', 'Open Government Licence Toronto', '0.06 minutes per trip', '0.63', '102 real TTC alerts',
                'Timetable risk for this trip', 'not the headline', 'Live check', 'Scheduled runs so far', 'README', 'Contains information licensed under the Open Government Licence']
NEED_DOCS = ['23%', '0.751', '7,455', '2 minute judge path', 'slay-hacks-submission', 'zero_minute_check.py', 'Zero minute records', 'freeze_check.mjs', 'parser_fresh', 'alerts-backup.yml', 'Scheduled runs so far', 'liveCheck', 'check_forecast_log.mjs', 'Delay already reached 5 min', 'The model is calibrated on recorded delay length, not time since the alert',
             'Copy TTC subway alerts', 'Exploratory: looked at while the rules were chosen', 'alerts seen this month',
             'Bike Share Toronto', 'axe-core', 'Open Government Licence Toronto',
             '0.06', '0.95', '0.63', 'alert_forecasts.jsonl', '102 real TTC alerts', 'calibration in the large', 'Narrow margin', 'Timetable risk for this trip',
             'run 43777263323', '15% instead of 23%', 'not the headline', '7 of the 102', '0.06 minutes per trip', 'Same simulation, two units', 'Live check', 'Contains information licensed under the Open Government Licence']

def text_of(p):
    s = open(p, encoding='utf-8').read()
    if p.endswith('.json'):
        d = json.load(open(p)); s = ' '.join(t for _, t in d.get('caps', []))
    if p.endswith('.html'): s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', s)

def prose_of(p):
    # the text without table rows (tables carry the label in their heading), for the per sentence checks
    s = open(p, encoding='utf-8').read()
    if p.endswith('.json'): return text_of(p)
    s = re.sub(r'<table.*?</table>', ' ', s, flags=re.S)
    s = '\n'.join(l for l in s.split('\n') if not l.lstrip().startswith('|'))
    if p.endswith('.html'): s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', s)

def main(extra):
    fails = []
    files = {'index.html': os.path.join(ROOT, 'index.html'), 'README.md': os.path.join(ROOT, 'README.md'), 'DEVPOST.md': os.path.join(ROOT, 'DEVPOST.md')}
    files.update({os.path.basename(p): p for p in extra})
    T = {k: text_of(p) for k, p in files.items()}
    T['app.js'] = text_of(os.path.join(ROOT, 'app.js'))
    P = {k: prose_of(p) for k, p in files.items()}
    for k, s in T.items():
        for r in RETIRED:
            if re.search(r, s, re.I): fails.append(f'{k}: retired wording /{r}/')
        if re.search('[\u2013\u2014]', s.replace(ATTR, '')): fails.append(f'{k}: contains a dash character')
        if MOJIBAKE.search(s): fails.append(f'{k}: mojibake (UTF 8 decoded as Windows 1252): {MOJIBAKE.search(s).group()!r}')
        if k != 'app.js':
            for sent in re.split(r'(?<=[.!?])\s+(?=[A-Z"*(`])', P[k]):
                if SAVED.search(sent) and MINS.search(sent) and not LABEL.search(sent) and not re.search(r'saves (into|the forecast)', sent): fails.append(f'{k}: minutes saved not labelled simulated: {sent[:120]}')
    for k in ('index.html', 'README.md', 'DEVPOST.md'):
        for n in NEED_ALL:
            if n not in T[k]: fails.append(f'{k}: missing "{n}"')
        if HERO not in T[k]: fails.append(f'{k}: hero line differs')
        if FIGS not in T[k]: fails.append(f'{k}: figures line differs or is missing')
    for k in ('index.html', 'README.md', 'DEVPOST.md'):
        if ATTR not in T[k]: fails.append(f'{k}: attribution statement missing or altered (it needs the real en dash)')
    for n in NEED_DOCS:
        if n.lower() not in T['README.md'].lower(): fails.append(f'README.md: missing "{n}"')
    for n in NEED_DEVPOST + NEED_BOTH:
        if n.lower() not in T['DEVPOST.md'].lower(): fails.append(f'DEVPOST.md: missing "{n}"')
    for n in NEED_BOTH:
        if n.lower() not in T['README.md'].lower(): fails.append(f'README.md: missing "{n}"')
    for k in extra:
        b = os.path.basename(k)
        if b.startswith('PASTE') and HERO not in T[b]: fails.append(f'{b}: pitch differs from the hero line')
        if b.startswith('PASTE') and FIGS not in T[b]: fails.append(f'{b}: figures line missing')
    page = T['index.html'] + ' ' + T['app.js']
    for n in NEED_BOTH + ['Delay already reached 5 min', 'Delay already reached 10 min', 'calibrated on recorded delay length', 'Scheduled departures you may be able to catch', 'Timetable estimate']:
        if n not in page: fails.append(f'page: missing "{n}"')
    print('\n'.join(fails) if fails else f'Consistent: {", ".join(sorted(T))}')
    return 1 if fails else 0

if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
