"""Bike Share Toronto stations within 400 metres of each subway station, for the Plan B extras.

Source: Bike Share Toronto live GBFS v3 station_information
(https://toronto.publicbikesystem.net/customer/gbfs/v3.0/station_information). The City of Toronto lists Bike Share
Toronto data under the Open Government Licence Toronto; the Mobility Database lists the live feed as CC BY 4.0.
Only the station list is saved here. Bikes and docks are read live by the page from station_status, which allows
cross origin requests, and are never stored.
"""
import json, math, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, '..', 'data')
INFO = 'https://toronto.publicbikesystem.net/customer/gbfs/v3.0/station_information'
RADIUS = 400

def metres(a, b, c, d):
    k = math.pi / 180; x = (d - b) * k * math.cos((a + c) / 2 * k); y = (c - a) * k
    return 6371000 * math.hypot(x, y)

def name_of(s):
    n = s.get('name')
    if isinstance(n, list): n = next((t['text'] for t in n if t.get('language', 'en').startswith('en')), n[0]['text'] if n else '')
    return ' '.join(str(n).split())

def nearby(stations, bikes, radius=RADIUS, keep=3):
    out = {}
    for st in stations:
        near = sorted(((round(metres(st['lat'], st['lon'], b['lat'], b['lon'])), b) for b in bikes), key=lambda t: t[0])
        out[st['name']] = [{'id': b['station_id'], 'name': name_of(b), 'metres': m} for m, b in near if m <= radius][:keep]
    return out

def main():
    req = urllib.request.Request(INFO, headers={'User-Agent': 'wait-or-walk (github.com/ALENZACODES/wait-or-walk)'})
    info = json.load(urllib.request.urlopen(req, timeout=30))
    bikes = info['data']['stations']
    model = json.load(open(os.path.join(DATA, 'model.json')))
    near = nearby(model['stations'], bikes)
    json.dump({'source': 'Bike Share Toronto GBFS v3 station_information (' + INFO + '), read ' + time.strftime('%Y-%m-%d'),
               'licence': 'Open Government Licence Toronto (City of Toronto catalogue); live feed listed as CC BY 4.0 by the Mobility Database',
               'statusUrl': 'https://toronto.publicbikesystem.net/customer/gbfs/v3.0/station_status', 'radiusMetres': RADIUS,
               'stations': near}, open(os.path.join(DATA, 'bikeshare_near.json'), 'w'), indent=0, ensure_ascii=False)
    have = sum(1 for v in near.values() if v)
    print(len(bikes), 'bike stations;', have, 'of', len(near), 'subway stations have one within', RADIUS, 'm')

if __name__ == '__main__': main()
