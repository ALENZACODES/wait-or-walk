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
assert.deepEqual([r1.line, r1.station, r1.group], ['YU', null, 'medical']);
assert.deepEqual(r1.choice.options.map((o) => o.station), ['St Clair', 'Lawrence', 'Eglinton']);
const r2 = W.readAlert('Line 2: Trains are not stopping at Bloor-Yonge while we investigate a security incident.', model);
assert.deepEqual([r2.line, r2.station, r2.group], ['BD', 'Yonge', 'security']);
const r3 = W.readAlert('Delays of up to 10 minutes near Kipling Station due to a person at track level.', model);
assert.deepEqual([r3.line, r3.station, r3.group], ['BD', 'Kipling', 'track_person']);
const r4 = W.readAlert('Line 1: Shuttle buses running between St. George and Union due to a fire investigation.', model);
assert.deepEqual([r4.station, r4.group], [null, 'fire']);
assert.deepEqual(r4.choice.options.map((o) => o.station), ['St George', 'Union']);
const r5 = W.readAlert('Line 1: Minor delays at Dundas due to a signal problem.', model);
assert.deepEqual([r5.station, r5.group], ['TMU', 'signals']);
const r6 = W.readAlert('Line 1: delay at Bloor-Yonge, passenger alarm activated', model);
assert.deepEqual([r6.station, r6.group, r6.choice], ['Bloor', 'alarm', null]);
assert.equal(W.readAlert('hello', model).found.length, 0);
assert.deepEqual([W.readAlert('hello', model).station, W.readAlert('hello', model).group, W.readAlert('hello', model).line], [null, null, null]);
assert.equal(r3.flags.length, 0); assert.equal(r3.choice, null);

// Ambiguous alerts: no number until the rider confirms
const empty = { line: '', station: '', group: '', derived: new Set(), pending: null };
// Bloor-Yonge with no line: must pick a line
const by = W.readAlert('Trains are not stopping at Bloor-Yonge due to a security incident.', model);
assert.deepEqual([by.line, by.station], [null, null]);
assert.deepEqual(by.choice.options.map((o) => [o.station, o.line]), [['Bloor', 'YU'], ['Yonge', 'BD']]);
let s1 = W.applyAlert(empty, by);
assert.equal(W.canForecast(s1), false);
s1 = W.chooseOption(s1, by.choice.options[1]);
assert.deepEqual([s1.station, s1.line, s1.group], ['Yonge', 'BD', 'security']);
assert.equal(W.canForecast(s1), true);
// Two stations named: must choose one
let s2 = W.applyAlert(empty, r4);
s2 = { ...s2, line: 'YU' };
assert.equal(W.canForecast(s2), false);
s2 = W.chooseOption(s2, r4.choice.options[0]);
assert.equal(s2.station, 'St George'); assert.equal(W.canForecast(s2), true);
// A station on two lines with no line given: must pick the line
const sg = W.readAlert('Delays at St George due to a signal problem.', model);
assert.deepEqual(sg.choice.options.map((o) => o.line), ['YU', 'BD']);
assert.equal(W.canForecast(W.applyAlert(empty, sg)), false);
// Clearing the whole alert clears the derived fields and the forecast
let s3 = W.applyAlert(empty, r3);
assert.equal(W.canForecast(s3), true);
s3 = W.applyAlert(s3, null);
assert.deepEqual([s3.line, s3.station, s3.group, s3.derived.size, W.canForecast(s3)], ['', '', '', 0, false]);
// ...but keeps a field the rider chose by hand
let s4 = W.applyAlert(empty, r3); s4 = { ...s4, group: 'fire', derived: new Set(['line', 'station']) };
s4 = W.applyAlert(s4, null);
assert.deepEqual([s4.station, s4.group], ['', 'fire']);
// A later alert that lacks a field does not keep the old value
const s5 = W.applyAlert(W.applyAlert(empty, r3), W.readAlert('Delays due to a signal problem.', model));
assert.deepEqual([s5.station, s5.line, s5.group], ['', '', 'signals']);
// Every example button alert gives a number without a choice, except the one meant to show the choice
const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const examples = [...html.matchAll(/data-alert="([^"]+)"/g)].map((m) => m[1]);
assert.equal(examples.length, 4);
for (const a of examples) {
  const st = W.applyAlert(empty, W.readAlert(a, model));
  assert.equal(W.canForecast(st), !/Bloor-Yonge due/.test(a), a);
}

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
// The five journeys checked by hand against the raw schedule (docs/plan-b-checks.md)
assert.ok(W.planB(pb, 'Finch', 'Eglinton').direct.some((r) => r.route === '97' && /^South/.test(r.heading)));
assert.ok(W.planB(pb, 'Main Street', 'Broadview').direct.some((r) => r.route === '62' && /^West/.test(r.heading)));
assert.ok(!W.planB(pb, 'Main Street', 'Broadview').direct.some((r) => /^East/.test(r.heading)));
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
