"""Sensitivity check: what the delay chances look like if the 0 minute records are kept.

The shipped models are fitted on recorded delays with a positive delay; the City log also has records with 0 minutes
of delay, which train.py leaves out. This script repeats the shipped pipeline (same features, half life, recalibration,
same three test periods) with the 0 minute records kept as "not 10+ minutes", and reports both views side by side.
It changes nothing in the app. Writes data/zero_minute_check.json.
Run: python3 scripts/zero_minute_check.py [cache_dir]
"""
import json, os, sys, zipfile
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import train as T0
from sklearn.metrics import roc_auc_score, log_loss

CACHE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ttc'
T0.CACHE = CACHE
PERIODS = [('2026-01-01', '2026-04-01'), ('2026-04-01', '2026-07-01'), ('2026-07-01', '2026-10-01')]
BANDS = {5: 'y5', 10: 'y', 20: 'y20'}

def prep(d, names):
    d = d[d.Line.isin(['YU', 'BD', 'SHP'])].copy()
    d['group'] = d.Code.map(T0.group_of)
    d['station'] = d.Station.map(T0.canon_delay_station)
    d['station'] = d.station.where(d.station.isin(names), 'Other')
    h = d.Time.str.slice(0, 2).astype(int)
    d['time'] = pd.cut(h, [-1, 5, 9, 15, 19, 23], labels=['night', 'am_peak', 'midday', 'pm_peak', 'evening']).astype(str)
    d['weekend'] = d.Day.isin(['Saturday', 'Sunday'])
    for k, yc in BANDS.items(): d[yc] = (d['Min Delay'] >= k).astype(int)
    d['dt'] = pd.to_datetime(d.Date)
    d['positive'] = d['Min Delay'] > 0
    return d

def main():
    raw = pd.read_csv(T0.fetch(T0.DELAYS_URL, 'since2025.csv'))
    gz = zipfile.ZipFile(T0.fetch(T0.GTFS_URL, 'gtfs.zip'))
    names = {s['name'] for s in T0.build_stations(gz)}
    allr = prep(raw, names)
    pos = allr[allr.positive].copy()
    groups = list(T0.GROUPS) + ['signals', 'track', 'train', 'operations', 'other']
    Tp = T0.make_tools(pos, names, groups); Ta = T0.make_tools(allr, names, groups)
    sig, logit = T0.sig, T0.logit
    def fitted(T, tr, start, yc):
        m, a, b, base, cal = T['pipeline'](tr, T0.cal_start_for(start), yc)
        return lambda df: sig(a * logit(m.predict_proba(T['X'](df))[:, 1]) + b)
    res = {'bands': {}}
    for k, yc in BANDS.items():
        ys_pos, ps_pos, ys_all, pa_all, pp_all = [], [], [], [], []
        for start, end in PERIODS:
            pf = fitted(Tp, pos[pos.Date < start], start, yc)
            af = fitted(Ta, allr[allr.Date < start], start, yc)
            te_pos = pos[(pos.Date >= start) & (pos.Date < end)]; te_all = allr[(allr.Date >= start) & (allr.Date < end)]
            ys_pos += list(te_pos[yc]); ps_pos += list(pf(te_pos))
            ys_all += list(te_all[yc]); pa_all += list(af(te_all)); pp_all += list(pf(te_all))
        ys_pos, ps_pos, ys_all, pa_all, pp_all = map(np.array, (ys_pos, ps_pos, ys_all, pa_all, pp_all))
        sc = lambda y, p: {'delays': int(len(y)), 'forecast': round(float(p.mean()), 3), 'actual': round(float(y.mean()), 3),
                           'auc': round(float(roc_auc_score(y, p)), 3), 'logLoss': round(float(log_loss(y, p)), 4)}
        res['bands'][str(k)] = {
            'shippedOnPositive': sc(ys_pos, ps_pos),          # what the page claims: among recorded positive delays
            'shippedOnAllRecords': sc(ys_all, pp_all),        # the same shipped model read as a chance per record, 0 minute records included
            'refitOnAllRecords': sc(ys_all, pa_all)}          # same pipeline refitted with 0 minute records kept
    # The Kipling example: person at track level, Kipling, Line 2, weekday 5:30 p.m.
    ex = pd.DataFrame([{'group': 'track_person', 'station': 'Kipling', 'Line': 'BD', 'time': 'pm_peak', 'weekend': False}])
    last = allr.Date.max(); res['kipling'] = {}
    for k, yc in BANDS.items():
        res['kipling'][str(k)] = {'positiveOnly': round(float(fitted(Tp, pos, last, yc)(ex)[0]), 3), 'allRecords': round(float(fitted(Ta, allr, last, yc)(ex)[0]), 3)}
    tp = allr[allr.group == 'track_person']
    res['kiplingCause'] = {'records': int(len(tp)), 'zeroMinute': int((~tp.positive).sum())}
    res['records'] = {'all': int(len(allr)), 'zeroMinute': int((~allr.positive).sum()), 'positive': int(allr.positive.sum()),
                      'zeroShareTestPeriods': round(float((~allr[(allr.Date >= PERIODS[0][0]) & (allr.Date < PERIODS[-1][1])].positive).mean()), 3)}
    res['note'] = ('The page reports the chance among recorded positive delays. Keeping 0 minute records answers a different question '
                   '(the chance per logged record), and 0 minute records are incidents the TTC logged with no delay minutes. Nothing in the app changed.')
    json.dump(res, open(os.path.join(T0.OUT, 'zero_minute_check.json'), 'w'), indent=1)
    print(json.dumps(res, indent=1))

if __name__ == '__main__':
    main()
