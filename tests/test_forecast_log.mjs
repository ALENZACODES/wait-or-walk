import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { entry } from '../scripts/log_forecasts.mjs';
const model = JSON.parse(readFileSync(new URL('../data/model.json', import.meta.url)));
const t = 1794772174; // Nov 15, 2026, 2:49 p.m. Toronto time, a Sunday
const a = entry('1', { firstSeen: t, header: 'Line 2 Bloor-Danforth: Delays at Kipling due to a person at track level.' }, model, new Date((t + 600) * 1000));
assert.equal(a.backfilled, false); assert.equal(a.time, 'midday'); assert.equal(a.weekend, true);
assert.equal(a.forecasts.length, 1); assert.equal(a.forecasts[0].station, 'Kipling');
assert.ok(a.forecasts[0].p5 >= a.forecasts[0].p10 && a.forecasts[0].p10 >= a.forecasts[0].p20);
const b = entry('2', { firstSeen: t, header: 'Line 2 Bloor-Danforth: No subway service between Victoria Park and Kennedy stations due to planned track work.' }, model, new Date((t + 7200) * 1000));
assert.equal(b.forecasts, null); assert.equal(b.reason, 'planned work: no forecast'); assert.equal(b.backfilled, true);
const c = entry('3', { firstSeen: t, header: 'Line 1 Yonge-University: No service between King and St Andrew stations due to a TPS investigation.' }, model);
assert.deepEqual(c.forecasts.map((f) => f.station).sort(), ['King', 'St Andrew']);
console.log('Forecast log tests passed.');
