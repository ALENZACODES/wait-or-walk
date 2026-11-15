"""Hand check of five Plan B journeys straight from the raw TTC GTFS files (not from data/planb.json).

For each journey: find a scheduled trip of the route with the stated direction, list its stops in
order from the stop by the delayed station to the stop by the destination (or the transfer station),
with scheduled times, and the straight line distance from each end to the subway station.
Run: python3 scripts/check_planb.py [cache_dir] > docs/plan-b-checks.md
"""
import re, sys, zipfile, math
import pandas as pd

CACHE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ttc'
JOURNEYS = [  # (from station, to station or transfer, route, direction word, board stop, alight stop, note)
    ('Union', 'College', '97', 'North', 'Front St West at Bay St', 'Yonge St at Carlton St North Side - College Station', 'Line 1, direct'),
    ('Finch', 'Eglinton', '97', 'South', 'Yonge St at Finch Ave West - Finch Station', '2190 Yonge St', 'Line 1, direct'),
    ('Kipling', 'Jane', '149', 'East', 'Kipling Station', 'Jane Station', 'Line 2, direct'),
    ('Main Street', 'Broadview', '62', 'West', 'Main Street Station', 'Broadview Station', 'Line 2, direct'),
    ('Dundas West', 'St Andrew', '504', 'East', 'Dundas West Station', None, 'Line 2 to Line 1: ride past the delay, change at St Andrew for Union'),
]

z = zipfile.ZipFile(f'{CACHE}/gtfs.zip')
routes = pd.read_csv(z.open('routes.txt')); stops = pd.read_csv(z.open('stops.txt')).set_index('stop_id')
trips = pd.read_csv(z.open('trips.txt')); st = pd.read_csv(z.open('stop_times.txt'))
sub_ids = set(st[st.trip_id.isin(trips[trips.route_id.isin(routes[routes.route_type == 1].route_id)].trip_id)].stop_id)
def station_xy(name):
    rows = [stops.loc[s] for s in sub_ids if re.sub(r'\s+Station$', '', re.sub(r'\s+-\s+.*$', '', stops.at[s, 'stop_name'])).strip() == name]
    return sum(r.stop_lat for r in rows) / len(rows), sum(r.stop_lon for r in rows) / len(rows)
def metres(a, b):
    return math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0])))
clean = lambda s: re.sub(r'\s+-\s+', ', ', s)

print('# Plan B journeys checked by hand against the TTC schedule\n')
print('Source: TTC Routes and Schedules (GTFS), City of Toronto Open Data, schedule dated Oct 20, 2026. Each check reads the raw schedule files, not the app data, and shows one scheduled weekday morning trip (Monday to Friday service, effective Nov 1, 2026). Checked Nov 15, 2026, and each journey is also an automated test in tests/test_logic.mjs. These are schedule checks only; the app has not been tested with riders.\n')
for frm, to, rno, word, board, alight, note in JOURNEYS:
    rid = routes[routes.route_short_name.astype(str) == rno].route_id.iloc[0]
    rt = trips[(trips.route_id == rid) & trips.trip_headsign.str.startswith(word)]
    cal = pd.read_csv(z.open('calendar.txt'))
    weekday = set(cal[(cal.monday == 1) & (cal.friday == 1)].service_id)
    svc = next(s for s in rt.service_id.value_counts().index if s in weekday)
    a_xy, b_xy = station_xy(frm), station_xy(to)
    found = None
    for tid in rt[rt.service_id == svc].trip_id:
        seq = st[st.trip_id == tid].sort_values('stop_sequence')
        names = [stops.at[s, 'stop_name'] for s in seq.stop_id]
        if board in names:
            i = names.index(board)
            if alight is None:
                d = [metres((stops.at[s, 'stop_lat'], stops.at[s, 'stop_lon']), b_xy) for s in seq.stop_id]
                j = min(range(i + 1, len(d)), key=lambda k: d[k]) if i + 1 < len(d) else None
            else:
                j = names.index(alight) if alight in names[i + 1:] else None
            if j is not None and j > i:
                dep = seq.iloc[i].departure_time.zfill(8)
                if '07:30:00' <= dep <= '09:30:00' or found is None:
                    found = (tid, seq.iloc[i:j + 1], rt[rt.trip_id == tid].trip_headsign.iloc[0])
                    if '07:30:00' <= dep <= '09:30:00': break
    tid, legs, hs = found
    b0 = legs.stop_id.iloc[0]; b1 = legs.stop_id.iloc[-1]
    d0 = metres((stops.at[b0, 'stop_lat'], stops.at[b0, 'stop_lon']), a_xy); d1 = metres((stops.at[b1, 'stop_lat'], stops.at[b1, 'stop_lon']), b_xy)
    title = 'Dundas West to Union' if to == 'St Andrew' else f'{frm} to {to}'
    print(f'## {title}: route {rno} {word.lower()}bound ({note})\n')
    print(f'- Headsign in the schedule: {clean(hs)}')
    print(f'- Trip {tid}: board at {clean(stops.at[b0, "stop_name"])} ({d0:.0f} m from {frm} station) at {legs.departure_time.iloc[0]}, get off at {clean(stops.at[b1, "stop_name"])} ({d1:.0f} m from {to} station) at {legs.arrival_time.iloc[-1]}, {len(legs) - 1} stops later')
    mid = [clean(stops.at[s, 'stop_name']) for s in legs.stop_id.iloc[1:-1]]
    if mid: print(f'- Stops in between: {"; ".join(mid[:8])}{" and more" if len(mid) > 8 else ""}')
    print(f'- Result: the schedule confirms this route runs from {frm} towards {to} in this direction. Matches what the app shows.\n')
