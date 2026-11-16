"""Copy the TTC's current subway alerts into data/live_alerts.json, so the page can read them from its own site,
and keep a log of when each alert was seen in data/alert_history.json. Also copies the elevator and escalator alerts
(https://gtfsrt.ttc.ca/alerts/accessibility, same licence) into data/access_alerts.json for the Plan B accessibility warning.

Source: the TTC GTFS Realtime alerts feed (https://gtfsrt.ttc.ca/alerts/subway), published on City of Toronto Open Data
("TTC GTFS Realtime (GTFS-RT)") under the Open Government Licence Toronto. The page cannot read the feed directly
(no cross origin headers), so a scheduled GitHub Action runs this every 30 minutes and commits only when the alerts
changed. Those automated commits are titled "Copy TTC subway alerts" and change only these data files and the alert time forecast log (data/alert_forecasts.jsonl, written by scripts/log_forecasts.mjs).
Keeps the alerts active at fetch time: id, line, cause, effect, text, start and end (Unix seconds).

History: firstSeen is the first saved copy with the alert; lastSeen is the latest saved copy that still had it; goneBy
is the first saved copy without it. Copies are saved only when the alerts change, so an alert ran from about firstSeen
until some time between lastSeen and goneBy. A log for later checks, not an accuracy claim.
Run: pip install gtfs-realtime-bindings==1.0.0 && python3 scripts/fetch_alerts.py
"""
import json, os, time, urllib.request

URL = 'https://gtfsrt.ttc.ca/alerts/subway?format=binary'
ACCESS_URL = 'https://gtfsrt.ttc.ca/alerts/accessibility?format=binary'
DATA = os.path.join(os.path.dirname(__file__), '..', 'data')
LINES = {'1': 'YU', '2': 'BD', '4': 'SHP'}

def text(t):
    for tr in t.translation:
        if tr.language in ('', 'en'): return ' '.join(tr.text.split())
    return ' '.join(t.translation[0].text.split()) if t.translation else ''

def feed_of(url):
    from google.transit import gtfs_realtime_pb2 as rt   # imported here so the tests run without it
    req = urllib.request.Request(url, headers={'User-Agent': 'wait-or-walk alerts copy (github.com/ALENZACODES/wait-or-walk)'})
    feed = rt.FeedMessage(); feed.ParseFromString(urllib.request.urlopen(req, timeout=30).read())
    return rt, feed

def active(a, now):
    periods = [(p.start or 0, p.end or 0) for p in a.active_period]
    return not periods or any(s <= now and (not t or now < t) for s, t in periods)

def read_access(now):
    """Elevator and escalator alerts active now. The station is the text before the first colon, as the TTC writes it."""
    rt, feed = feed_of(ACCESS_URL); out = []
    for e in feed.entity:
        if not e.HasField('alert') or not active(e.alert, now): continue
        h = text(e.alert.header_text)
        if not h: continue
        kind = 'elevator' if 'elevator' in h.lower() else 'escalator' if 'escalator' in h.lower() else 'other'
        out.append({'id': e.id, 'station': h.split(':')[0].strip() if ':' in h else '', 'kind': kind, 'header': h})
    return int(feed.header.timestamp), sorted(out, key=lambda x: x['id'])

def update_access(now, feed_ts, items, data=DATA):
    p = os.path.join(data, 'access_alerts.json')
    old = json.load(open(p)) if os.path.exists(p) else None
    if old and old.get('alerts') == items: return 'unchanged'
    json.dump({'source': 'TTC GTFS Realtime alerts, accessibility feed (' + ACCESS_URL.split('?')[0] + ')', 'licence': 'Open Government Licence Toronto',
               'fetchedAt': now, 'feedTimestamp': feed_ts, 'alerts': items}, open(p, 'w'), indent=1, ensure_ascii=False)
    return 'changed'

def read(now):
    rt, feed = feed_of(URL)
    out = []
    for e in feed.entity:
        if not e.HasField('alert'): continue
        a = e.alert
        periods = [(p.start or 0, p.end or 0) for p in a.active_period]
        if not active(a, now): continue
        lines = sorted({LINES[i.route_id] for i in a.informed_entity if i.route_id in LINES})
        if not lines: continue
        cur = next(((s, t) for s, t in periods if s <= now and (not t or now < t)), (0, 0))
        out.append({'id': e.id, 'lines': lines, 'cause': rt.Alert.Cause.Name(a.cause), 'effect': rt.Alert.Effect.Name(a.effect),
                    'header': text(a.header_text), 'description': text(a.description_text), 'start': cur[0], 'end': cur[1]})
    return int(feed.header.timestamp), sorted(out, key=lambda x: x['id'])

def update(now, feed_ts, alerts, data=DATA):
    """Write the copy and the history only if the alert list changed. Returns 'changed' or 'unchanged'."""
    live_p, hist_p = os.path.join(data, 'live_alerts.json'), os.path.join(data, 'alert_history.json')
    old = json.load(open(live_p)) if os.path.exists(live_p) else None
    if old and old.get('alerts') == alerts: return 'unchanged'
    hist = json.load(open(hist_p)) if os.path.exists(hist_p) else {'since': now, 'alerts': {}}
    ids = {a['id'] for a in alerts}
    for a in alerts:
        h = hist['alerts'].get(a['id'])
        if not h or h.get('goneBy'):
            h = {'firstSeen': now}
        h.update({'lastSeen': now, 'header': a['header'], 'lines': a['lines'], 'cause': a['cause'], 'effect': a['effect']})
        h.pop('goneBy', None); hist['alerts'][a['id']] = h
    for i, h in hist['alerts'].items():
        if i not in ids and not h.get('goneBy'): h['goneBy'] = now
    json.dump({'source': 'TTC GTFS Realtime alerts, subway feed (' + URL.split('?')[0] + ')',
               'licence': 'Open Government Licence Toronto', 'fetchedAt': now, 'feedTimestamp': feed_ts, 'alerts': alerts},
              open(live_p, 'w'), indent=1, ensure_ascii=False)
    json.dump(hist, open(hist_p, 'w'), indent=1, ensure_ascii=False)
    return 'changed'

def main():
    now = int(time.time())
    feed_ts, alerts = read(now)
    print(update(now, feed_ts, alerts) + ':', len(alerts), 'subway alerts')
    ats, acc = read_access(now)
    print(update_access(now, ats, acc) + ':', len(acc), 'elevator and escalator alerts')

if __name__ == '__main__':
    main()
