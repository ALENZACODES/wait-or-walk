"""Regression tests for the alerts copy (scripts/fetch_alerts.py), without the network or the protobuf library.
An unchanged feed bumps checkedAt on the live copy and leaves history and fetchedAt as they were; a changed feed rewrites both, logs first seen, last seen
and gone by times; a late run (the schedule delayed for hours) still only records what it saw, with its own time.
Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import fetch_alerts as F

A = {'id': '1', 'lines': ['YU'], 'cause': 'MEDICAL_EMERGENCY', 'effect': 'SIGNIFICANT_DELAYS', 'header': 'Line 1: Delays at Museum due to a medical emergency.', 'description': '', 'start': 100, 'end': 0}
B = {'id': '2', 'lines': ['BD'], 'cause': 'MAINTENANCE', 'effect': 'NO_SERVICE', 'header': 'Line 2: No service between Victoria Park and Kennedy due to planned track work.', 'description': '', 'start': 50, 'end': 99999}

class Copy(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
    def files(self):
        return {f: open(os.path.join(self.d, f), 'rb').read() for f in ('live_alerts.json', 'alert_history.json')}
    def test_unchanged_feed_bumps_checked_at(self):
        self.assertEqual(F.update(1000, 1000, [A, B], self.d), 'changed')
        before = self.files()
        self.assertEqual(F.update(2800, 2800, [A, B], self.d), 'checked')
        self.assertEqual(self.files()['alert_history.json'], before['alert_history.json'])  # history unchanged
        L = json.loads(self.files()['live_alerts.json'])
        self.assertEqual(L['fetchedAt'], 1000)
        self.assertEqual(L['checkedAt'], 2800)
        self.assertEqual([a['id'] for a in L['alerts']], ['1', '2'])
    def test_change_logs_first_last_and_gone(self):
        F.update(1000, 1000, [A, B], self.d)
        self.assertEqual(F.update(4600, 4600, [B], self.d), 'changed')
        h = json.loads(self.files()['alert_history.json'])['alerts']
        self.assertEqual((h['1']['firstSeen'], h['1']['lastSeen'], h['1']['goneBy']), (1000, 1000, 4600))
        self.assertEqual((h['2']['firstSeen'], h['2']['lastSeen']), (1000, 4600)); self.assertNotIn('goneBy', h['2'])
        L = json.loads(self.files()['live_alerts.json'])
        self.assertEqual((L['fetchedAt'], [a['id'] for a in L['alerts']]), (4600, ['2']))
    def test_late_run_uses_its_own_time(self):
        F.update(1000, 1000, [B], self.d)
        late = 1000 + 5 * 3600                          # the schedule ran five hours late
        self.assertEqual(F.update(late, late, [A, B], self.d), 'changed')
        h = json.loads(self.files()['alert_history.json'])['alerts']
        self.assertEqual(h['1']['firstSeen'], late)     # first seen when the late run saw it, never backdated
        self.assertEqual(json.loads(self.files()['live_alerts.json'])['fetchedAt'], late)
    def test_alert_that_returns_starts_a_new_sighting(self):
        F.update(1000, 1000, [A], self.d); F.update(2000, 2000, [], self.d); F.update(3000, 3000, [A], self.d)
        h = json.loads(self.files()['alert_history.json'])['alerts']['1']
        self.assertEqual((h['firstSeen'], h['lastSeen']), (3000, 3000)); self.assertNotIn('goneBy', h)
    def test_repo_files_have_the_shape_the_page_reads(self):
        root = os.path.join(os.path.dirname(__file__), '..', 'data')
        L = json.load(open(os.path.join(root, 'live_alerts.json'))); H = json.load(open(os.path.join(root, 'alert_history.json')))
        self.assertIn('fetchedAt', L); self.assertIn('checkedAt', L); self.assertTrue(all('header' in a for a in L['alerts']))
        self.assertTrue(all(h['firstSeen'] <= h['lastSeen'] and (not h.get('goneBy') or h['lastSeen'] <= h['goneBy']) for h in H['alerts'].values()))


    def test_empty_or_error_body_does_not_write_checked_at(self):
        # A 200 with an empty or error body must not bump checkedAt, even if a parsed list is offered.
        self.assertEqual(F.update(1000, 1000, [A], self.d), 'changed')
        before = json.loads(self.files()['live_alerts.json'])
        bodies = [b'', b'   ', b'<html>Internal Server Error</html>', b'{"error":"unavailable"}', b'Error: service unavailable']
        for body in bodies:
            self.assertFalse(F.usable_body(200, body), msg=repr(body))
            self.assertEqual(F.apply_if_usable(2800, 200, body, 2800, [A], self.d), 'rejected')
            L = json.loads(self.files()['live_alerts.json'])
            self.assertEqual(L['checkedAt'], 1000)
            self.assertEqual(L['fetchedAt'], 1000)
            self.assertEqual(L['alerts'], before['alerts'])
        proto = bytes([10, 8, 1])
        self.assertFalse(F.usable_body(500, proto))
        self.assertEqual(F.apply_if_usable(2800, 500, proto, 2800, [A], self.d), 'rejected')
        self.assertEqual(json.loads(self.files()['live_alerts.json'])['checkedAt'], 1000)

    def test_usable_200_body_still_writes_checked_at(self):
        # A 200 with a non-empty binary body (a stand-in for a protobuf feed) may write.
        proto = bytes([10, 8, 1, 18, 3, 8, 210, 9])
        self.assertTrue(F.usable_body(200, proto))
        self.assertEqual(F.apply_if_usable(1000, 200, proto, 1000, [A], self.d), 'changed')
        self.assertEqual(F.apply_if_usable(2800, 200, proto, 2800, [A], self.d), 'checked')
        self.assertEqual(json.loads(self.files()['live_alerts.json'])['checkedAt'], 2800)

class Access(unittest.TestCase):
    def test_unchanged_access_feed_bumps_checked_at(self):
        d = tempfile.mkdtemp(); X = [{'id': '9', 'station': 'Kipling', 'kind': 'escalator', 'header': 'Kipling: Escalator out of service.'}]
        self.assertEqual(F.update_access(1000, 1000, X, d), 'changed')
        self.assertEqual(F.update_access(2800, 2800, X, d), 'checked')
        L = json.load(open(os.path.join(d, 'access_alerts.json')))
        self.assertEqual((L['fetchedAt'], L['checkedAt'], L['alerts']), (1000, 2800, X))
        self.assertEqual(F.update_access(3600, 3600, [], d), 'changed')
        self.assertEqual(json.load(open(os.path.join(d, 'access_alerts.json')))['alerts'], [])

class Bikes(unittest.TestCase):
    def test_nearby_keeps_three_within_radius(self):
        import build_bikeshare as BS
        st = [{'name': 'X', 'lat': 43.65, 'lon': -79.38}]
        bikes = [{'station_id': str(i), 'name': [{'text': 'B%d' % i, 'language': 'en'}], 'lat': 43.65 + i * 0.001, 'lon': -79.38} for i in range(6)]
        out = BS.nearby(st, bikes)['X']
        self.assertEqual([b['id'] for b in out], ['0', '1', '2'])
        self.assertTrue(all(b['metres'] <= 400 for b in out)); self.assertEqual(out[1]['name'], 'B1')

if __name__ == '__main__':
    unittest.main()
