"""Checks on the shipped wait or switch rule (expected cost rule), on the same test periods as train.py.

1. Drift in the expected delay: the bin averages (m1 to m4) come from the base training data, and long delays became rarer
   in 2026. Compares them with averages from each period's recalibration window (the latest 91 days before it, still
   earlier data): bias of the expected delay against logged minutes, and the simulated minutes of the rule with each.
2. Stress test: the rider decides from the schedule (80 m a minute, 1 minute to board, on time buses), but the switch
   really costs more: buses 5 or 10 minutes late, the first catchable departure missed, walking at 1.0 m/s (60 m a minute),
   boarding buffers of 1 to 3 minutes, and all of the bad ones at once. Does the rule still beat always waiting?
3. A slippage robust margin: for each test period the margin is picked on that period's earlier window (the same 91 days
   used for recalibration) as the one with the fewest minutes when every bus runs 5 minutes late (busLate5), then the
   full stress table is run with it on the test period. It ships only if it is at least as good as the shipped rule as
   scheduled and loses less under slippage.
4. A "too close to call" band: when the expected cost difference is within b minutes above the margin, the page would
   say too close to call and the rider waits. b is picked on each earlier window as the largest of 0.5 to 5 minutes
   that costs at most 0.01 minutes per delay there, then scored on the later test period. Rule set in advance: it
   ships only if, as scheduled, it is not worse than the shipped rule on the test periods (point estimate at least
   minus 0.01 minutes per delay and the 95% interval not entirely below zero).
4c. Per trip: data/switch_per_trip.json gives the gain over all trips (delay and direction), the same unit as the
   switch rate, so the two can be read together.
4b. A late bus check, set in advance with no tuning: switch only if switching still wins when the bus leaves 5 minutes
   late (the shipped rule with the scheduled bus cost plus 5 minutes). Both this rule and the robust margin of item 3
   are scored on the earlier windows (where the robust margin was picked) and on the later test periods. Overall means
   the average over all eight stress scenarios. Rule set in advance: the late bus check ships only if it is not worse
   than the shipped rule overall on the test periods (point estimate at least 0).
5. Switch calls of the shipped late bus check: how often it says switch (per delay and direction) and the minutes
   gained on those calls, as scheduled and in each stress scenario. A recomputation, no new rule.
6. Per period results of the shipped rule, so each evaluation period can be shown on its own.
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

LATE_SAFE = 5
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
        ew_cb = exp_wait(cs['p5'], cs['p10'], cs['p20'], bm_base)
        m_robust = min(T0.MARGIN_GRID, key=lambda mg: cost(rows_c, Dc, lambda r, x: ew_cb[r] - x >= mg, 'busLate5').mean())
        base_c = cost(rows_c, Dc, lambda r, x: ew_cb[r] - x >= margins[k]).mean()
        earlier = {}
        for sc in SCENARIOS:
            sh = cost(rows_c, Dc, lambda r, x: ew_cb[r] - x >= margins[k], sc)
            earlier[sc] = {'shipped': float(sh.mean()), 'robust': float(cost(rows_c, Dc, lambda r, x: ew_cb[r] - x >= m_robust, sc).mean()),
                           'lateSafe': float(cost(rows_c, Dc, lambda r, x: ew_cb[r] - x - LATE_SAFE >= margins[k], sc).mean()), 'n': len(Dc)}
        b_close = 0.0
        for bb in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]:
            if cost(rows_c, Dc, lambda r, x: ew_cb[r] - x >= margins[k] + bb).mean() - base_c <= 0.01: b_close = bb
        rows = directions(te, pb, deps, cands)
        C = {'alwaysWait': cost(rows, D, lambda r, x: False),
             'shippedRule': cost(rows, D, lambda r, x: ew_base[r] - x >= margins[k]),
             'recentBinMeans': cost(rows, D, lambda r, x: ew_recent[r] - x >= m_recent)}
        for sc in SCENARIOS:
            C['stress_' + sc] = cost(rows, D, lambda r, x: ew_base[r] - x >= margins[k], sc)
            C['robust_' + sc] = cost(rows, D, lambda r, x: ew_base[r] - x >= m_robust, sc)
            C['late_' + sc] = cost(rows, D, lambda r, x: ew_base[r] - x - LATE_SAFE >= margins[k], sc)
            C['close_' + sc] = cost(rows, D, lambda r, x: ew_base[r] - x >= margins[k] + b_close, sc)
        # what a rider sees: how often the shipped late bus check says switch, and what it gains on those calls
        late_dec = lambda r, x: ew_base[r] - x - LATE_SAFE >= margins[k]
        for sc in SCENARIOS:
            n_sw = np.zeros(len(D)); g_sw = np.zeros(len(D)); n_lose = np.zeros(len(D)); n_dir = np.zeros(len(D))
            for r, dirs in enumerate(rows):
                n_dir[r] = len(dirs)
                for d in dirs:
                    if d is None or not late_dec(r, d[0]): continue
                    x = d[1][sc]; g = D[r] - (D[r] + 2 if x is None else x)
                    n_sw[r] += 1; g_sw[r] += g; n_lose[r] += g < 0
            C['swN_' + sc], C['swGain_' + sc], C['swLose_' + sc], C['swDirs_' + sc] = n_sw, g_sw, n_lose, n_dir
        drift.append({'test': metrics['folds'][k]['test'], 'binMeansBase': [round(x, 2) for x in bm_base], 'binMeansRecent': [round(x, 2) for x in bm_recent],
                      'loggedMinutesAverage': round(float(D.mean()), 2), 'expectedDelayBase': round(float(ew_base.mean()), 2),
                      'expectedDelayRecent': round(float(ew_recent.mean()), 2), 'recentMargin': m_recent,
                      'shippedMargin': margins[k], 'robustMargin': m_robust, 'closeBand': b_close, 'earlier': earlier})
        tests.append(dict(C, D=D, y=te['y'], date=te['date'], k=np.full(len(D), k)))
    allC = {q: np.concatenate([t[q] for t in tests]) for q in tests[0] if q not in ('D', 'y', 'date', 'k')}
    K = np.concatenate([t['k'] for t in tests])
    D = np.concatenate([t['D'] for t in tests])
    parts = [{'y': t['y'], 'date': t['date']} for t in tests]
    draw = T0.resampler(parts, 'day', rng); idxs = [draw() for _ in range(T0.BOOT)]
    subsets = {'all': np.ones(len(D), bool), 'under10': D < 10, 'atLeast20': D >= 20, 'atLeast30': D >= 30}
    def ci(diff, mask):
        vals = [diff[i][mask[i]].mean() for i in idxs]
        return {'value': round(float(diff[mask].mean()), 2), 'low': round(float(np.percentile(vals, 2.5)), 2), 'high': round(float(np.percentile(vals, 97.5)), 2)}
    out = {'drift': {'periods': drift, 'subsets': {}}, 'stress': {'scenarios': SCENARIOS, 'subsets': {}},
           'robust': {'chosenUnder': 'busLate5', 'margins': [d['robustMargin'] for d in drift], 'subsets': {}}}
    for name, mask in subsets.items():
        out['drift']['subsets'][name] = {'delays': int(mask.sum()), 'shippedRule': round(float(allC['shippedRule'][mask].mean()), 2),
                                         'recentBinMeans': round(float(allC['recentBinMeans'][mask].mean()), 2),
                                         'recentMinusShipped': ci(allC['shippedRule'] - allC['recentBinMeans'], mask)}
        row = {'delays': int(mask.sum()), 'alwaysWait': round(float(allC['alwaysWait'][mask].mean()), 2)}
        for sc in SCENARIOS:
            row[sc] = {'minutes': round(float(allC['stress_' + sc][mask].mean()), 2), 'savedVsWait': ci(allC['alwaysWait'] - allC['stress_' + sc], mask)}
        out['stress']['subsets'][name] = row
        rob = {'delays': int(mask.sum())}
        for sc in SCENARIOS:
            rob[sc] = {'minutes': round(float(allC['robust_' + sc][mask].mean()), 2), 'savedVsWait': ci(allC['alwaysWait'] - allC['robust_' + sc], mask),
                       'robustMinusShipped': ci(allC['stress_' + sc] - allC['robust_' + sc], mask),
                       'robustMinusLate': ci(allC['late_' + sc] - allC['robust_' + sc], mask)}
        out['robust']['subsets'][name] = rob
    out['closeCall'] = {'bands': [d['closeBand'] for d in drift], 'subsets': {}}
    for name, mask in subsets.items():
        row = {'delays': int(mask.sum())}
        for sc in ('asScheduled', 'busLate5', 'missedDeparture', 'allBad'):
            row[sc] = {'savedVsWait': ci(allC['alwaysWait'] - allC['close_' + sc], mask), 'closeMinusShipped': ci(allC['stress_' + sc] - allC['close_' + sc], mask)}
        out['closeCall']['subsets'][name] = row
    cc = out['closeCall']['subsets']['all']['asScheduled']['closeMinusShipped']
    out['closeCall']['ship'] = bool(cc['value'] >= -0.01 and cc['high'] >= 0)
    # late bus check and robust margin, earlier windows against later test periods
    ls = {'lateMinutes': LATE_SAFE, 'testPeriods': {}, 'earlierWindows': {}}
    for name, mask in subsets.items():
        row = {'delays': int(mask.sum())}
        for sc in SCENARIOS:
            row[sc] = {'minutes': round(float(allC['late_' + sc][mask].mean()), 2), 'savedVsWait': ci(allC['alwaysWait'] - allC['late_' + sc], mask),
                       'lateMinusShipped': ci(allC['stress_' + sc] - allC['late_' + sc], mask)}
        row['overall'] = {'lateMinusShipped': ci(sum(allC['stress_' + sc] - allC['late_' + sc] for sc in SCENARIOS) / len(SCENARIOS), mask),
                          'robustMinusShipped': ci(sum(allC['stress_' + sc] - allC['robust_' + sc] for sc in SCENARIOS) / len(SCENARIOS), mask)}
        ls['testPeriods'][name] = row
    nE = sum(d['earlier']['asScheduled']['n'] for d in drift)
    for sc in list(SCENARIOS) + ['overall']:
        scs = list(SCENARIOS) if sc == 'overall' else [sc]
        def avg(key):
            return sum(d['earlier'][q][key] * d['earlier'][q]['n'] for d in drift for q in scs) / (nE * len(scs))
        ls['earlierWindows'][sc] = {'lateMinusShipped': round(avg('shipped') - avg('lateSafe'), 2), 'robustMinusShipped': round(avg('shipped') - avg('robust'), 2)}
    ov = ls['testPeriods']['all']['overall']['lateMinusShipped']
    ls['ship'] = bool(ov['value'] >= 0)
    # switch rate and gain per switch call (per delay and direction, as the simulation scores both directions)
    def ratio(num, den, mask):
        vals = [num[i][mask[i]].sum() / max(den[i][mask[i]].sum(), 1) for i in idxs]
        return {'value': round(float(num[mask].sum() / max(den[mask].sum(), 1)), 3), 'low': round(float(np.percentile(vals, 2.5)), 3), 'high': round(float(np.percentile(vals, 97.5)), 3)}
    sw = {'unit': 'delay and direction', 'subsets': {}}
    for name, mask in subsets.items():
        row = {'delays': int(mask.sum()), 'directions': int(allC['swDirs_asScheduled'][mask].sum()),
               'switchCalls': int(allC['swN_asScheduled'][mask].sum()),
               'switchRate': ratio(allC['swN_asScheduled'], allC['swDirs_asScheduled'], mask)}
        for sc in SCENARIOS:
            row[sc] = {'gainPerSwitch': ratio(allC['swGain_' + sc], allC['swN_' + sc], mask),
                       'shareLosing': round(float(allC['swLose_' + sc][mask].sum() / max(allC['swN_' + sc][mask].sum(), 1)), 3)}
        sw['subsets'][name] = row
    out['switchCalls'] = sw
    # the same switch calls on one denominator: minutes gained per trip (delay and direction), switch or not,
    # so the switch rate and the overall gain share a unit (written to its own file; decision_checks.json is frozen)
    pt = {'unit': 'delay and direction', 'note': 'minutes gained against always waiting, summed over switch calls and divided by all trips; a trip with a wait call gains 0', 'subsets': {}}
    for name, mask in subsets.items():
        row = {'delays': int(mask.sum()), 'trips': int(allC['swDirs_asScheduled'][mask].sum()), 'switchCalls': int(allC['swN_asScheduled'][mask].sum())}
        for sc in SCENARIOS:
            row[sc] = {'gainPerTrip': ratio(allC['swGain_' + sc], allC['swDirs_' + sc], mask)}
        pt['subsets'][name] = row
    json.dump(pt, open(os.path.join(ROOT, 'data', 'switch_per_trip.json'), 'w'), indent=1)
    ls['reason'] = 'not worse than the timetable only rule averaged over the eight stress scenarios' if ls['ship'] else 'worse than the timetable only rule averaged over the eight stress scenarios'
    out['lateSafe'] = ls
    for d in drift: d.pop('earlier')
    out['periods'] = []
    for k in range(len(tests)):
        mk = K == k
        out['periods'].append({'test': drift[k]['test'], 'margin': margins[k], 'delays': int(mk.sum()),
                               'shippedSavedVsWait': ci(allC['alwaysWait'] - allC['shippedRule'], mk),
                               'shippedSavedVsWait20': ci(allC['alwaysWait'] - allC['shippedRule'], mk & (D >= 20)),
                               'lateSavedVsWait': ci(allC['alwaysWait'] - allC['late_asScheduled'], mk),
                               'lateSavedVsWait20': ci(allC['alwaysWait'] - allC['late_asScheduled'], mk & (D >= 20))})
    a = out['robust']['subsets']['all']
    sched_ok = a['asScheduled']['robustMinusShipped']['value'] >= 0
    slip_ok = a['busLate5']['robustMinusShipped']['value'] > 0
    out['robust']['ship'] = bool(sched_ok and slip_ok)
    out['robust']['reason'] = ('at least as good as scheduled and better under slippage' if sched_ok and slip_ok else
                               'worse as scheduled than the shipped rule' if not sched_ok else 'not better under slippage')
    json.dump(out, open(os.path.join(ROOT, 'data', 'decision_checks.json'), 'w'), indent=1)
    print(json.dumps(out['closeCall'], indent=1)); print(json.dumps(out['periods'], indent=1))

if __name__ == '__main__':
    main()
