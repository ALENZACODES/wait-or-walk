// Sanity check of the alert time forecast log (data/alert_forecasts.jsonl). Not an accuracy check: it checks that each
// line is well formed, ids are unique and match the alert history, chances are in order (5+ >= 10+ >= 20+, all between
// 0 and 1), planned work and unread alerts carry no forecast, the backfilled flag matches the 40 minute rule, and the
// time of day and day type match the first seen time in Toronto. Exits non zero on any problem.
// Run: node scripts/check_forecast_log.mjs
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
const require = createRequire(import.meta.url);
const W = require('../logic.js');
const file = (f) => new URL('../data/' + f, import.meta.url);
const lines = readFileSync(file('alert_forecasts.jsonl'), 'utf8').split('\n').filter(Boolean);
const hist = JSON.parse(readFileSync(file('alert_history.json'))).alerts;
const bad = [], ids = new Set();
let withForecast = 0, planned = 0, backfilled = 0, last = '';
lines.forEach((l, i) => {
  let e; try { e = JSON.parse(l); } catch { bad.push(`line ${i + 1}: not JSON`); return; }
  const at = `line ${i + 1} (${e.id})`;
  if (ids.has(e.id)) bad.push(`${at}: duplicate id`); ids.add(e.id);
  if (!hist[e.id]) bad.push(`${at}: not in the alert history`);
  else if (new Date(hist[e.id].firstSeen * 1000).toISOString() !== e.firstSeen) bad.push(`${at}: first seen differs from the history`);
  if (e.loggedAt < last) bad.push(`${at}: logged before the line above`); last = e.loggedAt;
  if (e.backfilled !== (Date.parse(e.loggedAt) - Date.parse(e.firstSeen) > 40 * 60000)) bad.push(`${at}: backfilled flag wrong`);
  const t = W.torontoNow(new Date(e.firstSeen));
  if (e.time !== W.timeBucket(t.hour) || e.weekend !== t.weekend) bad.push(`${at}: time of day or day type wrong`);
  if (!e.model || !e.model.trainedThrough) bad.push(`${at}: no model version`);
  if (e.read.planned && e.forecasts !== null) bad.push(`${at}: planned work with a forecast`);
  if ((e.forecasts === null) === (e.reason === null)) bad.push(`${at}: needs exactly one of forecasts and reason`);
  for (const f of e.forecasts || []) if (!(f.p5 >= f.p10 && f.p10 >= f.p20 && f.p20 >= 0 && f.p5 <= 1)) bad.push(`${at}: chances out of order at ${f.station}`);
  if (e.forecasts) withForecast++; if (e.read.planned) planned++; if (e.backfilled) backfilled++;
});
console.log(`Forecast log: ${lines.length} alerts, ${withForecast} with a forecast, ${planned} planned work, ${backfilled} backfilled.${bad.length ? '\n' + bad.join('\n') : ' All checks passed.'}`);
if (bad.length) process.exit(1);
