"""Build data/planb.json from the TTC GTFS schedule.

For every bus and streetcar stop pattern (the stop sequences that run at least 5% of a
route direction's trips), record which subway stations it passes within 300 metres, in order,
with the boarding stop and the direction it is heading. Also records the station order of
each subway line. Run: python3 scripts/build_planb.py [cache_dir]
"""
import json, os, re, sys, zipfile
import numpy as np, pandas as pd

CACHE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ttc'
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
    trips = pd.read_csv(gz.open('trips.txt'), usecols=['route_id', 'trip_id', 'direction_id', 'trip_headsign'])
    st = pd.read_csv(gz.open('stop_times.txt'), usecols=['trip_id', 'stop_id', 'stop_sequence']).sort_values(['trip_id', 'stop_sequence'])
    seqs = st.groupby('trip_id').stop_id.apply(tuple)
    trips['seq'] = trips.trip_id.map(seqs)
    trips = trips.merge(routes[['route_id', 'route_short_name', 'route_long_name', 'route_type']], on='route_id')

    sub = trips[trips.route_type == 1]
    def sname(sid):
        n = stops.at[sid, 'stop_name']
        return re.sub(r'\s+Station$', '', re.sub(r'\s+-\s+.*$', '', n)).strip()
    line_of = {1: 'YU', 2: 'BD', 4: 'SHP'}
    lines = {}
    for rid, g in sub.groupby('route_id'):
        best = g[g.direction_id == 0].seq.value_counts().index[0]
        order = []
        for sid in best:
            n = sname(sid)
            if not order or order[-1] != n: order.append(n)
        lines[line_of[int(rid)]] = order
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

    patterns = []
    for (rid, did), g in surf.groupby(['route_id', 'direction_id']):
        counts = g.groupby('seq').size().sort_values(ascending=False)
        total = counts.sum()
        for seq, c in counts.items():
            if c / total < 0.05: continue
            visits = []
            for sid in seq:
                if sid in near:
                    n, d = near[sid]
                    if visits and visits[-1]['station'] == n:
                        if d < visits[-1]['metres']: visits[-1].update(stop=clean(stops.at[sid, 'stop_name']), metres=int(round(d / 10) * 10))
                        continue
                    visits.append({'station': n, 'stop': clean(stops.at[sid, 'stop_name']), 'metres': int(round(d / 10) * 10)})
            if not visits: continue
            hs = g[g.seq == seq].trip_headsign.value_counts().index[0]
            r = g.iloc[0]
            patterns.append({'route': str(r.route_short_name), 'name': str(r.route_long_name).title(), 'kind': 'streetcar' if r.route_type == 0 else 'bus',
                             'night': str(r.route_short_name).startswith('3'), 'heading': headsign(hs), 'share': round(float(c / total), 2), 'visits': visits})
    out = {'source': 'TTC Routes and Schedules (GTFS), City of Toronto Open Data, schedule files dated Oct 20, 2026', 'radiusMetres': RADIUS, 'lines': lines, 'patterns': patterns}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    print(len(patterns), {k: len(v) for k, v in lines.items()}, os.path.getsize(OUT))

if __name__ == '__main__':
    main()
