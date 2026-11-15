"""Pick the shipped switch margin for the expected cost rule, on earlier data only.

The rule (tested in train.py, see decisionPolicy in data/metrics.json): switch when the expected logged delay minus the
scheduled switch cost reaches a margin. Expected logged delay = P(under 5) m1 + P(5 to 10) m2 + P(10 to 20) m3 + P(20+) m4,
from the three shipped bands, where m1 to m4 are the average logged minutes (capped at 60) in each range in the base
training data. The margin is the one that loses the fewest simulated minutes on the shipped model's own recalibration
window (model.json calibratedOn), the latest data before any rider uses it. Writes data/policy.json.
Run after train.py: python3 scripts/choose_policy.py [cache_dir]
"""
import json, os, sys
import numpy as np, pandas as pd
sys.argv = sys.argv[:2]
import train as T0

ROOT = os.path.join(os.path.dirname(__file__), '..')
CACHE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ttc'
sig = lambda z: 1 / (1 + np.exp(-z))

def main():
    model = json.load(open(os.path.join(ROOT, 'data', 'model.json')))
    d = pd.read_csv(os.path.join(CACHE, 'since2025.csv'))
    names = {s['name'] for s in model['stations']}
    d = d[(d['Min Delay'] > 0) & d.Line.isin(['YU', 'BD', 'SHP'])].copy()
    d['group'] = d.Code.map(T0.group_of); d['station'] = d.Station.map(T0.canon_delay_station)
    d['station'] = d.station.where(d.station.isin(names), 'Other')
    h = d.Time.str.slice(0, 2).astype(int); d['tmin'] = h * 60 + d.Time.str.slice(3, 5).astype(int)
    d['time'] = pd.cut(h, [-1, 5, 9, 15, 19, 23], labels=['night', 'am_peak', 'midday', 'pm_peak', 'evening']).astype(str)
    d['weekend'] = d.Day.isin(['Saturday', 'Sunday'])
    base = d[d.Date <= model['baseTrainedThrough']]
    lo, hi = model['calibratedOn'].split(' to ')
    cal = d[(d.Date >= lo) & (d.Date <= hi)]
    bD = np.minimum(base['Min Delay'].values.astype(float), T0.WAIT_CAP)
    bm = [float(bD[(bD >= a) & (bD < b)].mean()) for a, b in [(0, 5), (5, 10), (10, 20), (20, 1e9)]]
    def band(m):
        w = m['weights']
        z = m['intercept'] + np.array([w.get('group=' + g, 0) + w.get('station=' + s, 0) + w.get('line=' + l, 0) + w.get('time=' + t, 0) + (w.get('weekend', 0) if wk else 0)
                                       for g, s, l, t, wk in zip(cal.group, cal.station, cal.Line, cal.time, cal.weekend)])
        return sig(m['platt']['a'] * z + m['platt']['b'])
    p10 = band(model); p5 = np.maximum(band(model['bands']['5']), p10); p20 = np.minimum(band(model['bands']['20']), p10)
    ew = (1 - p5) * bm[0] + (p5 - p10) * bm[1] + (p10 - p20) * bm[2] + p20 * bm[3]
    part = {'y': np.zeros(len(cal)), 'station': cal.station.values, 'line': cal.Line.values, 'tmin': cal.tmin.values, 'day': cal.Day.values}
    rows, _ = T0.switch_rows([part]); D = np.minimum(cal['Min Delay'].values.astype(float), T0.WAIT_CAP)
    costs = {mg: float(T0.policy_costs(rows, D, lambda r, x: ew[r] - x >= mg).mean()) for mg in T0.MARGIN_GRID}
    best = min(T0.MARGIN_GRID, key=lambda mg: costs[mg])
    # "Too close to call" band: the largest of 0.5 to 5 minutes above the margin that costs at most 0.01 minutes per
    # delay on the same window (tested on later periods in scripts/decision_checks.py, which decides if it ships).
    band_close = 0.0
    for bb in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]:
        if float(T0.policy_costs(rows, D, lambda r, x: ew[r] - x >= best + bb).mean()) - costs[best] <= 0.01: band_close = bb
    out = {'rule': 'expectedCost', 'margin': best, 'binMeans': [round(x, 2) for x in bm], 'binMeansFrom': f"{base.Date.min()} to {model['baseTrainedThrough']}",
           'chosenOn': model['calibratedOn'], 'delays': int(len(cal)), 'averageMinutesAtMargin': round(costs[best], 3),
           'averageMinutesAlwaysWait': round(float(D.mean()), 3), 'closeBand': band_close}
    json.dump(out, open(os.path.join(ROOT, 'data', 'policy.json'), 'w'), indent=1)
    print(out)

if __name__ == '__main__':
    main()
