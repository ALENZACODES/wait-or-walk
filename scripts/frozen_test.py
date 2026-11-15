"""Score the frozen shipped model (data/model.json) once on delays logged after its training data ends.

Downloads the newest TTC Subway Delay Data since 2025 file, keeps only delays dated after model.json trainedThrough,
and scores the shipped 10+ model exactly as the page does, against cause only and the first model (both refit only on
data up to trainedThrough). Writes docs/frozen-test-<date checked>.json. If there are no newer delays it says so.
Run: python3 scripts/frozen_test.py [cache_dir]
"""
import json, os, sys, datetime, urllib.request
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
sys.argv = sys.argv[:2]
import train as T0

ROOT = os.path.join(os.path.dirname(__file__), '..')
CACHE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ttc'
sig = lambda z: 1 / (1 + np.exp(-z)); logit = lambda p: np.log(np.clip(p, 1e-9, 1 - 1e-9) / (1 - np.clip(p, 1e-9, 1 - 1e-9)))

def score():
    """Download the newest delay file and score the frozen model on delays after its training data. Returns a dict."""
    model = json.load(open(os.path.join(ROOT, 'data', 'model.json')))
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, 'since2025_latest.csv')
    req = urllib.request.urlopen(T0.DELAYS_URL); modified = req.headers.get('Last-Modified'); open(path, 'wb').write(req.read())
    d = pd.read_csv(path)
    names = {s['name'] for s in model['stations']}
    d = d[(d['Min Delay'] > 0) & d.Line.isin(['YU', 'BD', 'SHP'])].copy()
    d['group'] = d.Code.map(T0.group_of); d['station'] = d.Station.map(T0.canon_delay_station)
    d['station'] = d.station.where(d.station.isin(names), 'Other')
    h = d.Time.str.slice(0, 2).astype(int)
    d['time'] = pd.cut(h, [-1, 5, 9, 15, 19, 23], labels=['night', 'am_peak', 'midday', 'pm_peak', 'evening']).astype(str)
    d['weekend'] = d.Day.isin(['Saturday', 'Sunday']); d['y'] = (d['Min Delay'] >= 10).astype(int); d['dt'] = pd.to_datetime(d.Date)
    today = datetime.date.today().isoformat()
    fresh = d[d.Date > model['trainedThrough']]; old = d[d.Date <= model['trainedThrough']]
    out = {'checked': today, 'sourceLastModified': modified, 'latestDelayDate': str(d.Date.max()), 'modelTrainedThrough': model['trainedThrough'],
           'delaysAfterFreeze': int(len(fresh))}
    if len(fresh):
        w = model['weights']
        z = model['intercept'] + np.array([w.get('group=' + g, 0) + w.get('station=' + s, 0) + w.get('line=' + l, 0) + w.get('time=' + t, 0) + (w.get('weekend', 0) if wk else 0)
                                           for g, s, l, t, wk in zip(fresh.group, fresh.station, fresh.Line, fresh.time, fresh.weekend)])
        p = sig(model['platt']['a'] * z + model['platt']['b'])
        groups = list(T0.GROUPS) + ['signals', 'track', 'train', 'operations', 'other']
        T = T0.make_tools(old, names, groups)
        cs = model['calibratedOn'].split(' to ')[0]
        base = old[old.Date < cs]; cal = old[old.Date >= cs]
        rate, prior = T['group_rate'](base, cs, 'y')
        pa, pb = T['platt_on'](np.array([rate.get(g, prior) for g in cal.group]), cal.y)
        cause = sig(pa * logit(np.array([rate.get(g, prior) for g in fresh.group])) + pb)
        first = LogisticRegression(C=0.5, max_iter=5000).fit(T['X'](old), old.y).predict_proba(T['X'](fresh))[:, 1]
        part = [{'y': fresh.y.values, 'date': fresh.Date.values, 'waitOrWalk': p, 'causeOnly': cause, 'firstModel': first}]
        rng = np.random.default_rng(20261115)
        out['byDelay'] = T0.block(part, T0.METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'delay', rng)
        out['byDay'] = T0.block(part, T0.METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'day', rng)
    else:
        out['note'] = 'No delays after the training data yet, so there is no fresh frozen test. Run this again when the City publishes newer delays.'
    return out

def main():
    out = score(); today = out['checked']
    os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'docs', f'frozen-test-{today}.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1)[:3000])

if __name__ == '__main__':
    main()
