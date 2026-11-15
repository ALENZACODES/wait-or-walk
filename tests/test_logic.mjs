import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
const require = createRequire(import.meta.url);
const W = require('../logic.js');
const load = (f) => JSON.parse(readFileSync(new URL('../data/' + f, import.meta.url)));
const model = load('model.json');
const metrics = load('metrics.json');

// The browser gives the same answer as the trained model in Python
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

// Advice thresholds
assert.equal(W.advice(0.4).call, 'walk'); assert.equal(W.advice(0.2).call, 'either'); assert.equal(W.advice(0.05).call, 'wait');

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

// Toronto clock
assert.deepEqual(W.torontoNow(new Date('2026-11-15T13:30:00Z')), { hour: 8, weekend: true });
assert.deepEqual(W.torontoNow(new Date('2026-07-15T21:00:00Z')), { hour: 17, weekend: false });

// Data checks: every station has coordinates and lines; Union has streetcars nearby
assert.equal(model.stations.length, 71);
for (const s of model.stations) { assert.ok(s.lat > 43.5 && s.lat < 44 && s.lon < -79 && s.lon > -80); assert.ok(s.lines.length); }
assert.ok(model.stations.find((s) => s.name === 'Union').nearby.some((r) => r.kind === 'streetcar'));

// The honest headline: on the latest test months the model beats the cause only baseline on log loss
// and its average forecast is close to what happened (the overestimate is fixed)
const f = metrics.folds[1];
assert.ok(f.waitOrWalk.logLoss < f.causeOnlyRate.logLoss);
assert.ok(f.waitOrWalk.auc > f.causeOnlyRate.auc);
assert.ok(Math.abs(f.waitOrWalk.meanPredicted - f.actualShareLong) < 0.01);
assert.ok(f.firstModel.meanPredicted - f.actualShareLong > 0.04);

console.log('Wait or Walk tests passed.');
