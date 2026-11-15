"""Copy the TTC's current subway alerts into data/live_alerts.json, so the page can read them from its own site.

Source: the TTC GTFS Realtime alerts feed (https://gtfsrt.ttc.ca/alerts/subway), published on City of Toronto Open Data
("TTC GTFS Realtime (GTFS-RT)") under the Open Government Licence Toronto. The page cannot read the feed directly
(no cross origin headers), so a scheduled GitHub Action runs this every 30 minutes and commits the file only when the
alerts changed. Keeps the alerts active at fetch time: id, line, cause, effect, text, start and end (Unix seconds).
Run: pip install gtfs-realtime-bindings==1.0.0 && python3 scripts/fetch_alerts.py
Exit code 0 always when the feed was read; the file is rewritten only if the alert list differs from the saved one.
"""
import json, os, sys, time, urllib.request
from google.transit import gtfs_realtime_pb2 as rt

URL = 'https://gtfsrt.ttc.ca/alerts/subway?format=binary'
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'live_alerts.json')
LINES = {'1': 'YU', '2': 'BD', '4': 'SHP'}

def text(t):
    for tr in t.translation:
        if tr.language in ('', 'en'): return tr.text.strip()
    return t.translation[0].text.strip() if t.translation else ''

def read(now):
    req = urllib.request.Request(URL, headers={'User-Agent': 'wait-or-walk alerts copy (github.com/ALENZACODES/wait-or-walk)'})
    feed = rt.FeedMessage(); feed.ParseFromString(urllib.request.urlopen(req, timeout=30).read())
    out = []
    for e in feed.entity:
        if not e.HasField('alert'): continue
        a = e.alert
        periods = [(p.start or 0, p.end or 0) for p in a.active_period]
        if periods and not any(s <= now and (not t or now < t) for s, t in periods): continue
        lines = sorted({LINES[i.route_id] for i in a.informed_entity if i.route_id in LINES})
        if not lines: continue
        cur = next(((s, t) for s, t in periods if s <= now and (not t or now < t)), (0, 0))
        out.append({'id': e.id, 'lines': lines, 'cause': rt.Alert.Cause.Name(a.cause), 'effect': rt.Alert.Effect.Name(a.effect),
                    'header': text(a.header_text), 'description': text(a.description_text), 'start': cur[0], 'end': cur[1]})
    return int(feed.header.timestamp), sorted(out, key=lambda x: x['id'])

def main():
    now = int(time.time())
    feed_ts, alerts = read(now)
    old = json.load(open(OUT)) if os.path.exists(OUT) else None
    if old and old.get('alerts') == alerts:
        print('unchanged:', len(alerts), 'alerts'); return
    json.dump({'source': 'TTC GTFS Realtime alerts, subway feed (' + URL.split('?')[0] + ')',
               'licence': 'Open Government Licence Toronto', 'fetchedAt': now, 'feedTimestamp': feed_ts, 'alerts': alerts},
              open(OUT, 'w'), indent=1, ensure_ascii=False)
    print('changed:', len(alerts), 'alerts')

if __name__ == '__main__':
    main()
