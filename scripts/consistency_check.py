"""Consistency check across the public text: the page, README, DEVPOST and, if given, the paste sheet, the cover
script and the video captions. Fails on retired wording, dashes, missing key claims, or a hero line that differs.
Run: python3 scripts/consistency_check.py [extra text files...]
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
HERO = 'Subway stopped? Paste the TTC alert to see the chance of a long delay, timetabled buses nearby, and whether to wait.'
RETIRED = [r'can still catch', r'you can catch', r'\bcatchable\b', r'about (5|10) minutes in\b', r'About (5|10) min in', r'not been tested with riders']
NEED_ALL = ['No rider testing has been done', 'not real time']
NEED_DOCS = ['23%', '0.751', '3.08', '0.16', '7,455', 'Delay already reached 5 min', 'The model is calibrated on recorded delay length, not time since the alert',
             'Copy TTC subway alerts', 'too close to call', 'Exploratory: looked at while the rules were chosen', 'alerts seen this month',
             'Environment and Climate Change Canada', 'Bike Share Toronto', 'axe-core', 'Open Government Licence Toronto']

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
    for k in ('README.md', 'DEVPOST.md'):
        for n in NEED_DOCS:
            if n.lower() not in T[k].lower(): fails.append(f'{k}: missing "{n}"')
    for k in extra:
        b = os.path.basename(k)
        if b.startswith('PASTE') and HERO not in T[b]: fails.append(f'{b}: pitch differs from the hero line')
    page = T['index.html'] + ' ' + T['app.js']
    for n in ['Delay already reached 5 min', 'Delay already reached 10 min', 'calibrated on recorded delay length', 'Scheduled departures you may be able to catch', 'Timetable estimate']:
        if n not in page: fails.append(f'page: missing "{n}"')
    print('\n'.join(fails) if fails else f'Consistent: {", ".join(sorted(T))}')
    return 1 if fails else 0

if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
