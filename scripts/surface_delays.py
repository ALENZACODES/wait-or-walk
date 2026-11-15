"""Logged bus and streetcar delays per route, to qualify Plan B (shown behind the Plan B fold).

Sources (City of Toronto Open Data, Open Government Licence Toronto):
  TTC Bus Delay Data, ttc-bus-delay-data-since-2025.csv, and TTC Streetcar Delay Data, ttc-streetcar-delay-data-since-2025.csv
  TTC Routes and Schedules (GTFS), for scheduled trips per week (week of Nov 16, 2026)
What it measures: logged incidents with a recorded delay of 10 minutes or more, per week and per 100 scheduled trips.
That is a count of reported incidents, not on-time performance; a route can run late without an incident being logged.

Check before showing anything: the rate per route in the earlier window (2025) is compared with the later window
(Jan to Sep 2026), on routes with at least 200 scheduled trips a week. The page shows the line only if the earlier rate
ranks routes well (Spearman 0.7 or more) and beats the network average as a guess for the later rate.
Run: python3 scripts/surface_delays.py /path/to/bus.csv /path/to/streetcar.csv /path/to/gtfs.zip
"""
import json, os, sys, zipfile
import pandas as pd
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'data', 'surface_delays.json')
THR, MIN_TRIPS = 10, 200
EARLY, LATE = ('2025-01-01', '2025-12-31'), ('2026-01-01', None)

def load(bus, streetcar):
    d = pd.concat([pd.read_csv(bus).assign(mode='bus'), pd.read_csv(streetcar).assign(mode='streetcar')])
    d['date'] = pd.to_datetime(d['Date'].astype(str).str[:10]); d['route'] = d['Line'].astype(str).str.extract(r'^(\d+)')[0]
    d['min'] = pd.to_numeric(d['Min Delay'], errors='coerce').fillna(0)
    return d.dropna(subset=['route'])

def weekly_trips(gtfs):
    z = zipfile.ZipFile(gtfs)
    routes = pd.read_csv(z.open('routes.txt'), dtype={'route_short_name': str}); trips = pd.read_csv(z.open('trips.txt'))
    cal = pd.read_csv(z.open('calendar.txt')) if 'calendar.txt' in z.namelist() else None
    cd = pd.read_csv(z.open('calendar_dates.txt')) if 'calendar_dates.txt' in z.namelist() else None
    tr = trips.merge(routes[['route_id', 'route_short_name']], on='route_id'); wk = {}
    for day in pd.date_range('2026-11-16', '2026-11-22'):
        ds = int(day.strftime('%Y%m%d')); dn = day.strftime('%A').lower(); sv = set()
        if cal is not None: sv = set(cal[(cal.start_date <= ds) & (cal.end_date >= ds) & (cal[dn] == 1)].service_id)
        if cd is not None:
            x = cd[cd.date == ds]; sv |= set(x[x.exception_type == 1].service_id); sv -= set(x[x.exception_type == 2].service_id)
        for k, v in tr[tr.service_id.isin(sv)].groupby('route_short_name').size().items(): wk[str(k)] = wk.get(str(k), 0) + int(v)
    return pd.Series(wk)

def per_week(d, a, b):
    b = b or d.date.max().strftime('%Y-%m-%d')
    x = d[(d.date >= a) & (d.date <= b) & (d['min'] >= THR)]
    return x.groupby('route').size() / (((pd.Timestamp(b) - pd.Timestamp(a)).days + 1) / 7), b

def main(bus, streetcar, gtfs):
    d = load(bus, streetcar); wk = weekly_trips(gtfs)
    e, _ = per_week(d, *EARLY); l, last = per_week(d, *LATE)
    df = pd.DataFrame({'e': e, 'l': l, 'trips': wk}).fillna({'e': 0, 'l': 0}).dropna()
    df = df[df.trips >= MIN_TRIPS]
    df['pe'] = df.e / df.trips * 100; df['pl'] = df.l / df.trips * 100
    rho = float(spearmanr(df.pe, df.pl)[0])
    mae_route = float((df.pe - df.pl).abs().mean()); mae_net = float((df.pe.mean() - df.pl).abs().mean())
    ok = rho >= 0.7 and mae_route < mae_net
    q1, q2 = df.pl.quantile(1 / 3), df.pl.quantile(2 / 3)
    out = {'source': 'City of Toronto Open Data: TTC Bus Delay Data and TTC Streetcar Delay Data (since 2025), Open Government Licence Toronto; scheduled trips from TTC GTFS, week of Nov 16, 2026',
           'measure': f'logged incidents with a recorded delay of {THR} minutes or more', 'window': ['2026-01-01', last],
           'validation': {'earlier': list(EARLY), 'later': ['2026-01-01', last], 'routes': int(len(df)), 'minTripsPerWeek': MIN_TRIPS,
                          'spearman': round(rho, 3), 'maeRoute': round(mae_route, 3), 'maeNetworkAverage': round(mae_net, 3), 'show': bool(ok)},
           'routes': {r: {'perWeek': round(float(x.l), 1), 'per100Trips': round(float(x.pl), 3),
                          'compared': 'more than most' if x.pl > q2 else 'fewer than most' if x.pl < q1 else 'about typical'} for r, x in df.sort_index().iterrows()}}
    json.dump(out, open(OUT, 'w'), indent=0)
    print(json.dumps(out['validation']))

if __name__ == '__main__': main(*sys.argv[1:4])
