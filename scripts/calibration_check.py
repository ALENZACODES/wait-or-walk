"""Over forecasting check: can a fresher recalibration fix forecasts that run high in 2026?

For each test period, the calibrated forecasts are shifted by one log odds constant so that, on the last N days of that
period's own recalibration window (earlier data only), the average forecast equals the actual share. N is 30, 46 or 61.
Then the shifted forecasts are scored on the later test period against the shipped ones.
Measures, named: forecast vs actual is calibration in the large (average forecast against actual share, in percent);
calibration error is the expected calibration error (seven forecast bins, weighted average gap, in points); log loss.
Rule set in advance: a window ships only if, for the 10+ band, its forecast vs actual gap is smaller in all three test
periods, and pooled log loss is not worse for any band.
Run after train.py: python3 scripts/calibration_check.py [cache_dir]. Writes data/calibration_check.json.
"""
import json, os, sys, pickle
import numpy as np
from scipy.optimize import brentq
ROOT = os.path.join(os.path.dirname(__file__), '..')
CACHE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ttc'
EDGES = (0, .05, .1, .15, .2, .3, .45, 1.01)
lg = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
sg = lambda z: 1 / (1 + np.exp(-z))

def ece(y, p):
    return float(sum(((p >= a) & (p < b)).mean() * abs(p[(p >= a) & (p < b)].mean() - y[(p >= a) & (p < b)].mean())
                     for a, b in zip(EDGES[:-1], EDGES[1:]) if ((p >= a) & (p < b)).any()))

def ll(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

def main():
    P = pickle.load(open(os.path.join(CACHE, 'preds.pkl'), 'rb'))
    metrics = json.load(open(os.path.join(ROOT, 'data', 'metrics.json')))
    out = {'measures': {'forecastVsActual': 'calibration in the large: average forecast against actual share',
                        'calError': 'expected calibration error, seven forecast bins, weighted average gap in points', 'logLoss': 'log loss'},
           'windows': {}}
    for days in (30, 46, 61):
        W = {}
        for band in (5, 10, 20):
            rows, Y, A, B = [], [], [], []
            for k, cs in enumerate(P['calsets']):
                d = np.array(cs['date'], dtype='datetime64[D]'); m = d > d.max() - np.timedelta64(days, 'D')
                yc = (np.asarray(cs['minutes']) >= band).astype(float); pc = np.asarray(cs['p%d' % band])
                s = brentq(lambda x: sg(lg(pc[m]) + x).mean() - yc[m].mean(), -3, 3)
                te = P['preds'][band][k]; yt = (np.asarray(te['minutes']) >= band).astype(float)
                pt = np.asarray(te['waitOrWalk']); pa = sg(lg(pt) + s)
                rows.append({'test': metrics['folds'][k]['test'], 'shift': round(float(s), 3), 'actual': round(float(yt.mean()), 4),
                             'shipped': round(float(pt.mean()), 4), 'shifted': round(float(pa.mean()), 4),
                             'calErrorShipped': round(ece(yt, pt) * 100, 2), 'calErrorShifted': round(ece(yt, pa) * 100, 2),
                             'logLossShipped': round(ll(yt, pt), 4), 'logLossShifted': round(ll(yt, pa), 4)})
                Y.append(yt); A.append(pt); B.append(pa)
            Y, A, B = map(np.concatenate, (Y, A, B))
            W[str(band)] = {'periods': rows, 'pooled': {'actual': round(float(Y.mean()), 4), 'shipped': round(float(A.mean()), 4), 'shifted': round(float(B.mean()), 4),
                            'calErrorShipped': round(ece(Y, A) * 100, 2), 'calErrorShifted': round(ece(Y, B) * 100, 2),
                            'logLossShipped': round(ll(Y, A), 4), 'logLossShifted': round(ll(Y, B), 4)}}
        ten = W['10']['periods']
        closer = all(abs(r['shifted'] - r['actual']) < abs(r['shipped'] - r['actual']) for r in ten)
        llok = all(W[b]['pooled']['logLossShifted'] <= W[b]['pooled']['logLossShipped'] for b in W)
        W['ship'] = bool(closer and llok)
        W['why'] = 'passes' if W['ship'] else ('10+ gap not smaller in every period' if not closer else 'pooled log loss worse for a band')
        out['windows'][str(days)] = W
    out['shipped'] = [k for k, v in out['windows'].items() if v['ship']]
    json.dump(out, open(os.path.join(ROOT, 'data', 'calibration_check.json'), 'w'), indent=1)
    for k, v in out['windows'].items():
        print(k, v['ship'], v['why'], [(r['shipped'], r['shifted'], r['actual']) for r in v['10']['periods']])

if __name__ == '__main__':
    main()
