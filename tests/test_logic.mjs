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
  const b = W.predictBands(model, s);
  assert.ok(Math.abs(b.p5 - s.p5) < 1e-4 && Math.abs(b.p20 - s.p20) < 1e-4, `band parity ${JSON.stringify(s)} got ${JSON.stringify(b)}`);
  assert.ok(b.p5 >= b.p10 && b.p10 >= b.p20);
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

// Station and line must match before any number is shown (regression: Union with Line 2)
const mm = { line: 'BD', station: 'Union', group: 'medical', derived: new Set(), pending: null };
assert.equal(W.mismatch(mm, model), true);
assert.equal(W.canForecast(mm, model), false);
assert.equal(W.canForecast({ ...mm, line: 'YU' }, model), true);
const ua = W.applyAlert({ line: '', station: '', group: '', derived: new Set(), pending: null }, W.readAlert('Line 2: Delays at Union due to a medical emergency.', model));
assert.deepEqual([ua.line, ua.station], ['BD', 'Union']);
assert.equal(W.canForecast(ua, model), false);
assert.equal(W.canForecast({ ...mm, station: 'Bloor', line: 'BD' }, model), false);
assert.equal(W.canForecast({ ...mm, station: 'Yonge', line: 'BD' }, model), true);

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
// Line 5 Eglinton is light rail, not a streetcar
assert.ok(pb.patterns.filter((q) => q.route === '5').every((q) => q.kind === 'LRT'));
assert.ok(pb.patterns.filter((q) => q.route === '504').every((q) => q.kind === 'streetcar'));
// A trip that ends at the station is not offered as a way out of it
assert.ok(!W.planB(pb, 'Kipling', '').all.some((r) => r.directions.some((d) => /towards Kipling Station/.test(d.heading))));

// Schedule times: services for a date, next departures, walking time
const pt = load('planb_times.json');
assert.equal(pt.times.length, pb.patterns.length);
const mon = W.activeServices(pt.calendar, '20261116', 0), sat = W.activeServices(pt.calendar, '20261121', 5);
assert.ok(mon.covered && mon.services.has('1') && !mon.services.has('2'));
assert.ok(sat.services.has('2') && !sat.services.has('1'));
assert.equal(W.activeServices(pt.calendar, '20270301', 0).covered, false);
const k149 = W.planB(pb, 'Kipling', 'Jane').direct.find((r) => r.route === '149');
const nd = W.nextDepartures(pt.times, k149.refs, mon.services, new Set(), 7 * 60 + 30, 3);
assert.equal(nd.length, 3); assert.ok(nd[0] >= 450 && nd[0] < nd[1] && nd[1] < nd[2]);
assert.ok(nd.includes(455)); // the 7:35 weekday trip checked by hand in docs/plan-b-checks.md
assert.deepEqual(W.decodeTimes('a.5.5'), [10, 15, 20]);
// Only departures a rider can still catch: now + walking time + 1 minute to board
const r149 = (now) => W.reachable(pb, pt.times, k149.refs, mon.services, new Set(), now, 3).map((x) => x.dep);
assert.ok(r149(7 * 60 + 33).includes(455));   // 7:33 + 1 min walk + 1 min to board = 7:35, still catchable
assert.ok(!r149(7 * 60 + 34).includes(455));  // one minute later it is gone
for (const now of [300, 455, 1050, 1300]) for (const x of W.reachable(pb, pt.times, k149.refs, mon.services, new Set(), now, 3)) assert.ok(x.dep >= now + x.walk + W.BOARD_MINUTES && x.dep - now <= 180);
assert.equal(W.reachable(pb, pt.times, k149.refs, mon.services, new Set(), 23 * 60 + 59, 3, 1).length, 0); // nothing within a 1 minute horizon at midnight
// Ranked by scheduled arrival: the first catchable departure plus the scheduled ride (plus subway onward when changing)
const kj = W.planB(pb, 'Kipling', 'Jane'), ranked = W.rankByArrival(pb, pt.times, kj.direct.concat(kj.via), mon.services, new Set(), 1050, 'Jane');
assert.ok(ranked.length >= 2);
for (let i = 1; i < ranked.length; i++) if (ranked[i].estimate !== null) assert.ok(ranked[i - 1].estimate !== null && ranked[i - 1].estimate <= ranked[i].estimate);
assert.ok(ranked.every((r) => r.estimate === null || r.estimate > r.first.dep));
assert.equal(W.subwayMinutes(pb, 'BD', 'Kipling', 'Jane'), W.subwayMinutes(pb, 'BD', 'Jane', 'Kipling'));
// Schedule validity: Dec 7 and Dec 20 are covered, Dec 22 is after the end, and the range is reported
assert.deepEqual(W.scheduleRange(pt.calendar), { from: '20261101', to: '20261221' });
assert.ok(W.activeServices(pt.calendar, '20261207', 0).covered && W.activeServices(pt.calendar, '20261207', 0).services.has('1'));
assert.ok(W.activeServices(pt.calendar, '20261220', 6).covered && W.activeServices(pt.calendar, '20261220', 6).services.size > 0);
assert.equal(W.activeServices(pt.calendar, '20261222', 1).covered, false);
// 3 a.m.: trips from the previous service day that run past midnight are counted
assert.deepEqual(W.torontoClock(new Date('2026-11-17T08:00:00Z')), { ymd: '20261117', prevYmd: '20261116', dow: 1, prevDow: 0, minutes: 180 });
assert.equal(W.walkMinutes(300), 4); assert.equal(W.walkMinutes(10), 1);
assert.deepEqual(W.torontoClock(new Date('2026-11-16T05:10:00Z')), { ymd: '20261116', prevYmd: '20261115', dow: 0, prevDow: 6, minutes: 10 });

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

// Bootstrap intervals bracket the point values, and the published claims match the numbers
const ev = metrics.evidence;
for (const b of [...ev.periods, ev.pooled]) for (const m of Object.values(b.methods)) for (const x of Object.values(m)) assert.ok(x.low <= x.value + 1e-9 && x.value <= x.high + 1e-9);
assert.equal(ev.pooled.differences.causeOnly.auc.distinguishable, true);
assert.equal(ev.pooled.differences.firstModel.auc.distinguishable, false);
assert.ok(ev.pooled.methods.waitOrWalk.calError.value < ev.pooled.methods.firstModel.calError.value);
assert.equal(ev.decisionValue.length, 6);
assert.equal(ev.simulation.rows.length, 3);
// Day block bootstrap and the extra evidence are present and bracket their values
for (const b of [...ev.dayBlock.periods, ev.dayBlock.pooled, ev.bands['5'].pooled, ev.bands['20'].pooled, ev.cellShrinkage.pooled]) for (const m of Object.values(b.methods)) for (const x of Object.values(m)) assert.ok(x.low <= x.value + 1e-9 && x.value <= x.high + 1e-9);
assert.equal(ev.survival.length, 32);
assert.ok(ev.sensitivity.filter((x) => x.shipped).length === 1);
const ss = ev.stationSimulation; assert.ok(ss.directionsWithAlternative > 0 && ss.subsets.all.delays === metrics.pooled.delays);

// No leakage: each test period's recalibration and decision rule settings come from data before it; the shipped model is never scored
for (const c of ev.decisionPolicy.chosen) assert.ok(c.chosenOn.slice(-10) < c.test.slice(0, 10), `decision rule picked on ${c.chosenOn} before ${c.test}`);
for (const f of metrics.folds) assert.ok(model.calibratedOn.slice(0, 10) > f.calibratedOn.slice(-10));
assert.equal(ev.pooledFirstTwo.byDelay.delays, metrics.folds[0].testDelays + metrics.folds[1].testDelays);
// The shipped wait or switch rule
const policy = load('policy.json');
assert.equal(policy.rule, 'expectedCost'); assert.equal(policy.chosenOn, model.calibratedOn); assert.equal(policy.binMeans.length, 4);
assert.equal(ev.decisionPolicy.shipped, 'expectedCost');
const dpa = ev.decisionPolicy.subsets.all;
assert.ok(dpa.expectedCost_savedVsCurrent.low > 0 && dpa.expectedCost_savedVsWait.low > 0, 'shipped rule clearly better than the old rule and always waiting');
const eb = W.expectedDelay({ p5: 0.4, p10: 0.23, p20: 0.1 }, [3.4, 6.15, 13.12, 33.87]);
assert.ok(Math.abs(eb - (0.6 * 3.4 + 0.17 * 6.15 + 0.13 * 13.12 + 0.1 * 33.87)) < 1e-9);
assert.equal(W.switchCall(8.2, 19, 0).switch, false); assert.equal(W.switchCall(20, 9, 0).switch, true); assert.equal(W.switchCall(5, -3, 0).cost, 0);
assert.equal(W.switchCall(null, 5, 0), null); assert.equal(W.switchCall(5, null, 0), null);
// Blue Night routes only overnight (midnight to 6 a.m., the model's night band)
assert.ok(W.isOvernight(0) && W.isOvernight(180) && W.isOvernight(359) && !W.isOvernight(360) && !W.isOvernight(1050) && !W.isOvernight(1439));

console.log('Wait or Walk tests passed.');
