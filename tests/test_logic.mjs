import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
const require = createRequire(import.meta.url);
const W = require('../logic.js');
const load = (f) => JSON.parse(readFileSync(new URL('../data/' + f, import.meta.url)));
const model = load('model.json');
const metrics = load('metrics.json');

// The browser gives the same answer as the trained Python model on 30 example inputs (an implementation check, not a test of accuracy)
for (const s of load('parity.json')) {
  const p = W.predict(model, s).p;
  assert.ok(Math.abs(p - s.p) < 1e-4, `parity ${JSON.stringify(s)} got ${p}`);
}

// Time buckets match training: 0 to 5, 6 to 9, 10 to 15, 16 to 19, 20 to 23
assert.deepEqual([0, 5, 6, 9, 10, 15, 16, 19, 20, 23].map(W.timeBucket), ['night', 'night', 'am_peak', 'am_peak', 'midday', 'midday', 'pm_peak', 'pm_peak', 'evening', 'evening']);

// Sensible ordering of causes at the same place and time
const at = (group) => W.predict(model, { group, station: 'Union', line: 'YU', time: 'pm_peak', weekend: false }).p;
assert.ok(at('fire') > at('track_person'));
assert.ok(at('track_person') > at('medical'));
assert.ok(at('medical') > at('doors'));
assert.ok(at('doors') > at('cleaning'));
assert.ok(at('injury_track') > 0.5);
assert.ok(at('alarm') < 0.1);

// Risk bands
assert.equal(W.advice(0.4).level, 'high'); assert.equal(W.advice(0.2).level, 'moderate'); assert.equal(W.advice(0.05).level, 'low');
assert.equal(W.advice(0.35).level, 'high'); assert.equal(W.advice(0.15).level, 'moderate');

// Explanations name the cause first for a strong cause
const ex = W.explain(model, { group: 'fire', station: 'Union', line: 'YU', time: 'pm_peak', weekend: false });
assert.ok(ex[0].text === 'Cause (fire or smoke) raises the odds' && ex[0].up);

// Alert reading
const r1 = W.readAlert('Line 1 Yonge-University: No service between St Clair and Lawrence stations due to a medical emergency at Eglinton.', model);
assert.deepEqual([r1.line, r1.station, r1.group], ['YU', 'St Clair', 'medical']);
const r2 = W.readAlert('Line 2: Trains are not stopping at Bloor-Yonge while we investigate a security incident.', model);
assert.deepEqual([r2.line, r2.station, r2.group], ['BD', 'Yonge', 'security']);
const r3 = W.readAlert('Delays of up to 10 minutes near Kipling Station due to a person at track level.', model);
assert.deepEqual([r3.line, r3.station, r3.group], ['BD', 'Kipling', 'track_person']);
const r4 = W.readAlert('Line 1: Shuttle buses running between St. George and Union due to a fire investigation.', model);
assert.deepEqual([r4.station, r4.group], ['St George', 'fire']);
const r5 = W.readAlert('Line 1: Minor delays at Dundas due to a signal problem.', model);
assert.deepEqual([r5.station, r5.group], ['TMU', 'signals']);
const r6 = W.readAlert('Line 1: delay at Bloor-Yonge, passenger alarm activated', model);
assert.deepEqual([r6.station, r6.group], ['Bloor', 'alarm']);
assert.equal(W.readAlert('hello', model).found.length, 0);
assert.deepEqual([W.readAlert('hello', model).station, W.readAlert('hello', model).group, W.readAlert('hello', model).line], [null, null, null]);
// Uncertain matches are flagged
assert.ok(r1.flags.some((f) => f.field === 'station'));
assert.ok(W.readAlert('Trains are not stopping at Bloor-Yonge due to a security incident.', model).flags.some((f) => /two lines/.test(f.text)));
assert.equal(r3.flags.length, 0);

// Toronto clock
assert.deepEqual(W.torontoNow(new Date('2026-11-15T13:30:00Z')), { hour: 8, weekend: true });
assert.deepEqual(W.torontoNow(new Date('2026-07-15T21:00:00Z')), { hour: 17, weekend: false });

// Data checks: every station has coordinates and lines; Union has streetcars nearby
assert.equal(model.stations.length, 71);
for (const s of model.stations) { assert.ok(s.lat > 43.5 && s.lat < 44 && s.lon < -79 && s.lon > -80); assert.ok(s.lines.length); }
assert.ok(model.stations.find((s) => s.name === 'Union').nearby.some((r) => r.kind === 'streetcar'));

// Plan B from the schedule, with direction and destination
const pb = load('planb.json');
const u = W.planB(pb, 'Union', 'College');
assert.ok(u.direct.some((r) => r.route === '97' && /^North/.test(r.heading)));
assert.ok(!u.direct.some((r) => /^South/.test(r.heading)));
const k = W.planB(pb, 'Kipling', 'Jane');
assert.ok(k.direct.some((r) => r.route === '149' && /^East/.test(r.heading)));
assert.ok(k.night.every((r) => r.night));
const dw = W.planB(pb, 'Dundas West', 'Union');
assert.ok(dw.via.some((r) => r.route === '504' && r.transfer === 'St Andrew'));
const all = W.planB(pb, 'Union', '');
assert.ok(all.all.length && all.all.every((r) => r.directions.length));
assert.ok(!JSON.stringify(pb).includes(' - '));

// Honest metrics, each test run with the deployed process (base model stops before the
// recalibration window, recalibration window is the three months before the test, no refit)
assert.equal(metrics.folds.length, 3);
for (const f of metrics.folds) {
  assert.ok(f.baseTrainedThrough < f.calibratedOn.slice(0, 10) && f.calibratedOn.slice(-10) < f.test.slice(0, 10));
  assert.ok(f.waitOrWalk.auc > f.causeOnlyRate.auc);
  assert.ok(f.waitOrWalk.logLoss < f.causeOnlyRate.logLoss);
}
assert.ok(model.baseTrainedThrough < model.calibratedOn.slice(0, 10));
assert.equal(metrics.pooled.delays, metrics.folds.reduce((a, f) => a + f.testDelays, 0));
for (const g of Object.values(model.groups)) assert.ok(g.longDelays <= g.delays);

console.log('Wait or Walk tests passed.');
