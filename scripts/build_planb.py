"""Build data/planb.json from the TTC GTFS schedule.

For every bus and streetcar stop pattern (the stop sequences that run at least 5% of a
route direction's trips), record which subway stations it passes within 300 metres, in order,
with the boarding stop, the direction it is heading and the median scheduled ride time between
station visits. Also records the station order and scheduled running time of each subway line. Run: python3 scripts/build_planb.py [cache_dir]
"""
import json, os, re, sys, zipfile
from collections import defaultdict
import numpy as np, pandas as pd

CACHE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ttc'
TIMES_OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'planb_times.json')

def b36(n):
    s = ''
    while True:
        n, r = divmod(n, 36); s = '0123456789abcdefghijklmnopqrstuvwxyz'[r] + s
        if not n: return s

def mins(t):
    h, m, s = (int(x) for x in t.split(':'))
    return h * 60 + m
RADIUS = 300
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'planb.json')

def clean(s):
    return re.sub(r'\s+-\s+', ', ', str(s)).strip()

def headsign(h):
    h = str(h)
    m = re.match(r'^(North|South|East|West)\s*-\s*.*?towards\s+(.*)$', h, re.I)
    if m: return f'{m.group(1).title()} towards {m.group(2).strip()}'
    return re.sub(r'\s+-\s+', ', ', h).strip()

def main():
    gz = zipfile.ZipFile(os.path.join(CACHE, 'gtfs.zip'))
    routes = pd.read_csv(gz.open('routes.txt'))
    stops = pd.read_csv(gz.open('stops.txt')).set_index('stop_id')
    trips = pd.read_csv(gz.open('trips.txt'), usecols=['route_id', 'service_id', 'trip_id', 'direction_id', 'trip_headsign'])
    st = pd.read_csv(gz.open('stop_times.txt'), usecols=['trip_id', 'stop_id', 'stop_sequence', 'departure_time']).sort_values(['trip_id', 'stop_sequence'])
    seqs = st.groupby('trip_id').stop_id.apply(tuple)
    deps = st.groupby('trip_id').departure_time.apply(tuple)
    trips['seq'] = trips.trip_id.map(seqs)
    trips = trips.merge(routes[['route_id', 'route_short_name', 'route_long_name', 'route_type']], on='route_id')

    sub = trips[trips.route_type == 1]
    def sname(sid):
        n = stops.at[sid, 'stop_name']
        return re.sub(r'\s+Station$', '', re.sub(r'\s+-\s+.*$', '', n)).strip()
    line_of = {1: 'YU', 2: 'BD', 4: 'SHP'}
    lines = {}; subway_min = {}
    sub = sub.assign(deps=sub.trip_id.map(deps))
    for rid, g in sub.groupby('route_id'):
        best = g[g.direction_id == 0].seq.value_counts().index[0]
        bt = g[g.seq == best]
        order = []; cum = []
        for k, sid in enumerate(best):
            n = sname(sid)
            if not order or order[-1] != n:
                order.append(n)
                cum.append(float(np.median([mins(dd[k]) - mins(dd[0]) for dd in bt.deps])))
        lines[line_of[int(rid)]] = order
        subway_min[line_of[int(rid)]] = cum
    stations = {}
    for sid in set(s for q in sub.seq for s in q):
        stations.setdefault(sname(sid), []).append((stops.at[sid, 'stop_lat'], stops.at[sid, 'stop_lon']))
    centre = {n: (np.mean([a for a, _ in v]), np.mean([b for _, b in v])) for n, v in stations.items()}
    names = sorted(centre)
    cy = np.array([centre[n][0] for n in names]); cx = np.array([centre[n][1] for n in names])

    surf = trips[trips.route_type.isin([0, 3])]
    near = {}
    for sid in set(s for q in surf.seq for s in q):
        dy = (stops.at[sid, 'stop_lat'] - cy) * 111320; dx = (stops.at[sid, 'stop_lon'] - cx) * 111320 * np.cos(np.radians(cy))
        d = np.sqrt(dx * dx + dy * dy); i = int(d.argmin())
        if d[i] <= RADIUS: near[sid] = (names[i], float(d[i]))

    patterns = []; times = []
    surf = surf.assign(deps=surf.trip_id.map(deps))
    for (rid, did), g in surf.groupby(['route_id', 'direction_id']):
        counts = g.groupby('seq').size().sort_values(ascending=False)
        total = counts.sum()
        for seq, c in counts.items():
            if c / total < 0.05: continue
            visits = []
            for k, sid in enumerate(seq):
                if sid in near:
                    n, d = near[sid]
                    v = {'station': n, 'stop': clean(stops.at[sid, 'stop_name']), 'metres': int(round(d / 10) * 10), 'access': int(stops.at[sid, 'wheelchair_boarding']) if not pd.isna(stops.at[sid, 'wheelchair_boarding']) else 0, 'k': k, 'end': int(k >= len(seq) - 2)}
                    if visits and visits[-1]['station'] == n:
                        if d < visits[-1]['metres']: visits[-1].update(v)
                        continue
                    visits.append(v)
            if not visits: continue
            pt = g[g.seq == seq]
            for v in visits:  # median scheduled minutes from the first station visit, for ride time estimates
                v['ride'] = int(round(float(np.median([mins(dd[v['k']]) - mins(dd[visits[0]['k']]) for dd in pt.deps]))))
            vt = []
            for v in visits:
                by = defaultdict(list)
                for svc, dd in zip(pt.service_id, pt.deps): by[str(svc)].append(mins(dd[v['k']]))
                enc = {}
                for svc, L in by.items():
                    L.sort(); prev = 0; out = []
                    for m in L: out.append(b36(m - prev)); prev = m
                    enc[svc] = '.'.join(out)
                vt.append(enc)
                del v['k']
                if not v['end']: del v['end']
            times.append(vt)
            hs = g[g.seq == seq].trip_headsign.value_counts().index[0]
            r = g.iloc[0]
            patterns.append({'route': str(r.route_short_name), 'name': str(r.route_long_name).title(), 'kind': 'LRT' if str(r.route_long_name).startswith('Line ') else ('streetcar' if r.route_type == 0 else 'bus'),
                             'night': (str(r.route_short_name).isdigit() and 300 <= int(r.route_short_name) <= 399), 'heading': headsign(hs), 'share': round(float(c / total), 2), 'visits': visits})
    out = {'source': 'TTC Routes and Schedules (GTFS), City of Toronto Open Data, schedule files dated Oct 20, 2026', 'radiusMetres': RADIUS, 'lines': lines, 'subwayMinutes': subway_min, 'patterns': patterns}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    cal = pd.read_csv(gz.open('calendar.txt')); cd = pd.read_csv(gz.open('calendar_dates.txt'))
    calendar = {'weekly': [{'s': str(r.service_id), 'days': [int(getattr(r, d)) for d in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']], 'from': str(r.start_date), 'to': str(r.end_date)} for r in cal.itertuples()],
                'dates': [[str(r.service_id), str(r.date), int(r.exception_type)] for r in cd.itertuples()]}
    json.dump({'calendar': calendar, 'times': times}, open(TIMES_OUT, 'w'), separators=(',', ':'))
    print('times', os.path.getsize(TIMES_OUT))
    print(len(patterns), {k: len(v) for k, v in lines.items()}, os.path.getsize(OUT))

if __name__ == '__main__':
    main()
