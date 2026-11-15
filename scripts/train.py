"""Train the Wait or Walk model from City of Toronto open data.

Downloads (if missing) TTC Subway Delay Data since 2025 and the TTC GTFS schedule,
then writes data/model.json, data/metrics.json and data/parity.json.
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
    d['time'] = pd.cut(h, [-1, 5, 9, 15, 19, 23], labels=['night', 'am_peak', 'midday', 'pm_peak', 'evening']).astype(str)
    d['weekend'] = d.Day.isin(['Saturday', 'Sunday'])
    d['y'] = (d['Min Delay'] >= LONG).astype(int)
    d['dt'] = pd.to_datetime(d.Date)
    groups = list(GROUPS) + ['signals', 'track', 'train', 'operations', 'other']
    last = d.Date.max()

    def cols():
        c = ['group=' + g for g in groups] + ['station=' + s for s in sorted(names)] + ['station=Other']
        c += ['line=' + l for l in ['YU', 'BD', 'SHP']] + ['time=' + t for t in ['night', 'am_peak', 'midday', 'pm_peak', 'evening']] + ['weekend']
        return c
    COLS = cols()
    def X(df):
        m = np.zeros((len(df), len(COLS)))
        idx = {c: i for i, c in enumerate(COLS)}
        for r, (g, s, l, t, w) in enumerate(zip(df.group, df.station, df.Line, df.time, df.weekend)):
            m[r, idx['group=' + g]] = GROUP_SCALE
            for k in ('station=' + s, 'line=' + l, 'time=' + t):
                m[r, idx[k]] = 1
            if w: m[r, idx['weekend']] = 1
        return m
    def weights(df, ref):
        return 0.5 ** ((pd.Timestamp(ref) - df.dt).dt.days.values / HALF_LIFE_DAYS)
    def fit(df, ref):
        return LogisticRegression(C=0.5, max_iter=5000).fit(X(df), df.y, sample_weight=weights(df, ref))
    logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    sig = lambda z: 1 / (1 + np.exp(-z))
    def platt(m, cal):
        z = logit(m.predict_proba(X(cal))[:, 1]).reshape(-1, 1)
        pl = LogisticRegression(C=1e6).fit(z, cal.y)
        return float(pl.coef_[0][0]), float(pl.intercept_[0])
    def group_rate(tr, ref):
        w = weights(tr, ref)
        g = pd.DataFrame({'g': tr.group.values, 'y': tr.y.values, 'w': w})
        prior = (g.y * g.w).sum() / g.w.sum()
        num = (g.y * g.w).groupby(g.g).sum(); den = g.w.groupby(g.g).sum()
        return ((num + prior * 10) / (den + 10)).to_dict(), prior
    def pipeline(tr, cal_start):
        """The exact deployed process: base model on data before cal_start, Platt on cal_start onward. No refit."""
        base = tr[tr.Date < cal_start]; cal = tr[tr.Date >= cal_start]
        m = fit(base, cal_start)
        a, b = platt(m, cal)
        return m, a, b, base, cal
    def cal_start_for(ref):
        return (pd.Timestamp(ref) - pd.Timedelta(days=CAL_DAYS)).strftime('%Y-%m-%d')
    def score(y, p):
        return {'auc': round(float(roc_auc_score(y, p)), 3), 'brier': round(float(brier_score_loss(y, p)), 4), 'logLoss': round(float(log_loss(y, p)), 4), 'meanPredicted': round(float(np.mean(p)), 3)}
    def bins(y, p, edges=(0, .05, .1, .15, .2, .3, .45, 1.01)):
        out = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            k = (p >= lo) & (p < hi)
            if k.sum(): out.append({'from': lo, 'to': min(hi, 1), 'delays': int(k.sum()), 'predicted': round(float(p[k].mean()), 3), 'actual': round(float(np.asarray(y)[k].mean()), 3)})
        return out

    folds = []; pooled_y = []; pooled_p = []; preds = []
    for start, end in [('2026-01-01', '2026-04-01'), ('2026-04-01', '2026-07-01'), ('2026-07-01', '2026-10-01')]:
        tr = d[d.Date < start]; te = d[(d.Date >= start) & (d.Date < end)]
        cs = cal_start_for(start)
        m, a, b, base, cal = pipeline(tr, cs)
        raw = m.predict_proba(X(te))[:, 1]
        p = sig(a * logit(raw) + b)
        rate, prior = group_rate(base, cs)
        cr_cal = np.array([rate.get(g, prior) for g in cal.group]); cr_te = np.array([rate.get(g, prior) for g in te.group])
        pl = LogisticRegression(C=1e6).fit(logit(cr_cal).reshape(-1, 1), cal.y)
        cr_te_cal = sig(pl.coef_[0][0] * logit(cr_te) + pl.intercept_[0])
        m_raw = LogisticRegression(C=0.5, max_iter=5000).fit(X(tr), tr.y)
        pooled_y += list(te.y); pooled_p += list(p)
        preds.append({'y': te.y.values, 'minutes': te['Min Delay'].values.astype(float), 'waitOrWalk': p, 'causeOnly': cr_te_cal, 'firstModel': m_raw.predict_proba(X(te))[:, 1]})
        folds.append({'test': f'{start} to {te.Date.max()}', 'baseTrainedThrough': base.Date.max(), 'calibratedOn': f'{cal.Date.min()} to {cal.Date.max()}',
                      'testDelays': int(len(te)), 'actualShareLong': round(float(te.y.mean()), 3),
                      'overallRate': score(te.y, np.full(len(te), tr.y.mean())),
                      'causeOnlyRate': score(te.y, cr_te_cal),
                      'firstModel': score(te.y, m_raw.predict_proba(X(te))[:, 1]),
                      'beforeCalibration': score(te.y, raw),
                      'waitOrWalk': score(te.y, p),
                      'reliability': bins(te.y.values, p)})

    cs = cal_start_for((pd.Timestamp(last) + pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
    m, a, b, base, cal = pipeline(d, cs)
    w = dict(zip(COLS, (round(float(v) * (GROUP_SCALE if c.startswith('group=') else 1), 6) for c, v in zip(COLS, m.coef_[0]))))
    recent = d[d.Date >= cs]
    model = {'trainedThrough': last, 'baseTrainedThrough': base.Date.max(), 'calibratedOn': f'{cal.Date.min()} to {cal.Date.max()}', 'trainedFrom': d.Date.min(), 'delays': int(len(d)),
             'longMinutes': LONG, 'halfLifeDays': HALF_LIFE_DAYS, 'calibrationDays': CAL_DAYS,
             'intercept': round(float(m.intercept_[0]), 6), 'weights': w, 'platt': {'a': round(a, 6), 'b': round(b, 6)},
             'groups': {g: {'label': GROUPS[g][0] if g in GROUPS else EXTRA_LABELS[g], 'delays': int((d.group == g).sum()),
                            'longDelays': int(((d.group == g) & (d.y == 1)).sum()),
                            'medianMinutes': float(d[d.group == g]['Min Delay'].median()) if (d.group == g).any() else None,
                            'recentShareLong': round(float(recent[recent.group == g].y.mean()), 3) if (recent.group == g).any() else None}
                        for g in groups},
             'stationDelays': {s: int(v) for s, v in d.station.value_counts().items()},
             'stations': stations,
             'source': 'City of Toronto Open Data: TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS). Open Government Licence Toronto.'}
    os.makedirs(OUT, exist_ok=True)
    json.dump(model, open(os.path.join(OUT, 'model.json'), 'w'), indent=1)
    pooled = {'tests': len(folds), 'delays': len(pooled_y), 'reliability': bins(np.array(pooled_y), np.array(pooled_p))}
    evidence = evaluate(preds, [f['test'] for f in folds], bins)
    json.dump({'folds': folds, 'pooled': pooled, 'evidence': evidence, 'zeroMinuteRecordsExcluded': int(zero_excluded),
               'monthlyShareLong': {k: round(float(v), 3) for k, v in d.groupby(d.Date.str.slice(0, 7)).y.mean().items()}},
              open(os.path.join(OUT, 'metrics.json'), 'w'), indent=1)
    samp = d.sample(30, random_state=7)
    ps = sig(a * logit(m.predict_proba(X(samp))[:, 1]) + b)
    json.dump([{'group': g, 'station': s, 'line': l, 'time': t, 'weekend': bool(wk), 'p': round(float(p), 6)} for g, s, l, t, wk, p in zip(samp.group, samp.station, samp.Line, samp.time, samp.weekend, ps)],
              open(os.path.join(OUT, 'parity.json'), 'w'), indent=1)
    print(json.dumps([{k: v for k, v in f.items() if k != 'reliability'} for f in folds], indent=1)); print(json.dumps(pooled))

METHODS = ['waitOrWalk', 'causeOnly', 'firstModel']
BOOT = 2000
SWITCH_COSTS = [8, 12, 15]   # simulation: extra minutes a rider spends by switching to a bus or streetcar
WAIT_CAP = 60                # simulation: a rider waits at most this many minutes before leaving anyway

def ece(y, p, edges=(0, .05, .1, .15, .2, .3, .45, 1.01)):
    tot = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        k = (p >= lo) & (p < hi)
        if k.sum(): tot += k.sum() * abs(p[k].mean() - y[k].mean())
    return tot / len(y)

def evaluate(preds, names, bins):
    """Bootstrap 95% intervals (resampling delays within each period), decision value at the risk band cut offs,
    and a transparent decision simulation. Everything is on the out of time evaluation periods."""
    rng = np.random.default_rng(20261115)
    def metrics(y, p):
        return {'auc': roc_auc_score(y, p), 'logLoss': log_loss(y, np.clip(p, 1e-6, 1 - 1e-6), labels=[0, 1]), 'brier': brier_score_loss(y, p), 'calError': ece(y, p)}
    def block(parts):
        y = np.concatenate([q['y'] for q in parts])
        P = {m: np.concatenate([q[m] for q in parts]) for m in METHODS}
        point = {m: metrics(y, P[m]) for m in METHODS}
        sizes = [len(q['y']) for q in parts]; offs = np.cumsum([0] + sizes[:-1])
        draws = {m: {k: [] for k in point[m]} for m in METHODS}
        for _ in range(BOOT):
            idx = np.concatenate([o + rng.integers(0, n, n) for o, n in zip(offs, sizes)])
            yy = y[idx]
            for m in METHODS:
                r = metrics(yy, P[m][idx])
                for k, v in r.items(): draws[m][k].append(v)
        out = {'delays': int(len(y)), 'methods': {}, 'differences': {}}
        for m in METHODS:
            out['methods'][m] = {k: {'value': round(float(point[m][k]), 4), 'low': round(float(np.percentile(draws[m][k], 2.5)), 4), 'high': round(float(np.percentile(draws[m][k], 97.5)), 4)} for k in point[m]}
        for other in ['causeOnly', 'firstModel']:
            dd = {}
            for k in point['waitOrWalk']:
                diff = np.array(draws['waitOrWalk'][k]) - np.array(draws[other][k])
                lo, hi = np.percentile(diff, [2.5, 97.5])
                dd[k] = {'value': round(float(point['waitOrWalk'][k] - point[other][k]), 4), 'low': round(float(lo), 4), 'high': round(float(hi), 4), 'distinguishable': bool(lo > 0 or hi < 0)}
            out['differences'][other] = dd
        return out
    ev = {'bootstrapResamples': BOOT, 'periods': [dict(test=n, **block([q])) for n, q in zip(names, preds)], 'pooled': block(preds)}
    # Decision value at the 15% and 35% cut offs, pooled over the three periods
    y = np.concatenate([q['y'] for q in preds]); mins_ = np.concatenate([q['minutes'] for q in preds])
    P = {m: np.concatenate([q[m] for q in preds]) for m in METHODS}
    dv = []
    for th in (0.15, 0.35):
        for m in METHODS:
            f = P[m] >= th
            dv.append({'threshold': th, 'method': m, 'flaggedShare': round(float(f.mean()), 3), 'longFlagged': round(float(f[y == 1].mean()), 3),
                       'falseFlagRate': round(float(f[y == 0].mean()), 3), 'flaggedThatWereLong': round(float(y[f].mean()), 3) if f.any() else None})
    ev['decisionValue'] = dv
    # Simulation: wait costs the logged delay minutes (capped), switching costs a fixed number of extra minutes
    wait = np.minimum(mins_, WAIT_CAP)
    sim = {'assumptions': {'waitCostIsLoggedDelayMinutesCappedAt': WAIT_CAP, 'switchCostsMinutes': SWITCH_COSTS, 'threshold': 0.35}, 'rows': []}
    for c in SWITCH_COSTS:
        row = {'switchCost': c, 'alwaysWait': round(float(wait.mean()), 2), 'alwaysSwitch': float(c), 'hindsightBest': round(float(np.minimum(wait, c).mean()), 2)}
        for m in ['causeOnly', 'waitOrWalk']:
            row[m] = round(float(np.where(P[m] >= 0.35, c, wait).mean()), 2)
        idxs = [rng.integers(0, len(y), len(y)) for _ in range(BOOT)]
        dif = [np.where(P['waitOrWalk'][i] >= 0.35, c, wait[i]).mean() - np.where(P['causeOnly'][i] >= 0.35, c, wait[i]).mean() for i in idxs]
        row['waitOrWalkMinusCauseOnly'] = {'value': round(row['waitOrWalk'] - row['causeOnly'], 2), 'low': round(float(np.percentile(dif, 2.5)), 2), 'high': round(float(np.percentile(dif, 97.5)), 2)}
        sim['rows'].append(row)
    ev['simulation'] = sim
    return ev

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
