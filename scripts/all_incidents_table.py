"""The all incidents view, shown beside every chance on the page.

The shipped models (frozen, data/model.json) give the chance among incidents with a recorded delay of 1 minute or more.
This script runs the same pipeline as the zero minute sensitivity check (scripts/zero_minute_check.py: same features,
age weighting, recalibration), fitted on every record up to the latest date with the 0 minute records kept as "not
5+ / 10+ / 20+ minutes", and writes the chance for every cause, station, line, time of day and day type to
data/all_incidents.json. The page looks it up; it does not change the shipped model, the verdict or any frozen file.
As a check, the same grid from the positive delay pipeline is compared with the shipped model's parity cases
(data/parity.json) and the largest gap is recorded.
Run: python3 scripts/all_incidents_table.py [cache_dir]
"""
import json, os, sys, zipfile
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import zero_minute_check as Z
T0 = Z.T0
TIMES = ['night', 'am_peak', 'midday', 'pm_peak', 'evening']

def main():
    raw = pd.read_csv(T0.fetch(T0.DELAYS_URL, 'since2025.csv'))
    gz = zipfile.ZipFile(T0.fetch(T0.GTFS_URL, 'gtfs.zip'))
    names = {s['name'] for s in T0.build_stations(gz)}
    allr = Z.prep(raw, names); pos = allr[allr.positive].copy()
    groups = list(T0.GROUPS) + ['signals', 'track', 'train', 'operations', 'other']
    Tp = T0.make_tools(pos, names, groups); Ta = T0.make_tools(allr, names, groups)
    last = allr.Date.max()
    def fitted(T, tr, yc):
        m, a, b, base, cal = T['pipeline'](tr, T0.cal_start_for(last), yc)
        return lambda df: T0.sig(a * T0.logit(m.predict_proba(T['X'](df))[:, 1]) + b)
    model = json.load(open(os.path.join(T0.OUT, 'model.json')))
    rows = []
    for g in model['groups']:
        for s in model['stations']:
            for l in s['lines']:
                for t in TIMES:
                    for w in (False, True):
                        rows.append({'group': g, 'station': s['name'] if s['name'] in names else 'Other', 'name': s['name'], 'Line': l, 'time': t, 'weekend': w})
    df = pd.DataFrame(rows)
    A = {k: fitted(Ta, allr, yc)(df) for k, yc in Z.BANDS.items()}
    P = {k: fitted(Tp, pos, yc)(df) for k, yc in Z.BANDS.items()}
    table = {}
    for i, r in df.iterrows():
        key = f"{r['name']}|{r.Line}"
        table.setdefault(r.group, {}).setdefault(key, []).append([round(float(A[k][i]), 3) for k in (5, 10, 20)])
    # check: the positive delay grid against the shipped model's parity cases
    par = json.load(open(os.path.join(T0.OUT, 'parity.json'))); gaps = []
    for c in par:
        j = df[(df.group == c['group']) & (df.name == c['station']) & (df.Line == c['line']) & (df.time == c['time']) & (df.weekend == c['weekend'])].index
        if len(j): gaps.append(abs(float(P[10][j[0]]) - c['p']))
    out = {'note': 'Chance per logged incident, 0 minute records included (5+, 10+, 20+ minutes), from the pipeline of scripts/zero_minute_check.py fitted on every record to ' + str(last) +
                   '. Shown beside the shipped chance, which is among incidents with a recorded delay of 1 minute or more. Not used by the verdict.',
           'fittedThrough': str(last), 'bands': [5, 10, 20], 'order': 'for each cause and station|line: time of day (' + ', '.join(TIMES) + ') by weekday then weekend',
           'times': TIMES, 'check': {'parityCases': len(gaps), 'maxGapPositivePipelineVsShipped10': round(max(gaps), 4) if gaps else None},
           'table': table}
    json.dump(out, open(os.path.join(T0.OUT, 'all_incidents.json'), 'w'), separators=(',', ':'))
    print(json.dumps(out['check']), len(df), 'cells')

if __name__ == '__main__':
    main()
