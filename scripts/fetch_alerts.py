"""Copy the TTC's current subway alerts into data/live_alerts.json, so the page can read them from its own site,
and keep a log of when each alert was seen in data/alert_history.json. Also copies the elevator and escalator alerts
(https://gtfsrt.ttc.ca/alerts/accessibility, same licence) into data/access_alerts.json for the Plan B accessibility warning.

Source: the TTC GTFS Realtime alerts feed (https://gtfsrt.ttc.ca/alerts/subway), published on City of Toronto Open Data
("TTC GTFS Realtime (GTFS-RT)") under the Open Government Licence Toronto. The page cannot read the feed directly
(no cross origin headers), so a scheduled GitHub Action runs this every 30 minutes. fetchedAt is when the alert list last
changed; checkedAt is written on every successful check, even when the list is unchanged, so the page can show last
checked from the file. Those automated commits are titled "Copy TTC subway alerts" and change only these data files and the alert time forecast log (data/alert_forecasts.jsonl, written by scripts/log_forecasts.mjs).
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

def usable_body(status, body):
    """True only for an HTTP 200 with a non-empty body that is not an HTML, JSON or text error page.
    An empty or error body must not be written as a successful check (no checkedAt)."""
    if status != 200 or body is None:
        return False
    raw = body if isinstance(body, (bytes, bytearray)) else str(body).encode('utf-8', 'replace')
    if not raw.strip():
        return False
    head = raw.lstrip()[:64]
    if head.startswith(b'<') or head.startswith(b'{') or head.startswith(b'['):
        return False
    try:
        text_head = raw[:200].decode('utf-8')
    except UnicodeDecodeError:
        return True  # binary, likely a protobuf feed
    low = text_head.lstrip().lower()
    if low.startswith(('error', 'not found', 'service unavailable', 'unauthorized', 'forbidden')):
        return False
    return True

def fetch_response(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'wait-or-walk alerts copy (github.com/ALENZACODES/wait-or-walk)'})
    with urllib.request.urlopen(req, timeout=30) as res:
        status = getattr(res, 'status', 200)
        body = res.read()
    return status, body

def apply_if_usable(now, status, body, feed_ts, items, data=DATA, kind='subway'):
    """Write checkedAt only after a usable 200 body. Returns 'rejected' and leaves files unchanged otherwise."""
    if not usable_body(status, body):
        return 'rejected'
    if kind == 'access':
        return update_access(now, feed_ts, items, data)
    return update(now, feed_ts, items, data)

def text(t):
    for tr in t.translation:
        if tr.language in ('', 'en'): return ' '.join(tr.text.split())
    return ' '.join(t.translation[0].text.split()) if t.translation else ''

def feed_of(url):
    from google.transit import gtfs_realtime_pb2 as rt   # imported here so the tests run without it
    status, body = fetch_response(url)
    if not usable_body(status, body):
        raise ValueError('feed response is empty or not a usable body; not writing checkedAt')
    feed = rt.FeedMessage(); feed.ParseFromString(body)
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
    """Write the accessibility copy. Always bumps checkedAt; fetchedAt changes only with the list. Returns 'changed' or 'checked'."""
    p = os.path.join(data, 'access_alerts.json')
    old = json.load(open(p)) if os.path.exists(p) else None
    changed = not (old and old.get('alerts') == items)
    json.dump({'source': 'TTC GTFS Realtime alerts, accessibility feed (' + ACCESS_URL.split('?')[0] + ')', 'licence': 'Open Government Licence Toronto',
               'fetchedAt': now if changed else old.get('fetchedAt', now), 'checkedAt': now,
               'feedTimestamp': feed_ts if changed else old.get('feedTimestamp', feed_ts), 'alerts': items}, open(p, 'w'), indent=1, ensure_ascii=False)
    return 'changed' if changed else 'checked'

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
    """Always write checkedAt on the live copy. Rewrite history and fetchedAt only if the alert list changed.
    Returns 'changed' or 'checked'."""
    live_p, hist_p = os.path.join(data, 'live_alerts.json'), os.path.join(data, 'alert_history.json')
    old = json.load(open(live_p)) if os.path.exists(live_p) else None
    changed = not (old and old.get('alerts') == alerts)
    if changed:
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
        json.dump(hist, open(hist_p, 'w'), indent=1, ensure_ascii=False)
        fetchedAt, stamp = now, feed_ts
    else:
        fetchedAt, stamp = old.get('fetchedAt', now), old.get('feedTimestamp', feed_ts)
    json.dump({'source': 'TTC GTFS Realtime alerts, subway feed (' + URL.split('?')[0] + ')',
               'licence': 'Open Government Licence Toronto', 'fetchedAt': fetchedAt, 'checkedAt': now,
               'feedTimestamp': stamp, 'alerts': alerts},
              open(live_p, 'w'), indent=1, ensure_ascii=False)
    return 'changed' if changed else 'checked'

def main():
    now = int(time.time())
    feed_ts, alerts = read(now)
    print(update(now, feed_ts, alerts) + ':', len(alerts), 'subway alerts')
    ats, acc = read_access(now)
    print(update_access(now, ats, acc) + ':', len(acc), 'elevator and escalator alerts')

if __name__ == '__main__':
    main()
