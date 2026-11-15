"""Train the Wait or Walk model from City of Toronto open data.

Downloads (if missing) TTC Subway Delay Data since 2025 and the TTC GTFS schedule,
then writes data/model.json, data/metrics.json and data/parity.json.
Run scripts/build_planb.py first: the station switch simulation reads data/planb.json and data/planb_times.json.
Run: python3 scripts/train.py [cache_dir]
"""
import json, re, sys, os, io, zipfile, urllib.request
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss

CACHE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ttc'
DELAYS_URL = 'https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/996cfe8d-fb35-40ce-b569-698d51fc683b/resource/0b6e5c52-e993-46d6-8d74-8602ee224457/download'
GTFS_URL = 'https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/7795b45e-e65a-4465-81fc-c36b9dfff169/resource/cfb6b2b8-6191-41e3-bda1-b175c51148cb/download/opendata_ttc_schedules.zip'
HALF_LIFE_DAYS = 180   # newer delays count more
CAL_DAYS = 91          # recalibrate on the latest three months
GROUP_SCALE = 3.0      # weaker shrinkage for the cause, which carries most of the signal
LONG = 10              # minutes that count as a long delay
OUT = os.path.join(os.path.dirname(__file__), '..', 'data')

def fetch(url, name):
    p = os.path.join(CACHE, name)
    if not os.path.exists(p):
        os.makedirs(CACHE, exist_ok=True)
        urllib.request.urlretrieve(url, p)
    return p

# What a rider can read in a TTC alert, mapped from the TTC delay codes.
GROUPS = {
    'medical': ('Medical emergency', ['MUI', 'MUIR', 'MUIS', 'MUIRS', 'MUIE']),
    'track_person': ('Person at track level', ['SUUT']),
    'injury_track': ('Personal injury at track level', ['MUPR1']),
    'security': ('Security or police incident', ['SUDP', 'SUO', 'SUAP', 'SUAE', 'SUPOL', 'SUBT', 'SUROB', 'SUSA', 'SUSP', 'SUCOL']),
    'alarm': ('Passenger alarm', ['MUPAA', 'SUEAS']),
    'fire': ('Fire or smoke', ['MUPLB', 'MUPLA', 'MUFS', 'PUMEL']),
    'doors': ('Door problem', ['MUDD', 'EUDO', 'MUD', 'PUOPO']),
    'weather': ('Weather', ['MUWEA', 'PUSIS', 'PUTIS']),
    'power': ('Power problem', ['MUPF', 'PUEO', 'PUPOW']),
    'cleaning': ('Cleaning or unsanitary train', ['MUSAN', 'SUG', 'SUL']),
}
PREFIX_GROUPS = [('PUS', 'signals'), ('PUATC', 'signals'), ('PUCSC', 'signals'), ('PUT', 'track'), ('EU', 'train'), ('TU', 'operations'), ('MUTO', 'operations'), ('MUNOA', 'operations'), ('MUCL', 'operations'), ('MUTD', 'operations')]
EXTRA_LABELS = {'signals': 'Signal problem', 'track': 'Track or switch problem', 'train': 'Train mechanical problem', 'operations': 'Operator or service management', 'other': 'Other or not stated'}
CODE_TO_GROUP = {c: g for g, (_, cs) in GROUPS.items() for c in cs}

def group_of(code):
    code = str(code).strip()
    if code in CODE_TO_GROUP: return CODE_TO_GROUP[code]
    for pre, g in PREFIX_GROUPS:
        if code.startswith(pre): return g
    return 'other'

ALIAS = {'BLOOR': 'Bloor', 'YONGE': 'Yonge', 'TMU': 'TMU', 'VAUGHAN MC': 'Vaughan Metropolitan Centre', 'SHEPPARD': 'Sheppard-Yonge', 'SHEPPARD-YONGE': 'Sheppard-Yonge',
         'EGLINTON WEST': 'Cedarvale', 'DUNDAS': 'TMU', 'VMC': 'Vaughan Metropolitan Centre', 'NORTH YORK CTR': 'North York Centre', 'NORTH YORK CENTRE': 'North York Centre'}

def canon_delay_station(s):
    s = str(s).upper().strip()
    s = re.sub(r'\s+(STATION|STATIO|STATI|STN|STA)\b.*$', '', s)
    s = re.sub(r'\s+(YUS|YU|BD|SHP|SRT)( LINE)?$', '', s).replace('ST. ', 'ST ').strip()
    return ALIAS.get(s, s.title().replace("'S", "'s"))

BANDS = {5: 'y5', 10: 'y', 20: 'y20'}   # minutes: target column. 10+ is the headline; 5+ and 20+ are shown beside it.

def make_tools(d, names, groups, half_life=None):
    hl = HALF_LIFE_DAYS if half_life is None else half_life
    COLS = ['group=' + g for g in groups] + ['station=' + s for s in sorted(names)] + ['station=Other']
    COLS += ['line=' + l for l in ['YU', 'BD', 'SHP']] + ['time=' + t for t in ['night', 'am_peak', 'midday', 'pm_peak', 'evening']] + ['weekend']
    idx = {c: i for i, c in enumerate(COLS)}
    def X(df):
        m = np.zeros((len(df), len(COLS)))
        for r, (g, s, l, t, w) in enumerate(zip(df.group, df.station, df.Line, df.time, df.weekend)):
            m[r, idx['group=' + g]] = GROUP_SCALE
            for k in ('station=' + s, 'line=' + l, 'time=' + t):
                m[r, idx[k]] = 1
            if w: m[r, idx['weekend']] = 1
        return m
    def weights(df, ref):
        if not hl: return np.ones(len(df))   # 0 means equal weights
        return 0.5 ** ((pd.Timestamp(ref) - df.dt).dt.days.values / hl)
    def fit(df, ref, yc='y'):
        return LogisticRegression(C=0.5, max_iter=5000).fit(X(df), df[yc], sample_weight=weights(df, ref))
    def platt_on(z, y):
        pl = LogisticRegression(C=1e6).fit(logit(z).reshape(-1, 1), y)
        return float(pl.coef_[0][0]), float(pl.intercept_[0])
    def group_rate(tr, ref, yc='y'):
        w = weights(tr, ref)
        g = pd.DataFrame({'g': tr.group.values, 'y': tr[yc].values, 'w': w})
        prior = (g.y * g.w).sum() / g.w.sum()
        num = (g.y * g.w).groupby(g.g).sum(); den = g.w.groupby(g.g).sum()
        return ((num + prior * 10) / (den + 10)).to_dict(), prior
    def pipeline(tr, cal_start, yc='y'):
        """The exact deployed process: base model on data before cal_start, Platt on cal_start onward. No refit."""
        base = tr[tr.Date < cal_start]; cal = tr[tr.Date >= cal_start]
        m = fit(base, cal_start, yc)
        a, b = platt_on(m.predict_proba(X(cal))[:, 1], cal[yc])
        return m, a, b, base, cal
    return dict(COLS=COLS, X=X, weights=weights, fit=fit, platt_on=platt_on, group_rate=group_rate, pipeline=pipeline)

logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
sig = lambda z: 1 / (1 + np.exp(-z))

def cal_start_for(ref, days=None):
    return (pd.Timestamp(ref) - pd.Timedelta(days=CAL_DAYS if days is None else days)).strftime('%Y-%m-%d')

def cell_shrunk(T, m, a_cal, base, cal, te, ref, prior_a=None):
    """Empirical Bayes adjustment for each station by cause cell on top of the base model.
    Observed long delays O and model expected E per cell (age weighted, base period only); multiplier (O + a) / (E + a)
    with a gamma prior whose strength a is picked by marginal likelihood. Then Platt is refitted on the calibration period."""
    from scipy.special import gammaln
    X = T['X']; w = T['weights'](base, ref)
    pb = m.predict_proba(X(base))[:, 1]
    key = (base.station + '|' + base.group).values
    O = pd.Series(w * base.y.values).groupby(key).sum(); E = pd.Series(w * pb).groupby(key).sum()
    if prior_a is None:
        grid = [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 3000, 10000, 100000]
        ll = [float((gammaln(O + a) - gammaln(a) + a * np.log(a / (a + E)) + O * np.log(E / (a + E))).sum()) for a in grid]
        prior_a = grid[int(np.argmax(ll))]
    mult = np.clip((O + prior_a) / (E + prior_a), 0.1, 10)
    def adj(df):
        k = pd.Series((df.station + '|' + df.group).values)
        return sig(logit(m.predict_proba(X(df))[:, 1]) + np.log(k.map(mult).fillna(1.0).values))
    a2, b2 = T['platt_on'](adj(cal), cal.y)
    return sig(a2 * logit(adj(te)) + b2), prior_a, int((O + E > 0).sum())

def main():
    d = pd.read_csv(fetch(DELAYS_URL, 'since2025.csv'))
    gz = zipfile.ZipFile(fetch(GTFS_URL, 'gtfs.zip'))
    stations = build_stations(gz)
    names = {s['name'] for s in stations}
    zero_excluded = ((d['Min Delay'] <= 0) & d.Line.isin(['YU', 'BD', 'SHP'])).sum()
    d = d[(d['Min Delay'] > 0) & d.Line.isin(['YU', 'BD', 'SHP'])].copy()
    d['group'] = d.Code.map(group_of)
    d['station'] = d.Station.map(canon_delay_station)
    d['station'] = d.station.where(d.station.isin(names), 'Other')
    h = d.Time.str.slice(0, 2).astype(int)
    d['tmin'] = h * 60 + d.Time.str.slice(3, 5).astype(int)
    d['time'] = pd.cut(h, [-1, 5, 9, 15, 19, 23], labels=['night', 'am_peak', 'midday', 'pm_peak', 'evening']).astype(str)
    d['weekend'] = d.Day.isin(['Saturday', 'Sunday'])
    for k, yc in BANDS.items(): d[yc] = (d['Min Delay'] >= k).astype(int)
    d['dt'] = pd.to_datetime(d.Date)
    groups = list(GROUPS) + ['signals', 'track', 'train', 'operations', 'other']
    last = d.Date.max()
    T = make_tools(d, names, groups); X = T['X']; COLS = T['COLS']

    def score(y, p):
        return {'auc': round(float(roc_auc_score(y, p)), 3), 'brier': round(float(brier_score_loss(y, p)), 4), 'logLoss': round(float(log_loss(y, p)), 4), 'meanPredicted': round(float(np.mean(p)), 3)}
    def bins(y, p, edges=(0, .05, .1, .15, .2, .3, .45, 1.01)):
        out = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            k = (p >= lo) & (p < hi)
            if k.sum(): out.append({'from': lo, 'to': min(hi, 1), 'delays': int(k.sum()), 'predicted': round(float(p[k].mean()), 3), 'actual': round(float(np.asarray(y)[k].mean()), 3)})
        return out

    PERIODS = [('2026-01-01', '2026-04-01'), ('2026-04-01', '2026-07-01'), ('2026-07-01', '2026-10-01')]
    folds = []; pooled_y = []; pooled_p = []; preds = {k: [] for k in BANDS}; crossing = []; cell_info = []; calsets = []
    for start, end in PERIODS:
        tr = d[d.Date < start]; te = d[(d.Date >= start) & (d.Date < end)]
        cs = cal_start_for(start)
        out = {}
        for k, yc in BANDS.items():
            m, a, b, base, cal = T['pipeline'](tr, cs, yc)
            raw = m.predict_proba(X(te))[:, 1]
            rate, prior = T['group_rate'](base, cs, yc)
            cr_cal = np.array([rate.get(g, prior) for g in cal.group]); cr_te = np.array([rate.get(g, prior) for g in te.group])
            pa, pb_ = T['platt_on'](cr_cal, cal[yc])
            fm = LogisticRegression(C=0.5, max_iter=5000).fit(X(tr), tr[yc]).predict_proba(X(te))[:, 1]
            out[k] = {'waitOrWalk': sig(a * logit(raw) + b), 'causeOnly': sig(pa * logit(cr_te) + pb_), 'firstModel': fm, 'raw': raw,
                      'calWindow': sig(a * logit(m.predict_proba(X(cal))[:, 1]) + b)}   # earlier data only, used to pick decision thresholds
            if k == 10: m10 = (m, a, b, base, cal)
        crossing.append({'test': start, 'delays': int(len(te)), 'share': round(float(((out[5]['waitOrWalk'] < out[10]['waitOrWalk']) | (out[20]['waitOrWalk'] > out[10]['waitOrWalk'])).mean()), 4)})
        for meth in ['waitOrWalk', 'causeOnly', 'firstModel']:   # the page shows 5+ >= 10+ >= 20+, so clamp the same way here
            out[5][meth] = np.maximum(out[5][meth], out[10][meth]); out[20][meth] = np.minimum(out[20][meth], out[10][meth])
        cal10 = m10[4]; bD = np.minimum(m10[3]['Min Delay'].values.astype(float), WAIT_CAP)
        calsets.append({'minutes': cal10['Min Delay'].values.astype(float), 'date': cal10.Date.values, 'station': cal10.station.values, 'line': cal10.Line.values,
                        'tmin': cal10.tmin.values, 'day': cal10.Day.values, 'y': cal10.y.values,
                        'p5': np.maximum(out[5]['calWindow'], out[10]['calWindow']), 'p10': out[10]['calWindow'], 'p20': np.minimum(out[20]['calWindow'], out[10]['calWindow']),
                        'binMeans': [float(bD[(bD >= lo) & (bD < hi)].mean()) for lo, hi in [(0, 5), (5, 10), (10, 20), (20, 1e9)]],
                        'calibratedOn': f'{cal10.Date.min()} to {cal10.Date.max()}'})
        info = {'y': None, 'minutes': te['Min Delay'].values.astype(float), 'date': te.Date.values, 'station': te.station.values, 'line': te.Line.values, 'tmin': te.tmin.values, 'day': te.Day.values}
        for k, yc in BANDS.items():
            preds[k].append(dict(info, y=te[yc].values, **{q: out[k][q] for q in ['waitOrWalk', 'causeOnly', 'firstModel']}))
        m, a, b, base, cal = m10
        cs_p, prior_a, ncell = cell_shrunk(T, m, a, base, cal, te, cs)
        cr_p, _, _ = cell_shrunk(T, m, a, base, cal, te, cs, prior_a=0.01)
        preds[10][-1]['cellShrunk'] = cs_p; preds[10][-1]['cellRaw'] = cr_p
        cell_info.append({'test': start, 'priorStrength': prior_a, 'cells': ncell})
        p = out[10]['waitOrWalk']; raw = out[10]['raw']
        pooled_y += list(te.y); pooled_p += list(p)
        folds.append({'test': f'{start} to {te.Date.max()}', 'baseTrainedThrough': base.Date.max(), 'calibratedOn': f'{cal.Date.min()} to {cal.Date.max()}',
                      'testDelays': int(len(te)), 'actualShareLong': round(float(te.y.mean()), 3),
                      'overallRate': score(te.y, np.full(len(te), tr.y.mean())),
                      'causeOnlyRate': score(te.y, out[10]['causeOnly']),
                      'firstModel': score(te.y, out[10]['firstModel']),
                      'beforeCalibration': score(te.y, raw),
                      'waitOrWalk': score(te.y, p),
                      'reliability': bins(te.y.values, p)})

    # Sensitivity of the headline model to the half life and the recalibration window (pooled point estimates).
    sens = []
    for hl in [90, 180, 365, 0]:
        Ts = make_tools(d, names, groups, half_life=hl)
        for cd in [61, 91, 122]:
            ys, ps = [], []
            for start, end in PERIODS:
                tr = d[d.Date < start]; te = d[(d.Date >= start) & (d.Date < end)]
                cs = cal_start_for(start, cd); base = tr[tr.Date < cs]; cal = tr[tr.Date >= cs]
                mm = Ts['fit'](base, cs)
                a, b = Ts['platt_on'](mm.predict_proba(X(cal))[:, 1], cal.y)
                ys.append(te.y.values); ps.append(sig(a * logit(mm.predict_proba(X(te))[:, 1]) + b))
            yy, pp = np.concatenate(ys), np.concatenate(ps)
            sens.append({'halfLifeDays': hl or None, 'calibrationDays': cd, 'shipped': hl == HALF_LIFE_DAYS and cd == CAL_DAYS,
                         'auc': round(float(roc_auc_score(yy, pp)), 4), 'logLoss': round(float(log_loss(yy, pp)), 4), 'calError': round(float(ece(yy, pp)) * 100, 2)})

    # The shipped models: one per band, each trained and recalibrated the same way.
    cs = cal_start_for((pd.Timestamp(last) + pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
    shipped = {}
    for k, yc in BANDS.items():
        m, a, b, base, cal = T['pipeline'](d, cs, yc)
        shipped[k] = {'intercept': round(float(m.intercept_[0]), 6),
                      'weights': dict(zip(COLS, (round(float(v) * (GROUP_SCALE if c.startswith('group=') else 1), 6) for c, v in zip(COLS, m.coef_[0])))),
                      'platt': {'a': round(a, 6), 'b': round(b, 6)}, '_m': m}
    m = shipped[10]['_m']; a = shipped[10]['platt']['a']; b = shipped[10]['platt']['b']
    recent = d[d.Date >= cs]
    model = {'trainedThrough': last, 'baseTrainedThrough': base.Date.max(), 'calibratedOn': f'{cal.Date.min()} to {cal.Date.max()}', 'trainedFrom': d.Date.min(), 'delays': int(len(d)),
             'longMinutes': LONG, 'halfLifeDays': HALF_LIFE_DAYS, 'calibrationDays': CAL_DAYS,
             'intercept': shipped[10]['intercept'], 'weights': shipped[10]['weights'], 'platt': shipped[10]['platt'],
             'bands': {str(k): {q: shipped[k][q] for q in ['intercept', 'weights', 'platt']} for k in (5, 20)},
             'groups': {g: {'label': GROUPS[g][0] if g in GROUPS else EXTRA_LABELS[g], 'delays': int((d.group == g).sum()),
                            'longDelays': int(((d.group == g) & (d.y == 1)).sum()),
                            'medianMinutes': float(d[d.group == g]['Min Delay'].median()) if (d.group == g).any() else None,
                            'recentShareLong': round(float(recent[recent.group == g].y.mean()), 3) if (recent.group == g).any() else None,
                            'recentDelays': int((recent.group == g).sum())}
                        for g in groups},
             'stationDelays': {s: int(v) for s, v in d.station.value_counts().items()},
             'stations': stations,
             'source': 'City of Toronto Open Data: TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS). Open Government Licence Toronto.'}
    os.makedirs(OUT, exist_ok=True)
    json.dump(model, open(os.path.join(OUT, 'model.json'), 'w'), indent=1)
    pooled = {'tests': len(folds), 'delays': len(pooled_y), 'reliability': bins(np.array(pooled_y), np.array(pooled_p))}
    import pickle; pickle.dump({'preds': preds, 'calsets': calsets, 'names': [f['test'] for f in folds]}, open(os.path.join(CACHE, 'preds.pkl'), 'wb'))   # for quick reruns of the evidence
    evidence = evaluate(preds, [f['test'] for f in folds])
    evidence['decisionPolicy'] = policy_test(preds, calsets, [f['test'] for f in folds], np.random.default_rng(20261116))
    evidence['bandCrossingBeforeClamp'] = crossing
    evidence['cellShrinkage']['prior'] = cell_info
    evidence['sensitivity'] = sens
    json.dump({'folds': folds, 'pooled': pooled, 'evidence': evidence, 'zeroMinuteRecordsExcluded': int(zero_excluded),
               'monthlyShareLong': {k: round(float(v), 3) for k, v in d.groupby(d.Date.str.slice(0, 7)).y.mean().items()}},
              open(os.path.join(OUT, 'metrics.json'), 'w'), indent=1)
    samp = d.sample(30, random_state=7)
    pr = {k: sig(shipped[k]['platt']['a'] * logit(shipped[k]['_m'].predict_proba(X(samp))[:, 1]) + shipped[k]['platt']['b']) for k in BANDS}
    p5 = np.maximum(pr[5], pr[10]); p20 = np.minimum(pr[20], pr[10])
    json.dump([{'group': g, 'station': s, 'line': l, 'time': t, 'weekend': bool(wk), 'p': round(float(p), 6), 'p5': round(float(q5), 6), 'p20': round(float(q20), 6)}
               for g, s, l, t, wk, p, q5, q20 in zip(samp.group, samp.station, samp.Line, samp.time, samp.weekend, pr[10], p5, p20)],
              open(os.path.join(OUT, 'parity.json'), 'w'), indent=1)
    print(json.dumps([{k: v for k, v in f.items() if k != 'reliability'} for f in folds], indent=1)); print(json.dumps(pooled))

METHODS = ['waitOrWalk', 'causeOnly', 'firstModel']
BOOT = 2000
SWITCH_COSTS = [8, 12, 15]   # simulation: extra minutes a rider spends by switching to a bus or streetcar
WAIT_CAP = 60                # simulation: a rider waits at most this many minutes before leaving anyway
SWITCH_AT = 0.35             # simulation: a rider switches when the forecast is in the high band
BOARD_MIN = 1                # minutes allowed to board after walking to the stop
MAX_STEPS = 3                # simulation: the alternative must reach a station at most 3 stops along the line, past the delay

def ece(y, p, edges=(0, .05, .1, .15, .2, .3, .45, 1.01)):
    tot = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        k = (p >= lo) & (p < hi)
        if k.sum(): tot += k.sum() * abs(p[k].mean() - y[k].mean())
    return tot / len(y)

def fast_auc(y, p):
    from scipy.stats import rankdata
    r = rankdata(p); n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

def metrics(y, p):
    q = np.clip(p, 1e-6, 1 - 1e-6)
    return {'auc': fast_auc(y, p), 'logLoss': float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q))), 'brier': float(np.mean((p - y) ** 2)), 'calError': ece(y, p)}

def resampler(parts, mode, rng):
    """Index draws within each period: single delays ('delay') or whole service days ('day')."""
    sizes = [len(q['y']) for q in parts]; offs = np.cumsum([0] + sizes[:-1])
    if mode == 'delay':
        return lambda: np.concatenate([o + rng.integers(0, n, n) for o, n in zip(offs, sizes)])
    days = []
    for o, q in zip(offs, parts):
        dd = pd.Series(np.arange(len(q['y'])) + o).groupby(q['date']).apply(np.array).tolist()
        days.append(dd)
    return lambda: np.concatenate([np.concatenate([dd[i] for i in rng.integers(0, len(dd), len(dd))]) for dd in days])

def block(parts, methods, base, others, mode, rng, boot=BOOT):
    y = np.concatenate([q['y'] for q in parts])
    P = {m: np.concatenate([q[m] for q in parts]) for m in methods}
    point = {m: metrics(y, P[m]) for m in methods}
    draw = resampler(parts, mode, rng)
    draws = {m: {k: [] for k in point[m]} for m in methods}
    for _ in range(boot):
        idx = draw(); yy = y[idx]
        for m in methods:
            for k, v in metrics(yy, P[m][idx]).items(): draws[m][k].append(v)
    out = {'delays': int(len(y)), 'resampling': mode, 'methods': {}, 'differences': {}}
    for m in methods:
        out['methods'][m] = {k: {'value': round(float(point[m][k]), 4), 'low': round(float(np.percentile(draws[m][k], 2.5)), 4), 'high': round(float(np.percentile(draws[m][k], 97.5)), 4)} for k in point[m]}
    for other in others:
        dd = {}
        for k in point[base]:
            diff = np.array(draws[base][k]) - np.array(draws[other][k])
            lo, hi = np.percentile(diff, [2.5, 97.5])
            dd[k] = {'value': round(float(point[base][k] - point[other][k]), 4), 'low': round(float(lo), 4), 'high': round(float(hi), 4), 'distinguishable': bool(lo > 0 or hi < 0)}
        out['differences'][other] = dd
    return out

def evaluate(preds, names):
    """Bootstrap 95% intervals on the out of time evaluation periods, by delay and (as a sensitivity check) by service day;
    the 5+ and 20+ bands; station by cause shrinkage; decision value; and two decision simulations."""
    rng = np.random.default_rng(20261115)
    P10 = preds[10]
    ev = {'bootstrapResamples': BOOT,
          'periods': [dict(test=n, **block([q], METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'delay', rng)) for n, q in zip(names, P10)],
          'pooled': block(P10, METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'delay', rng)}
    ev['dayBlock'] = {'periods': [dict(test=n, **block([q], METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'day', rng)) for n, q in zip(names, P10)],
                      'pooled': block(P10, METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'day', rng)}
    surv = []
    for scope, a, b in [('pooled', ev['pooled'], ev['dayBlock']['pooled'])] + [(n, x, y) for n, x, y in zip(names, ev['periods'], ev['dayBlock']['periods'])]:
        for other in ['causeOnly', 'firstModel']:
            for k in ['auc', 'logLoss', 'brier', 'calError']:
                da, db = a['differences'][other][k], b['differences'][other][k]
                surv.append({'scope': scope, 'against': other, 'metric': k, 'value': da['value'], 'byDelay': da['distinguishable'], 'byDay': db['distinguishable'],
                             'dayLow': db['low'], 'dayHigh': db['high']})
    ev['survival'] = surv
    ev['bands'] = {}
    for k in (5, 20):
        ev['bands'][str(k)] = {'periods': [dict(test=n, **block([q], METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'delay', rng)) for n, q in zip(names, preds[k])],
                               'pooled': block(preds[k], METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'delay', rng),
                               'pooledByDay': block(preds[k], METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'day', rng),
                               'actualShare': round(float(np.concatenate([q['y'] for q in preds[k]]).mean()), 3)}
    CM = ['cellShrunk', 'waitOrWalk', 'cellRaw']
    ev['cellShrinkage'] = {'pooled': block(P10, CM, 'cellShrunk', ['waitOrWalk', 'cellRaw'], 'delay', rng),
                           'pooledByDay': block(P10, CM, 'cellShrunk', ['waitOrWalk', 'cellRaw'], 'day', rng),
                           'periods': [dict(test=n, **block([q], CM, 'cellShrunk', ['waitOrWalk', 'cellRaw'], 'delay', rng)) for n, q in zip(names, P10)]}
    y = np.concatenate([q['y'] for q in P10]); mins_ = np.concatenate([q['minutes'] for q in P10])
    P = {m: np.concatenate([q[m] for q in P10]) for m in METHODS}
    dv = []
    for th in (0.15, 0.35):
        for m in METHODS:
            f = P[m] >= th
            dv.append({'threshold': th, 'method': m, 'flaggedShare': round(float(f.mean()), 3), 'longFlagged': round(float(f[y == 1].mean()), 3),
                       'falseFlagRate': round(float(f[y == 0].mean()), 3), 'flaggedThatWereLong': round(float(y[f].mean()), 3) if f.any() else None})
    ev['decisionValue'] = dv
    wait = np.minimum(mins_, WAIT_CAP)
    sim = {'assumptions': {'waitCostIsLoggedDelayMinutesCappedAt': WAIT_CAP, 'switchCostsMinutes': SWITCH_COSTS, 'threshold': SWITCH_AT}, 'rows': []}
    for c in SWITCH_COSTS:
        row = {'switchCost': c, 'alwaysWait': round(float(wait.mean()), 2), 'alwaysSwitch': float(c), 'hindsightBest': round(float(np.minimum(wait, c).mean()), 2)}
        for m in ['causeOnly', 'waitOrWalk']:
            row[m] = round(float(np.where(P[m] >= SWITCH_AT, c, wait).mean()), 2)
        idxs = [rng.integers(0, len(y), len(y)) for _ in range(BOOT)]
        dif = [np.where(P['waitOrWalk'][i] >= SWITCH_AT, c, wait[i]).mean() - np.where(P['causeOnly'][i] >= SWITCH_AT, c, wait[i]).mean() for i in idxs]
        row['waitOrWalkMinusCauseOnly'] = {'value': round(row['waitOrWalk'] - row['causeOnly'], 2), 'low': round(float(np.percentile(dif, 2.5)), 2), 'high': round(float(np.percentile(dif, 97.5)), 2)}
        sim['rows'].append(row)
    ev['simulation'] = sim
    ev['stationSimulation'] = station_simulation(P10, rng)
    r2 = np.random.default_rng(20261117)   # its own seed, so adding it left every earlier interval unchanged
    ev['pooledFirstTwo'] = {'byDelay': block(P10[:2], METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'delay', r2),
                            'byDay': block(P10[:2], METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'day', r2)}
    return ev

def schedule_tables():
    """Scheduled alternatives from data/planb.json and data/planb_times.json (the files the page uses)."""
    pb = json.load(open(os.path.join(OUT, 'planb.json'))); pt = json.load(open(os.path.join(OUT, 'planb_times.json')))
    def active(ymd, dow):
        on = set()
        for w in pt['calendar']['weekly']:
            if w['from'] <= ymd <= w['to'] and w['days'][dow]: on.add(w['s'])
        for s, dd, ty in pt['calendar']['dates']:
            if dd == ymd: (on.add(s) if ty == 1 else on.discard(s))
        return on
    def dec(st):
        t = 0; out = []
        for x in (st.split('.') if st else []): t += int(x, 36); out.append(t)
        return out
    # One ordinary week inside the schedule stands in for each day type: Tue Nov 17, Sat Nov 21, Sun Nov 22, 2026.
    days = {'weekday': active('20261117', 1), 'saturday': active('20261121', 5), 'sunday': active('20261122', 6)}
    deps = {dt: [[np.array(sorted({m for s in svc for m in dec(v.get(s))})) for v in pat] for pat in pt['times']] for dt, svc in days.items()}
    return pb, deps

_TABLES = {}
def switch_rows(parts):
    """For each delay, the scheduled switch cost in each direction along its line (None where no alternative leaves within 3 hours)."""
    if not _TABLES:
        pb, deps = schedule_tables()
        cands = {}
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
                            if abs(pos[s2] - a) > MAX_STEPS: break   # a crosstown jump (such as across the U of Line 1) is not a way past the delay
                            dirn = 1 if pos[s2] > a else -1
                            walk = max(1, int(np.ceil(v['metres'] / 80)))
                            cands.setdefault((v['station'], l, dirn), []).append((pi, i, walk, q['visits'][j]['ride'] - v['ride'], abs(cum[pos[s2]] - cum[a])))
                            break
        _TABLES.update(pb=pb, deps=deps, cands=cands)
    pb, deps, cands = _TABLES['pb'], _TABLES['deps'], _TABLES['cands']
    rows = []; raw_extra = []
    for q in parts:
        for r in range(len(q['y'])):
            st, l, t = q['station'][r], q['line'][r], int(q['tmin'][r])
            dt = 'saturday' if q['day'][r] == 'Saturday' else 'sunday' if q['day'][r] == 'Sunday' else 'weekday'
            order = pb['lines'].get(l, [])
            dirs = []
            if st in order:
                a = order.index(st)
                for dirn in (1, -1):
                    if 0 <= a + dirn < len(order):   # a direction exists past this station
                        best = None
                        for pi, i, walk, ride, sub in cands.get((st, l, dirn), []):
                            arr = deps[dt][pi][i]; e = t + walk + BOARD_MIN
                            k = np.searchsorted(arr, e)
                            if k < len(arr) and arr[k] - t <= 180:
                                extra = arr[k] + ride - t - sub
                                raw_extra.append(extra)
                                extra = max(extra, 0)   # the simulation never lets a bus beat an on time subway
                                best = extra if best is None else min(best, extra)
                        dirs.append(best)
            rows.append(dirs)
    return rows, raw_extra

def station_simulation(P10, rng):
    """A decision simulation with a switch cost for each station and time from the schedule.
    For each test delay and each direction of travel along its line: walking to the stop (80 metres a minute) plus 1 minute
    to board, waiting for the next scheduled departure after that, and the scheduled ride to the first station past the delay
    (at most 3 stops along the line),
    minus the scheduled subway time for the same two stations (floored at 0, since the subway's own wait for a train is
    not modelled). Waiting costs the logged delay minutes, capped at 60.
    A rider switches when the forecast is 35% or more and an alternative leaves within 3 hours in their direction."""
    rows, raw_extra = switch_rows(P10)
    n = len(rows)
    y = np.concatenate([q['y'] for q in P10]); D = np.minimum(np.concatenate([q['minutes'] for q in P10]), WAIT_CAP)
    P = {m: np.concatenate([q[m] for q in P10]) for m in METHODS}
    def cost(policy):
        out = np.empty(n)
        for r, dirs in enumerate(rows):
            if not dirs: out[r] = D[r]; continue
            out[r] = np.mean([D[r] if (x is None or not policy(r, x)) else x for x in dirs])
        return out
    pol = {'alwaysWait': lambda r, x: False, 'alwaysSwitch': lambda r, x: True, 'hindsightBest': lambda r, x: x < D[r]}
    for m in METHODS: pol[m] = (lambda mm: lambda r, x: P[mm][r] >= SWITCH_AT)(m)
    C = {k: cost(f) for k, f in pol.items()}
    pairs = [x for dirs in rows for x in dirs]
    have = [x for x in pairs if x is not None]
    subsets = {'all': np.ones(n, bool), 'atLeast20': D >= 20, 'atLeast30': D >= 30, 'under10': D < 10}
    res = {'assumptions': {'maxStopsAlongLine': MAX_STEPS, 'waitCostIsLoggedDelayMinutesCappedAt': WAIT_CAP, 'switchAt': SWITCH_AT, 'walkMetresPerMinute': 80, 'boardingMinutes': BOARD_MIN,
                           'maxWaitForDepartureMinutes': 180, 'scheduleDays': 'Tue Nov 17, Sat Nov 21 and Sun Nov 22, 2026 stand in for each day type'},
           'delays': n, 'directions': len(pairs), 'directionsWithAlternative': len(have),
           'medianSwitchCost': round(float(np.median(have)), 1) if have else None,
           'candidateCostsBelowZeroBeforeClamp': round(float(np.mean(np.array(raw_extra) < 0)), 3),
           'subsets': {}}
    sizes = [len(q['y']) for q in P10]
    draw = resampler(P10, 'day', rng)
    idxs = [draw() for _ in range(BOOT)]
    for name, mask in subsets.items():
        row = {'delays': int(mask.sum())}
        for k in C: row[k] = round(float(C[k][mask].mean()), 2)
        for k in ['waitOrWalk', 'causeOnly', 'firstModel', 'hindsightBest']:
            saved = C['alwaysWait'] - C[k]
            vals = [saved[i][mask[i]].mean() for i in idxs]
            row['savedVsWait_' + k] = {'value': round(float(saved[mask].mean()), 2), 'low': round(float(np.percentile(vals, 2.5)), 2), 'high': round(float(np.percentile(vals, 97.5)), 2)}
        for other in ['causeOnly', 'firstModel']:
            diff = C[other] - C['waitOrWalk']
            vals = [diff[i][mask[i]].mean() for i in idxs]
            row['savedVs_' + other] = {'value': round(float(diff[mask].mean()), 2), 'low': round(float(np.percentile(vals, 2.5)), 2), 'high': round(float(np.percentile(vals, 97.5)), 2)}
        res['subsets'][name] = row
    return res

def policy_costs(rows, D, switch):
    """Average minutes over directions: switch(r, x) says whether to switch for delay r with switch cost x."""
    out = np.empty(len(rows))
    for r, dirs in enumerate(rows):
        out[r] = D[r] if not dirs else np.mean([D[r] if (x is None or not switch(r, x)) else x for x in dirs])
    return out

P20_GRID = [round(0.02 + 0.01 * i, 2) for i in range(39)]
MARGIN_GRID = [round(-5 + 0.5 * i, 1) for i in range(41)]
def policy_test(preds, calsets, names, rng):
    """Decision rules whose threshold is picked on earlier data only (each period's recalibration window, which ends
    before the period), then tested on that period. P20: switch when the 20+ chance reaches t. Expected cost: switch when
    the expected wait from the three bands minus the station's scheduled switch cost reaches a margin."""
    def exp_wait(p5, p10, p20, bm):
        return (1 - p5) * bm[0] + (p5 - p10) * bm[1] + (p10 - p20) * bm[2] + p20 * bm[3]
    chosen = []; tests = []
    for k, cs in enumerate(calsets):
        rows_c, _ = switch_rows([cs]); Dc = np.minimum(cs['minutes'], WAIT_CAP)
        t_best = min(P20_GRID, key=lambda t: policy_costs(rows_c, Dc, lambda r, x: cs['p20'][r] >= t).mean())
        ew_c = exp_wait(cs['p5'], cs['p10'], cs['p20'], cs['binMeans'])
        m_best = min(MARGIN_GRID, key=lambda mg: policy_costs(rows_c, Dc, lambda r, x: ew_c[r] - x >= mg).mean())
        te = {q: preds[10][k][q] for q in ['minutes', 'date', 'station', 'line', 'tmin', 'day', 'y']}
        te.update(p5=preds[5][k]['waitOrWalk'], p10=preds[10][k]['waitOrWalk'], p20=preds[20][k]['waitOrWalk'], cause=preds[10][k]['causeOnly'])
        rows_t, _ = switch_rows([te]); Dt = np.minimum(te['minutes'], WAIT_CAP)
        ew_t = exp_wait(te['p5'], te['p10'], te['p20'], cs['binMeans'])
        C = {'alwaysWait': policy_costs(rows_t, Dt, lambda r, x: False),
             'causeOnly35': policy_costs(rows_t, Dt, lambda r, x: te['cause'][r] >= SWITCH_AT),
             'current35': policy_costs(rows_t, Dt, lambda r, x: te['p10'][r] >= SWITCH_AT),
             'p20Rule': policy_costs(rows_t, Dt, lambda r, x: te['p20'][r] >= t_best),
             'expectedCost': policy_costs(rows_t, Dt, lambda r, x: ew_t[r] - x >= m_best)}
        chosen.append({'test': names[k], 'chosenOn': cs['calibratedOn'], 'p20Threshold': t_best, 'expectedCostMargin': m_best})
        tests.append(dict(C, date=te['date'], D=Dt, y=te['y']))
    allC = {q: np.concatenate([t[q] for t in tests]) for q in tests[0] if q not in ('date', 'D', 'y')}
    D = np.concatenate([t['D'] for t in tests])
    parts = [{'y': t['y'], 'date': t['date']} for t in tests]
    draw = resampler(parts, 'day', rng); idxs = [draw() for _ in range(BOOT)]
    subsets = {'all': np.ones(len(D), bool), 'under10': D < 10, 'atLeast20': D >= 20, 'atLeast30': D >= 30}
    def ci(diff, mask):
        vals = [diff[i][mask[i]].mean() for i in idxs]
        return {'value': round(float(diff[mask].mean()), 2), 'low': round(float(np.percentile(vals, 2.5)), 2), 'high': round(float(np.percentile(vals, 97.5)), 2)}
    res = {'chosen': chosen, 'subsets': {}}
    for name, mask in subsets.items():
        row = {'delays': int(mask.sum())}
        for q in allC: row[q] = round(float(allC[q][mask].mean()), 2)
        for q in ['p20Rule', 'expectedCost']:
            row[q + '_savedVsCurrent'] = ci(allC['current35'] - allC[q], mask)
            row[q + '_savedVsWait'] = ci(allC['alwaysWait'] - allC[q], mask)
            row[q + '_savedVsCause'] = ci(allC['causeOnly35'] - allC[q], mask)
        row['current35_savedVsWait'] = ci(allC['alwaysWait'] - allC['current35'], mask)
        res['subsets'][name] = row
    a = res['subsets']['all']
    res['shipped'] = None
    for q in ['p20Rule', 'expectedCost']:
        if a[q + '_savedVsCurrent']['low'] > 0 and a[q + '_savedVsWait']['low'] > 0: res['shipped'] = q
    return res

def build_stations(gz):
    r = pd.read_csv(gz.open('routes.txt')); s = pd.read_csv(gz.open('stops.txt'))
    t = pd.read_csv(gz.open('trips.txt'), usecols=['route_id', 'trip_id'])
    st = pd.read_csv(gz.open('stop_times.txt'), usecols=['trip_id', 'stop_id'])
    sr = st.merge(t, on='trip_id')[['stop_id', 'route_id']].drop_duplicates().merge(r[['route_id', 'route_short_name', 'route_long_name', 'route_type']], on='route_id')
    line_of = {1: 'YU', 2: 'BD', 4: 'SHP'}
    sub = sr[sr.route_type == 1].merge(s, on='stop_id')
    sub['name'] = sub.stop_name.str.replace(r'\s+-\s+.*$', '', regex=True).str.replace(r'\s+Station$', '', regex=True).str.strip()
    surf = sr[sr.route_type.isin([0, 3])].merge(s, on='stop_id')
    out = []
    for name, g in sub.groupby('name'):
        lat, lon = g.stop_lat.mean(), g.stop_lon.mean()
        dy = (surf.stop_lat - lat) * 111320; dx = (surf.stop_lon - lon) * 111320 * np.cos(np.radians(lat))
        dist = np.sqrt(dx * dx + dy * dy)
        near = surf.assign(m=dist)[dist <= 300].sort_values('m').drop_duplicates('route_id')
        routes = [{'route': str(x.route_short_name), 'name': str(x.route_long_name).title(), 'kind': 'streetcar' if x.route_type == 0 else 'bus',
                   'stop': re.sub(r'\s+-\s+', ', ', str(x.stop_name)), 'metres': int(round(x.m / 10) * 10), 'night': (str(x.route_short_name).isdigit() and 300 <= int(x.route_short_name) <= 399)} for x in near.itertuples()]
        label = {'Bloor': 'Bloor-Yonge (Line 1)', 'Yonge': 'Bloor-Yonge (Line 2)'}.get(name, name)
        out.append({'name': name, 'label': label, 'lines': sorted({line_of[int(i)] for i in g.route_id}), 'lat': round(lat, 5), 'lon': round(lon, 5), 'nearby': routes})
    return out

if __name__ == '__main__':
    main()
