"""Checks on the shipped wait or switch rule (expected cost rule), on the same test periods as train.py.

1. Drift in the expected delay: the bin averages (m1 to m4) come from the base training data, and long delays became rarer
   in 2026. Compares them with averages from each period's recalibration window (the latest 91 days before it, still
   earlier data): bias of the expected delay against logged minutes, and the simulated minutes of the rule with each.
2. Stress test: the rider decides from the schedule (80 m a minute, 1 minute to board, on time buses), but the switch
   really costs more: buses 5 or 10 minutes late, the first catchable departure missed, walking at 1.0 m/s (60 m a minute),
   boarding buffers of 1 to 3 minutes, and all of the bad ones at once. Does the rule still beat always waiting?
Reads the evaluation forecasts train.py saves in the cache (preds.pkl). Writes data/decision_checks.json.
Run after train.py: python3 scripts/decision_checks.py [cache_dir]
"""
import json, os, sys, pickle
import numpy as np
sys.argv = sys.argv[:2]
import train as T0

ROOT = os.path.join(os.path.dirname(__file__), '..')
CACHE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ttc'
WAIT_CAP = T0.WAIT_CAP
BINS = [(0, 5), (5, 10), (10, 20), (20, 1e9)]

def bin_means(minutes):
    D = np.minimum(np.asarray(minutes, float), WAIT_CAP)
    return [float(D[(D >= a) & (D < b)].mean()) for a, b in BINS]

def exp_wait(p5, p10, p20, bm):
    return (1 - p5) * bm[0] + (p5 - p10) * bm[1] + (p10 - p20) * bm[2] + p20 * bm[3]

def candidates():
    pb, deps = T0.schedule_tables(); cands = {}
    for l, order in pb['lines'].items():
        pos = {n: i for i, n in enumerate(order)}; cum = pb['subwayMinutes'][l]
        for pi, q in enumerate(pb['patterns']):
            if q['night']: continue
            for i, v in enumerate(q['visits']):
                if v['station'] not in pos or v.get('end'): continue
                a = pos[v['station']]
                for j in range(i + 1, len(q['visits'])):
                    s2 = q['visits'][j]['station']
                    if s2 in pos and s2 != v['station']:
                        if abs(pos[s2] - a) > T0.MAX_STEPS: break
                        cands.setdefault((v['station'], l, 1 if pos[s2] > a else -1), []).append((pi, i, v['metres'], q['visits'][j]['ride'] - v['ride'], abs(cum[pos[s2]] - cum[a])))
                        break
    return pb, deps, cands

SCENARIOS = {'asScheduled': {}, 'busLate5': {'late': 5}, 'busLate10': {'late': 10}, 'missedDeparture': {'miss': 1},
             'walk60': {'speed': 60}, 'board2': {'board': 2}, 'board3': {'board': 3},
             'allBad': {'late': 5, 'miss': 1, 'speed': 60, 'board': 3}}

def directions(part, pb, deps, cands):
    """For each delay: a list per direction of (scheduled cost, {scenario: realized cost}) for the route the schedule picks."""
    out = []
    for r in range(len(part['y'])):
        st, l, t = part['station'][r], part['line'][r], int(part['tmin'][r])
        dt = 'saturday' if part['day'][r] == 'Saturday' else 'sunday' if part['day'][r] == 'Sunday' else 'weekday'
        order = pb['lines'].get(l, []); dirs = []
        if st in order:
            a = order.index(st)
            for dirn in (1, -1):
                if not 0 <= a + dirn < len(order): continue
                best = None
                for c in cands.get((st, l, dirn), []):
                    pi, i, metres, ride, sub = c; arr = deps[dt][pi][i]
                    k = np.searchsorted(arr, t + max(1, int(np.ceil(metres / 80))) + T0.BOARD_MIN)
                    if k < len(arr) and arr[k] - t <= 180:
                        x = max(arr[k] + ride - t - sub, 0)
                        if best is None or x < best[0]: best = (x, c)
                if best is None: dirs.append(None); continue
                pi, i, metres, ride, sub = best[1]; arr = deps[dt][pi][i]; real = {}
                for name, s in SCENARIOS.items():
                    walk = max(1, int(np.ceil(metres / s.get('speed', 80))))
                    k = np.searchsorted(arr, t + walk + s.get('board', T0.BOARD_MIN)) + s.get('miss', 0)
                    real[name] = max(arr[k] + s.get('late', 0) + ride - t - sub, 0) if k < len(arr) else None
                dirs.append((best[0], real))
        out.append(dirs)
    return out

def cost(rows, D, decide, scenario=None):
    """Average minutes over directions. decide(r, x) uses the scheduled cost x; the realized cost may differ.
    A direction with no later departure under a scenario costs the delay plus walking back (2 minutes)."""
    out = np.empty(len(rows))
    for r, dirs in enumerate(rows):
        if not dirs: out[r] = D[r]; continue
        vals = []
        for d in dirs:
            if d is None or not decide(r, d[0]): vals.append(D[r]); continue
            x = d[0] if scenario is None else d[1][scenario]
            vals.append(D[r] + 2 if x is None else x)
        out[r] = np.mean(vals)
    return out

def main():
    P = pickle.load(open(os.path.join(CACHE, 'preds.pkl'), 'rb')); preds, calsets = P['preds'], P['calsets']
    metrics = json.load(open(os.path.join(ROOT, 'data', 'metrics.json')))
    margins = [c['expectedCostMargin'] for c in metrics['evidence']['decisionPolicy']['chosen']]
    pb, deps, cands = candidates()
    rng = np.random.default_rng(20261118)
    tests, drift = [], []
    for k, cs in enumerate(calsets):
        te = {q: preds[10][k][q] for q in ['minutes', 'date', 'station', 'line', 'tmin', 'day', 'y']}
        p5, p10, p20 = preds[5][k]['waitOrWalk'], preds[10][k]['waitOrWalk'], preds[20][k]['waitOrWalk']
        D = np.minimum(te['minutes'], WAIT_CAP)
        bm_base, bm_recent = cs['binMeans'], bin_means(cs['minutes'])
        ew_base, ew_recent = exp_wait(p5, p10, p20, bm_base), exp_wait(p5, p10, p20, bm_recent)
        # the recent version gets its own margin, picked on the same earlier window
        rows_c = directions(cs, pb, deps, cands); Dc = np.minimum(cs['minutes'], WAIT_CAP)
        ew_c = exp_wait(cs['p5'], cs['p10'], cs['p20'], bm_recent)
        m_recent = min(T0.MARGIN_GRID, key=lambda mg: cost(rows_c, Dc, lambda r, x: ew_c[r] - x >= mg).mean())
        rows = directions(te, pb, deps, cands)
        C = {'alwaysWait': cost(rows, D, lambda r, x: False),
             'shippedRule': cost(rows, D, lambda r, x: ew_base[r] - x >= margins[k]),
             'recentBinMeans': cost(rows, D, lambda r, x: ew_recent[r] - x >= m_recent)}
        for sc in SCENARIOS:
            C['stress_' + sc] = cost(rows, D, lambda r, x: ew_base[r] - x >= margins[k], sc)
            C['stressWait_' + sc] = C['alwaysWait']
        drift.append({'test': metrics['folds'][k]['test'], 'binMeansBase': [round(x, 2) for x in bm_base], 'binMeansRecent': [round(x, 2) for x in bm_recent],
                      'loggedMinutesAverage': round(float(D.mean()), 2), 'expectedDelayBase': round(float(ew_base.mean()), 2),
                      'expectedDelayRecent': round(float(ew_recent.mean()), 2), 'recentMargin': m_recent})
        tests.append(dict(C, D=D, y=te['y'], date=te['date']))
    allC = {q: np.concatenate([t[q] for t in tests]) for q in tests[0] if q not in ('D', 'y', 'date')}
    D = np.concatenate([t['D'] for t in tests])
    parts = [{'y': t['y'], 'date': t['date']} for t in tests]
    draw = T0.resampler(parts, 'day', rng); idxs = [draw() for _ in range(T0.BOOT)]
    subsets = {'all': np.ones(len(D), bool), 'under10': D < 10, 'atLeast20': D >= 20}
    def ci(diff, mask):
        vals = [diff[i][mask[i]].mean() for i in idxs]
        return {'value': round(float(diff[mask].mean()), 2), 'low': round(float(np.percentile(vals, 2.5)), 2), 'high': round(float(np.percentile(vals, 97.5)), 2)}
    out = {'drift': {'periods': drift, 'subsets': {}}, 'stress': {'scenarios': SCENARIOS, 'subsets': {}}}
    for name, mask in subsets.items():
        out['drift']['subsets'][name] = {'delays': int(mask.sum()), 'shippedRule': round(float(allC['shippedRule'][mask].mean()), 2),
                                         'recentBinMeans': round(float(allC['recentBinMeans'][mask].mean()), 2),
                                         'recentMinusShipped': ci(allC['shippedRule'] - allC['recentBinMeans'], mask)}
        row = {'delays': int(mask.sum()), 'alwaysWait': round(float(allC['alwaysWait'][mask].mean()), 2)}
        for sc in SCENARIOS:
            row[sc] = {'minutes': round(float(allC['stress_' + sc][mask].mean()), 2), 'savedVsWait': ci(allC['alwaysWait'] - allC['stress_' + sc], mask)}
        out['stress']['subsets'][name] = row
    json.dump(out, open(os.path.join(ROOT, 'data', 'decision_checks.json'), 'w'), indent=1)
    print(json.dumps(out['drift'], indent=1)); print(json.dumps(out['stress']['subsets'], indent=1))

if __name__ == '__main__':
    main()
